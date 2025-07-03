from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uvicorn
import httpx
import re
import sqlite3
from datetime import datetime
import uuid
import os
from pathlib import Path
import aiofiles
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from chain import get_law_chain_intent, get_law_chain
from config import config
from callback import OutCallbackHandler
from schemas import KnowledgeUploadData, CaseStructure, IdealCaseStructure
import permission_manager
from permission_manager import get_user_private_files, get_public_files
from utils import (
    get_vectorstore, get_model_openai, get_memory, 
    rerank_documents_doc, get_embeder,
    get_law_vectorstore, get_case_vectorstore,
    search_law_documents, search_case_documents,
    search_case_documents_with_user_filter,
    rerank_existing_documents, get_model,
    add_single_file_to_vectorstore
)
from prompt import (
    PRE_QUESTION_PROMPT, CHECK_INTENT_PROMPT, 
    LAW_PROMPT_HISTORY, FRIENDLY_REJECTION_PROMPT,
    MULTI_QUERY_PROMPT_TEMPLATE
)
# 网络搜索功能实现
def search_web_serper(query: str, num_results: int = 3) -> str:
    """
    使用Serper API进行网络搜索
    
    Args:
        query: 搜索查询字符串
        num_results: 返回结果数量，默认为3
        
    Returns:
        格式化的搜索结果字符串
    """
    import requests
    import json
    
    try:
        # 从环境变量获取API密钥
        serper_api_key = os.getenv('SERPER_API_KEY')
        if not serper_api_key:
            print("警告: 未找到SERPER_API_KEY环境变量")
            return "网络搜索不可用：缺少API密钥"
        
        # Serper API配置
        url = "https://google.serper.dev/search"
        headers = {
            'X-API-KEY': serper_api_key,
            'Content-Type': 'application/json'
        }
        
        # 请求数据
        payload = {
            "q": query,
            "num": num_results,
            "hl": "zh-cn",  # 中文搜索
            "gl": "cn"      # 中国地区
        }
        
        # 发送请求
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # 解析搜索结果
        results = []
        if 'organic' in data:
            for item in data['organic'][:num_results]:
                title = item.get('title', '无标题')
                snippet = item.get('snippet', '无摘要')
                link = item.get('link', '无链接')
                
                # 格式化单个结果
                formatted_result = f"标题: {title}\n摘要: {snippet}\n来源: {link}"
                results.append(formatted_result)
        
        if results:
            # 用双换行符连接多个结果
            return "\n\n".join(results)
        else:
            return "未找到相关搜索结果"
            
    except requests.exceptions.RequestException as e:
        print(f"网络请求错误: {e}")
        return "网络搜索失败：请求错误"
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        return "网络搜索失败：响应解析错误"
    except Exception as e:
        print(f"搜索过程中发生错误: {e}")
        return "网络搜索失败：未知错误"
from langchain.schema.output_parser import StrOutputParser
from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import MarkdownTextSplitter
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from rank_bm25 import BM25Okapi
from dotenv import load_dotenv
from pathlib import Path
import logging
import numpy as np
import aiohttp
import aiofiles
import os

app = FastAPI(title="知识库上传接收服务")

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

# 数据模型定义
# 数据库初始化
def init_database():
    """【新架构版】初始化SQLite数据库，创建files和file_permissions表"""
    conn = sqlite3.connect('knowledge_files.db')
    cursor = conn.cursor()
    
    # 开启外键约束，这对于ON DELETE CASCADE至关重要
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. 创建新的 files 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            file_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            file_path TEXT NOT NULL UNIQUE,
            file_category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. 创建新的 file_permissions 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_permissions (
            permission_id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            permission_type TEXT NOT NULL, -- 'public' 或 'private'
            owner_id INTEGER,              -- 类型为 'private' 时，此处为 user_id
            FOREIGN KEY (file_id) REFERENCES files (file_id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()
    print("[DB_INIT] 新架构数据库表初始化/检查完成。")

# add_file_and_permissions函数已移动到permission_manager.py模块中

# 已删除 get_file_path_by_id - 基于旧表结构，已被新架构取代

# 已删除 delete_file_record - 基于旧表结构，已被新架构取代

def sanitize_filename(name: str) -> str:
    """文件名安全净化"""
    if not name or name.strip() == "":
        return "无标题文档"
    
    # 移除或替换非法字符
    sanitized = re.sub(r'[/\\:*?"<>|]', '_', name)
    # 替换连续空格为单个空格
    sanitized = re.sub(r'\s+', ' ', sanitized)
    # 移除首尾空格和点
    sanitized = sanitized.strip(' .')
    # 限制长度
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    
    return sanitized if sanitized else "无标题文档"

def format_data_to_markdown(data: dict) -> str:
    """将结构化数据格式化为Markdown"""
    markdown_content = f"""# {data.get('标题', '无标题')}

## 基本信息

**案例类型**: {data.get('案例类型', '未知')}

**关键词**: {', '.join(data.get('关键词', []))}

**当事人**: {', '.join(data.get('当事人', []))}

## 争议焦点

{data.get('争议焦点', '无')}

## 法律条文

{chr(10).join([f'- {item}' for item in data.get('法律条文', [])])}

## 判决结果

{data.get('判决结果', '无')}

## 案例要点

{data.get('案例要点', '无')}

## 适用法条

{chr(10).join([f'- {item}' for item in data.get('适用法条', [])])}

## 案例意义

{data.get('案例意义', '无')}
"""
    return markdown_content

def extract_text_from_file(file_path: str) -> str:
    """从文件中提取文本内容"""
    try:
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            try:
                import pypdf
                with open(file_path, 'rb') as file:
                    reader = pypdf.PdfReader(file)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text
            except ImportError:
                logger.error("pypdf库未安装，无法处理PDF文件")
                return ""
        
        elif file_ext == '.docx':
            try:
                import docx
                doc = docx.Document(file_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            except ImportError:
                logger.error("python-docx库未安装，无法处理DOCX文件")
                return ""
        
        elif file_ext in ['.txt', '.md']:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        
        else:
            logger.warning(f"不支持的文件格式: {file_ext}")
            return ""
            
    except Exception as e:
        logger.error(f"文本提取失败: {str(e)}")
        return ""

def clean_llm_json_output(raw_output: str) -> str:
    """清理LLM输出中的格式问题"""
    import re
    import json
    
    # 移除```json标记
    cleaned = re.sub(r'```json\s*', '', raw_output)
    cleaned = re.sub(r'```\s*$', '', cleaned)
    
    # 移除开头和结尾的多余空白
    cleaned = cleaned.strip()
    
    # 尝试找到JSON对象的开始和结束
    start_idx = cleaned.find('{')
    end_idx = cleaned.rfind('}')
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = cleaned[start_idx:end_idx+1]
        
        # 处理重复字段问题
        try:
            # 先尝试直接解析
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            # 如果失败，尝试修复重复字段
            lines = json_str.split('\n')
            seen_keys = set()
            cleaned_lines = []
            
            for line in lines:
                # 检查是否是键值对行
                if ':' in line and '"' in line:
                    # 提取键名
                    key_match = re.search(r'"([^"]+)"\s*:', line)
                    if key_match:
                        key = key_match.group(1)
                        if key in seen_keys:
                            continue  # 跳过重复的键
                        seen_keys.add(key)
                
                cleaned_lines.append(line)
            
            return '\n'.join(cleaned_lines)
    
    return cleaned

def structure_content_with_llm(raw_text: str) -> dict:
    """【全新升级版】使用LLM对内容进行深度加工和结构化处理"""
    try:
        # 注意：这里的parser现在使用新的IdealCaseStructure
        parser = PydanticOutputParser(pydantic_object=IdealCaseStructure)
        
        # 使用新的、更强大的Prompt
        from prompt import TRANSFORM_AND_STRUCTURE_PROMPT_TEMPLATE
        prompt_template = PromptTemplate(
            template=TRANSFORM_AND_STRUCTURE_PROMPT_TEMPLATE,
            input_variables=["text"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        # 获取模型
        model = get_model_openai()
        
        print("[INFO] 启动LLM进行深度加工与结构化...")
        
        # 分步处理：先获取原始响应，再清理，最后解析
        formatted_prompt = prompt_template.format(text=raw_text[:8000])
        raw_response = model.invoke(formatted_prompt)
        
        print(f"[DEBUG] LLM原始响应长度: {len(raw_response.content)}")
        
        # 清理响应内容
        cleaned_content = clean_llm_json_output(raw_response.content)
        print(f"[DEBUG] 清理后内容长度: {len(cleaned_content)}")
        
        # 使用parser解析清理后的内容
        result = parser.parse(cleaned_content)
        
        # 使用 .model_dump() 代替 .dict()
        return result.model_dump()
            
    except Exception as e:
        logger.error(f"LLM结构化处理失败: {str(e)}")
        print(f"[ERROR] 详细错误信息: {e}")
        
        # 失败时返回一个空的、符合新结构的字典
        return IdealCaseStructure(
            标题="文档解析失败", 关键词=[], 案例类型="未知", 基本案情="解析失败",
            裁判理由="解析失败", 裁判要旨="解析失败", 法律条文=[]
        ).model_dump()

def format_ideal_case_to_markdown(data: dict) -> str:
    """将新的、理想格式的结构化数据格式化为Markdown"""
    
    # 使用.get(key, default_value)来安全地获取数据
    title = data.get('标题', '无标题')
    keywords = ", ".join(data.get('关键词', []))
    case_type = data.get('案例类型', '未提供')
    case_number = data.get('案例编号', '未提供')
    basic_facts = data.get('基本案情', '未提供')
    reasoning = data.get('裁判理由', '未提供')
    gist = data.get('裁判要旨', '未提供')
    articles = "\n".join([f"- {item}" for item in data.get('法律条文', [])]) if data.get('法律条文') else '未提供'
    court = data.get('法院', '未提供')
    judgment_date = data.get('判决日期', '未提供')

    markdown_content = f"""# {title}

## 关键词

{keywords}

## 案例类型

{case_type}

## 案例编号

{case_number}

## 基本案情

{basic_facts}

## 裁判理由

{reasoning}

## 裁判要旨

{gist}

## 法律条文

{articles}

## 法院

{court}

## 判决日期

{judgment_date}
"""
    return markdown_content

# add_single_file_to_vectorstore 函数已移至 utils.py 作为统一的守门员函数

async def handle_existing_file_update(data: KnowledgeUploadData, existing_file_info: dict, pm):
    """处理已存在文件的智能更新操作 - 轻量级更新"""
    try:
        print(f"[DEBUG] 智能更新: 开始处理已存在文件 {data.file_id}")
        logger.info(f"智能更新: 开始处理已存在文件 {data.file_id}")
        
        # 获取当前文件信息
        current_file_path = existing_file_info.get('file_path')
        current_title = existing_file_info.get('title', 'untitled')
        
        print(f"[DEBUG] 智能更新: 当前文件路径: {current_file_path}")
        print(f"[DEBUG] 智能更新: 当前文件标题: {current_title}")
        
        # 确定新的存储路径和元数据
        knowledge_types = data.knowledge_types if data.knowledge_types else ['private']
        print(f"[DEBUG] 智能更新: 新的知识库类型: {knowledge_types}")
        
        # 检查是否为混合模式
        is_hybrid = 'public' in knowledge_types and 'private' in knowledge_types
        
        if is_hybrid:
            new_target_dir = '/home/spuser/new_law/redebug_lawbrain/LawBrain/law_docs/混合案例'
            doc_type = 'hybrid_case'
        elif 'public' in knowledge_types:
            new_target_dir = '/home/spuser/new_law/redebug_lawbrain/LawBrain/law_docs/共有案例'
            doc_type = 'public_case'
        else:
            new_target_dir = f'/home/spuser/new_law/redebug_lawbrain/LawBrain/law_docs/私有案例/{data.user_id}'
            doc_type = 'private_case'
        
        # 生成新的文件路径
        safe_filename = sanitize_filename(current_title) + '.md'
        new_file_path = os.path.join(new_target_dir, safe_filename)
        
        print(f"[DEBUG] 智能更新: 新目标目录: {new_target_dir}")
        print(f"[DEBUG] 智能更新: 新文件路径: {new_file_path}")
        
        # 如果路径发生变化，移动物理文件
        if current_file_path != new_file_path:
            print(f"[DEBUG] 智能更新: 路径变化，需要移动文件")
            print(f"[DEBUG] 智能更新: 从 {current_file_path} 移动到 {new_file_path}")
            
            # 确保新目标目录存在
            os.makedirs(new_target_dir, exist_ok=True)
            
            # 移动文件
            if os.path.exists(current_file_path):
                os.rename(current_file_path, new_file_path)
                print(f"[DEBUG] 智能更新: 文件移动成功")
            else:
                print(f"[WARNING] 智能更新: 原文件不存在: {current_file_path}")
            
            # 更新数据库中的文件路径
            pm.update_file_path(data.file_id, new_file_path)
            print(f"[DEBUG] 智能更新: 数据库路径更新完成")
            
            # 更新向量存储中的元数据
            import utils
            utils.update_vector_metadata(data.file_id, {'source': new_file_path})
            print(f"[DEBUG] 智能更新: 向量元数据更新完成")
        else:
            print(f"[DEBUG] 智能更新: 路径未变化，跳过文件移动")
        
        # 更新数据库权限（这是核心操作）
        print(f"[DEBUG] 智能更新: 更新数据库权限")
        success = permission_manager.add_file_with_permissions(
            file_id=data.file_id,
            user_id=data.user_id,
            title=current_title,
            file_path=new_file_path,
            knowledge_types=knowledge_types,
            file_category=data.file_category
        )
        
        if success:
            print(f"[DEBUG] 智能更新: 权限更新成功 - 文件ID: {data.file_id}, 权限: {knowledge_types}")
            logger.info(f"智能更新完成: 文件ID {data.file_id}, 新权限: {knowledge_types}")
            
            # 发送成功通知
            await send_upload_success_notification(data)
            print(f"✅ 智能更新成功！文件ID: {data.file_id}, 文件名: {data.filename}")
        else:
            print(f"[ERROR] 智能更新: 权限更新失败 - 文件ID: {data.file_id}")
            raise Exception("智能更新失败：权限更新失败")
            
    except Exception as e:
        print(f"[ERROR] 智能更新失败 {data.file_id}: {str(e)}")
        print(f"[ERROR] 异常详情: {type(e).__name__}: {str(e)}")
        logger.error(f"智能更新失败 {data.file_id}: {str(e)}")
        
        # 发送失败通知
        await send_upload_failure_notification(data, str(e))
        raise

async def process_new_knowledge(data: KnowledgeUploadData):
    """后台处理新知识文件的完整流程 - 智能检查文件存在性"""
    temp_path = None
    try:
        print(f"[DEBUG] 步骤0: 开始处理知识文件: {data.file_id}")
        logger.info(f"开始处理知识文件: {data.file_id}")
        
        # 【新增】步骤0.5：检查文件是否已存在
        pm = permission_manager.get_permission_manager()
        existing_file_info = pm.get_file_info(data.file_id)
        
        if existing_file_info:
            print(f"[INFO] 文件 {data.file_id} 已存在，执行智能更新操作")
            return await handle_existing_file_update(data, existing_file_info, pm)
        
        print(f"[INFO] 文件 {data.file_id} 不存在，执行完整新增流程")
        
        # 步骤1：下载并提取文本
        print(f"[DEBUG] 步骤1: 开始下载文件: {data.file_path}")
        download_result = await download_file_from_minio(data.file_path)
        print(f"[DEBUG] 步骤1: 下载结果: {download_result}")
        if not download_result.get("success"):
            print(f"[ERROR] 步骤1: 文件下载失败: {download_result.get('error', '未知错误')}")
            raise Exception(f"文件下载失败: {download_result.get('error', '未知错误')}")
        
        temp_path = download_result.get("local_path")
        print(f"[DEBUG] 步骤1: 临时文件路径: {temp_path}")
        if not temp_path or not os.path.exists(temp_path):
            print(f"[ERROR] 步骤1: 本地路径无效或文件不存在: {temp_path}")
            raise Exception("文件下载失败：本地路径无效")
        
        print(f"[DEBUG] 步骤1: 开始提取文本内容")
        raw_text = extract_text_from_file(temp_path)
        print(f"[DEBUG] 步骤1: 提取的文本长度: {len(raw_text) if raw_text else 0}")
        if not raw_text.strip():
            print(f"[ERROR] 步骤1: 文本提取失败或文件为空")
            raise Exception("文本提取失败或文件为空")
        
        # 步骤2：调用LLM进行内容结构化
        print(f"[DEBUG] 步骤2: 开始LLM结构化处理")
        structured_data = structure_content_with_llm(raw_text)
        print(f"[DEBUG] 步骤2: LLM结构化完成，标题: {structured_data.get('标题', 'N/A')}")
        
        # 步骤3：确定元数据和存档路径
        print(f"[DEBUG] 步骤3: 确定元数据和存档路径")
        knowledge_types = data.knowledge_types if data.knowledge_types else ['private']
        print(f"[DEBUG] 步骤3: 知识库类型列表: {knowledge_types}")
        
        # 检查是否为混合模式（同时包含public和private）
        is_hybrid = 'public' in knowledge_types and 'private' in knowledge_types
        
        if is_hybrid:
            # 混合模式：owner_id为列表，包含system和用户ID
            owner_id = ['system', str(data.user_id)]
            doc_type = 'hybrid_case'
            target_dir = '/home/spuser/new_law/redebug_lawbrain/LawBrain/law_docs/混合案例'
            print(f"[DEBUG] 步骤3: 混合模式 - owner_id: {owner_id}")
        elif 'public' in knowledge_types:
            # 纯公开模式
            owner_id = ['system']
            doc_type = 'public_case'
            target_dir = '/home/spuser/new_law/redebug_lawbrain/LawBrain/law_docs/共有案例'
        else:
            # 纯私有模式
            owner_id = [str(data.user_id)]
            doc_type = 'private_case'
            target_dir = f'/home/spuser/new_law/redebug_lawbrain/LawBrain/law_docs/私有案例/{data.user_id}'
        
        print(f"[DEBUG] 步骤3: 目标目录: {target_dir}, 文档类型: {doc_type}, owner_id: {owner_id}")
        
        # 创建简化的元数据结构
        metadata_for_db = {
            'file_id': data.file_id,
            'title': structured_data.get('标题', 'untitled') or "未知标题"
        }
        
        # 步骤4：序列化为Markdown并物理存档
        print(f"[DEBUG] 步骤4: 开始序列化为Markdown并物理存档")
        title = structured_data.get('标题', 'untitled')
        safe_filename = sanitize_filename(title) + '.md'
        print(f"[DEBUG] 步骤4: 文件标题: {title}, 安全文件名: {safe_filename}")
        
        # 确保目标目录存在
        print(f"[DEBUG] 步骤4: 创建目标目录: {target_dir}")
        os.makedirs(target_dir, exist_ok=True)
        
        final_save_path = os.path.join(target_dir, safe_filename)
        print(f"[DEBUG] 步骤4: 最终保存路径: {final_save_path}")
        
        # 更新元数据中的source字段
        metadata_for_db['source'] = final_save_path
        
        # 格式化为Markdown并保存
        print(f"[DEBUG] 步骤4: 格式化为Markdown")
        md_content = format_ideal_case_to_markdown(structured_data)
        print(f"[DEBUG] 步骤4: Markdown内容长度: {len(md_content)}")
        with open(final_save_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"[DEBUG] 步骤4: 文件保存完成")
        
        logger.info(f"文件已保存到: {final_save_path}")
        
        # 步骤5：向量化入库
        print(f"[DEBUG] 步骤5: 开始向量化入库")
        print(f"[DEBUG] 步骤5: 元数据: {metadata_for_db}")
        add_single_file_to_vectorstore(final_save_path, metadata_for_db, vectorstore_type='case')
        print(f"[DEBUG] 步骤5: 向量化入库完成")
        
        # 步骤6：注册文件和权限到数据库
        print(f"[DEBUG] 步骤6: 注册文件和权限到数据库")
        
        # 使用permission_manager模块添加文件和权限
        success = permission_manager.add_file_with_permissions(
            file_id=data.file_id,
            user_id=data.user_id,
            title=title,
            file_path=final_save_path,
            knowledge_types=knowledge_types,
            file_category=data.file_category
        )
        
        if success:
            print(f"[DEBUG] 步骤6: 文件和权限注册成功 - 文件ID: {data.file_id}, 权限: {knowledge_types}")
        else:
            print(f"[ERROR] 步骤6: 文件和权限注册失败 - 文件ID: {data.file_id}")
            raise Exception("文件和权限注册失败")
        
        print(f"[DEBUG] 所有步骤完成: 知识文件处理完成: {data.file_id}")
        print(f"✅ 文件上传成功！文件ID: {data.file_id}, 文件名: {data.filename}")
        logger.info(f"知识文件处理完成: {data.file_id}")
        logger.info(f"✅ 文件上传成功！文件ID: {data.file_id}, 文件名: {data.filename}")
        
        # 发送成功通知
        await send_upload_success_notification(data)
        
    except Exception as e:
        print(f"[ERROR] 处理知识文件失败 {data.file_id}: {str(e)}")
        print(f"[ERROR] 异常详情: {type(e).__name__}: {str(e)}")
        logger.error(f"处理知识文件失败 {data.file_id}: {str(e)}")
        
        # 发送失败通知
        await send_upload_failure_notification(data, str(e))
        raise
    finally:
        # 步骤7：清理临时文件
        print(f"[DEBUG] 步骤7: 开始清理临时文件: {temp_path}")
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"临时文件已清理: {temp_path}")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {str(e)}")

async def send_upload_success_notification(data: KnowledgeUploadData):
    """发送文件上传成功通知"""
    try:
        # 这里可以根据需要实现不同的通知方式
        # 例如：发送到消息队列、调用回调API、发送邮件等
        
        success_message = {
            "event": "upload_success",
            "user_id": data.user_id,
            "file_id": data.file_id,
            "filename": data.filename,
            "message": f"文件 '{data.filename}' 上传成功！",
            "timestamp": datetime.now().isoformat()
        }
        
        # 打印成功通知（可以替换为实际的通知机制）
        print(f"📢 上传成功通知: {success_message}")
        logger.info(f"上传成功通知: {success_message}")
        
        # TODO: 这里可以添加实际的通知发送逻辑
        # 例如：
        # - 发送到WebSocket连接
        # - 调用前端回调API
        # - 发送到消息队列
        # - 发送邮件通知
        
    except Exception as e:
        print(f"[ERROR] 发送上传成功通知失败: {str(e)}")
        logger.error(f"发送上传成功通知失败: {str(e)}")

async def send_upload_failure_notification(data: KnowledgeUploadData, error_message: str):
    """发送文件上传失败通知"""
    try:
        failure_message = {
            "event": "upload_failure",
            "user_id": data.user_id,
            "file_id": data.file_id,
            "filename": data.filename,
            "message": f"文件 '{data.filename}' 上传失败！",
            "error": error_message,
            "timestamp": datetime.now().isoformat()
        }
        
        # 打印失败通知
        print(f"❌ 上传失败通知: {failure_message}")
        logger.error(f"上传失败通知: {failure_message}")
        
        # TODO: 这里可以添加实际的通知发送逻辑
        # 例如：
        # - 发送到WebSocket连接
        # - 调用前端回调API
        # - 发送到消息队列
        # - 发送邮件通知
        
    except Exception as e:
        print(f"[ERROR] 发送上传失败通知失败: {str(e)}")
        logger.error(f"发送上传失败通知失败: {str(e)}")

async def new_intelligent_cancel(data: KnowledgeUploadData):
    """
    【全新智能删除函数】正确使用permission_manager模块处理智能删除请求
    """
    file_id = data.file_id
    user_id = data.user_id
    permissions_to_remove = set(data.knowledge_types or [])

    print(f"[智能删除] 开始处理文件 {file_id}。请求移除权限: {permissions_to_remove}")

    try:
        # 1. 获取管理器
        pm = permission_manager.get_permission_manager()
        
        # 2. 查询现状
        file_info = pm.get_file_info(file_id)
        if not file_info:
            msg = f"文件 {file_id} 不存在或已被删除，取消操作成功。"
            print(f"[INFO] {msg}")
            await send_upload_success_notification(data)
            return {"status": "success", "message": msg}

        current_path = file_info['file_path']
        current_permissions_info = pm.get_file_permissions(file_id)
        current_permission_types = {p['permission_type'] for p in current_permissions_info}
        print(f"[智能删除] 文件当前权限: {current_permission_types}")

        # 3. 计算剩余权限
        remaining_permissions = current_permission_types - permissions_to_remove
        print(f"[智能删除] 计算后剩余权限: {remaining_permissions}")

        # 4. 判断并执行
        if not remaining_permissions:
            # --- 分支A：执行完全删除 ---
            print(f"[智能删除] 决策：完全删除文件 {file_id}")
            
            # a. 删除物理文件
            if os.path.exists(current_path):
                os.remove(current_path)
                print(f"物理文件已删除: {current_path}")
            
            # b. 删除数据库记录 (权限记录会级联删除)
            pm.delete_file(file_id)
            print(f"数据库记录已删除: file_id={file_id}")
            
            # c. 删除向量索引
            vectorstore = get_case_vectorstore()
            vectorstore.delete(where={'file_id': file_id})
            print(f"向量数据库索引已删除: file_id={file_id}")
            
            await send_upload_success_notification(data)
            return {"status": "success", "message": "文件已完全删除"}

        else:
            # --- 分支B：执行部分删除（权限更新） ---
            print(f"[智能删除] 决策：更新文件 {file_id} 的权限为 {remaining_permissions}")
            
            # a. 更新数据库中的权限
            pm.set_file_permissions(file_id, list(remaining_permissions), user_id)
            print("数据库权限记录已更新。")

            # b. 判断是否需要移动文件并执行
            if 'public' in remaining_permissions:
                new_target_dir = '/home/spuser/new_law/redebug_lawbrain/LawBrain/law_docs/共有案例'
            else:  # private only
                new_target_dir = f'/home/spuser/new_law/redebug_lawbrain/LawBrain/law_docs/私有案例/{user_id}'

            new_path = os.path.join(new_target_dir, os.path.basename(current_path))

            if current_path != new_path:
                print(f"文件位置变更，移动: {current_path} -> {new_path}")
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                os.rename(current_path, new_path)
                
                # c. 更新数据库中的文件路径
                pm.update_file_path(file_id, new_path)
                print("数据库文件路径已更新。")
                
                # d. 更新向量库中的source元数据
                from utils import update_vector_metadata
                update_vector_metadata(file_id, {'source': new_path})
                print("向量数据库source元数据已更新。")
            
            await send_upload_success_notification(data)
            return {"status": "success", "message": "权限已更新", "remaining_permissions": list(remaining_permissions)}
            
    except Exception as e:
        print(f"[ERROR] 智能删除操作失败: {e}")
        import traceback
        traceback.print_exc()
        await send_upload_failure_notification(data, f"操作失败: {e}")
        return {
            "status": "error",
            "message": f"取消处理失败: {str(e)}",
            "file_id": data.file_id,
            "user_id": data.user_id
        }


# process_full_deletion函数已被删除，功能已整合到new_intelligent_cancel中

# process_permission_update函数已被删除，功能已整合到new_intelligent_cancel中

# process_knowledge_removal函数已被删除，功能已整合到new_intelligent_cancel中

# 初始化数据库
init_database()

class CompleteQASystem:
    """
    完整问答系统类 - 集成complete_qa_test.py的所有功能
    """
    
    def __init__(self):
        """初始化问答系统"""
        self.vectorstore = get_vectorstore(config.LAW_VS_COLLECTION_NAME)
        self.law_vectorstore = get_law_vectorstore()
        self.case_vectorstore = get_case_vectorstore()
        self.model = get_model_openai()
        self.memory = get_memory()
        
        # 初始化BM25索引
        self.bm25_index = self._create_bm25_index()
    
    def _create_bm25_index(self) -> BM25Okapi:
        """创建BM25索引"""
        try:
            # 获取所有文档
            all_docs = self.vectorstore.similarity_search("", k=1000)
            
            # 预处理文档文本
            tokenized_docs = []
            for doc in all_docs:
                text = doc.page_content.replace('\t', ' ').replace('\n', ' ')
                tokens = list(text.replace(' ', ''))
                tokens = [token for token in tokens if token.strip()]
                if tokens:
                    tokenized_docs.append(tokens)
            
            return BM25Okapi(tokenized_docs)
        except Exception as e:
            print(f"BM25索引创建失败: {e}")
            return None
    
    def step1_question_completion(self, question: str, chat_history: str = "") -> str:
        """步骤1: 问题补全"""
        try:
            input_data = {
                "question": question,
                "chat_history": chat_history
            }
            
            chain = PRE_QUESTION_PROMPT | self.model | StrOutputParser()
            completed_question = chain.invoke(input_data)
            return completed_question
        except Exception as e:
            print(f"问题补全失败: {e}")
            return question
    
    def step2_intent_recognition(self, question: str) -> str:
        """步骤2: 意图识别"""
        try:
            chain = CHECK_INTENT_PROMPT | self.model | StrOutputParser()
            intent = chain.invoke({"question": question}).strip().lower()
            return intent
        except Exception as e:
            print(f"意图识别失败: {e}")
            return "other"
    
    def step3_multi_query_generation(self, question: str) -> List[str]:
        """步骤3: 生成多查询"""
        try:
            chain = MULTI_QUERY_PROMPT_TEMPLATE | self.model | StrOutputParser()
            multi_queries_text = chain.invoke({"question": question})
            
            queries = [line.strip() for line in multi_queries_text.strip().split("\n") if line.strip()]
            return queries
        except Exception as e:
            print(f"多查询生成失败: {e}")
            return [question]
    
    def step4_knowledge_retrieval(self, multi_queries: List[str], mode: str, user_id: str = None, top_k: int = 10) -> List[Document]:
        """【重构版本】步骤4: 知识库检索 - 精确的模式化检索策略
        
        根据不同的知识库模式采用精确的检索策略：
        - public_knowledge: 只查公共知识（公共法律+公共案例）
        - private_knowledge: 只查该用户的私有知识（公共法律+私有案例）
        - entire_knowledge: 查用户可访问的全部知识（公共法律+公共案例+私有案例）
        - none_knowledge: 不使用知识库
        
        兼容旧的mode名称：
        - shared_knowledge -> public_knowledge
        """
        try:
            # 模式名称兼容性转换
            if mode == "shared_knowledge":
                mode = "public_knowledge"
                print(f"🔄 模式转换: shared_knowledge -> public_knowledge")
            
            if mode == "none_knowledge":
                print("跳过知识库检索 - mode为none_knowledge")
                return []

            main_query = multi_queries[0] if multi_queries else ""
            if not main_query:
                print("警告：没有有效的查询语句，跳过检索。")
                return []

            print(f"🎯 开始精确检索 (模式: {mode})，目标数量: 法律条文{top_k}篇 + 案例{top_k}篇")
            
            # 1. 法律条文检索：所有模式都检索公共法律条文
            print(f"📚 开始检索法律条文，目标数量: {top_k}")
            law_docs = search_law_documents(
                question=main_query,
                k=top_k,
                use_rerank=True,
                rerank_top_k=top_k
            )
            print(f"✅ 检索到 {len(law_docs)} 篇相关法律条文")

            # 2. 案例文档检索：根据模式执行不同的检索策略
            case_docs = []
            
            if mode == "public_knowledge":
                print(f"🌐 公共知识模式：检索公共案例，目标数量: {top_k}")
                # 获取公共文件ID列表
                public_file_ids = get_public_files()
                if public_file_ids:
                    case_docs = self._search_case_documents_by_file_ids(
                        question=main_query, 
                        file_ids=public_file_ids, 
                        k=top_k
                    )
                else:
                    print("⚠️ 未找到公共案例文件")
                    
            elif mode == "private_knowledge":
                if user_id:
                    try:
                        user_id_int = int(user_id)
                        print(f"🔒 私有知识模式：检索用户{user_id_int}的私有案例，目标数量: {top_k}")
                        # 获取用户私有文件ID列表
                        private_file_ids = get_user_private_files(user_id_int)
                        if private_file_ids:
                            case_docs = self._search_case_documents_by_file_ids(
                                question=main_query, 
                                file_ids=private_file_ids, 
                                k=top_k
                            )
                            print(f"✅ 检索到 {len(case_docs)} 篇私有案例")
                        else:
                            print(f"⚠️ 用户{user_id_int}没有私有案例文件")
                            case_docs = []
                    except (ValueError, TypeError) as e:
                        print(f"❌ 用户ID转换失败: {user_id}, 错误: {e}")
                        case_docs = []
                else:
                    print("⚠️ 私有知识库模式但未提供user_id")
                    case_docs = []
                
                # private_knowledge模式：只返回私有案例，不包含法律条文
                print(f"🎉 私有知识检索完成，返回 {len(case_docs)} 篇私有案例")
                return case_docs
                    
            elif mode == "entire_knowledge":
                if user_id:
                    try:
                        user_id_int = int(user_id)
                        print(f"🌍 全量知识模式：检索公共+用户{user_id_int}私有案例，目标数量: {top_k * 3} -> 重排序保留{top_k}")
                        
                        # 获取公共文件和用户私有文件ID
                        public_file_ids = get_public_files()
                        private_file_ids = get_user_private_files(user_id_int)
                        all_accessible_file_ids = list(set(public_file_ids + private_file_ids))
                        
                        if all_accessible_file_ids:
                            # 检索更多文档然后重排序
                            case_docs = self._search_case_documents_by_file_ids(
                                question=main_query, 
                                file_ids=all_accessible_file_ids, 
                                k=top_k * 3  # 检索3倍数量
                            )
                            # 重排序保留top_k个
                            if len(case_docs) > top_k:
                                case_docs = rerank_existing_documents(
                                    question=main_query,
                                    docs=case_docs,
                                    top_k=top_k
                                )
                        else:
                            print(f"⚠️ 用户{user_id_int}没有可访问的案例文件")
                    except (ValueError, TypeError) as e:
                        print(f"❌ 用户ID转换失败: {user_id}, 错误: {e}")
                        # Fallback: 只检索公共案例
                        public_file_ids = get_public_files()
                        if public_file_ids:
                            case_docs = self._search_case_documents_by_file_ids(
                                question=main_query, 
                                file_ids=public_file_ids, 
                                k=top_k
                            )
                else:
                    print("⚠️ 全量知识库模式但未提供user_id，回退到公共知识模式")
                    # Fallback: 只检索公共案例
                    public_file_ids = get_public_files()
                    if public_file_ids:
                        case_docs = self._search_case_documents_by_file_ids(
                            question=main_query, 
                            file_ids=public_file_ids, 
                            k=top_k
                        )
            else:
                print(f"❌ 未知的检索模式: {mode}，回退到公共知识模式")
                # Fallback: 公共知识模式
                public_file_ids = get_public_files()
                if public_file_ids:
                    case_docs = self._search_case_documents_by_file_ids(
                        question=main_query, 
                        file_ids=public_file_ids, 
                        k=top_k
                    )
                
            print(f"✅ 检索到 {len(case_docs)} 篇相关案例")

            # 3. 合并法律条文和案例文档
            final_docs = law_docs + case_docs
            print(f"🎉 检索流程完成，总计返回 {len(final_docs)} 篇文档 (法律条文: {len(law_docs)}, 案例: {len(case_docs)})")
            return final_docs
                
        except Exception as e:
            print(f"❌ 知识库检索过程中发生严重错误: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _search_case_documents_by_file_ids(self, question: str, file_ids: List[int], k: int) -> List[Document]:
        """根据文件ID列表检索案例文档的内部辅助函数"""
        try:
            if not file_ids:
                return []
            
            # 使用现有的search_case_documents函数，但添加文件ID过滤
            # 这里我们需要修改utils中的函数或者直接在这里实现过滤逻辑
            # 暂时使用现有函数，后续可以优化
            case_docs = search_case_documents(
                question=question, 
                k=k * 2,  # 检索更多然后过滤
                use_rerank=True, 
                rerank_top_k=k
            )
            
            # 过滤出指定文件ID的文档
            filtered_docs = []
            for doc in case_docs:
                doc_file_id = doc.metadata.get('file_id')
                if doc_file_id and int(doc_file_id) in file_ids:
                    filtered_docs.append(doc)
                if len(filtered_docs) >= k:
                    break
            
            return filtered_docs[:k]
            
        except Exception as e:
            print(f"❌ 根据文件ID检索案例文档失败: {e}")
            return []
    
    def step5_separated_reranking(self, law_docs: List, case_docs: List, question: str, top_k: int = 10) -> Dict:
        """步骤5: 分离式重排序 - 新逻辑：对k篇法律条文和k篇案例分别进行重排序"""
        try:
            # 新逻辑：直接使用k值进行重排序，不再进行复杂的分配计算
            # 对法律条文重排序保留k篇，对案例文档重排序保留k篇
            law_rerank_k = top_k  # 法律条文重排序保留k篇
            case_rerank_k = top_k  # 案例文档重排序保留k篇
            
            reranked_law_docs = []
            reranked_case_docs = []
            
            # 对法律条文进行重排序
            if law_docs:
                print(f"对{len(law_docs)}篇法律条文进行重排序，保留前{law_rerank_k}篇")
                from utils import rerank_existing_documents
                reranked_law_docs = rerank_existing_documents(
                    question=question,
                    docs=law_docs,
                    top_k=law_rerank_k
                )
            
            # 对案例进行重排序
            if case_docs:
                print(f"对{len(case_docs)}篇案例进行重排序，保留前{case_rerank_k}篇")
                from utils import rerank_existing_documents
                reranked_case_docs = rerank_existing_documents(
                    question=question,
                    docs=case_docs,
                    top_k=case_rerank_k
                )
            
            print(f"重排序结果: {len(reranked_law_docs)}篇法律条文 + {len(reranked_case_docs)}篇案例文档 = 总计{len(reranked_law_docs) + len(reranked_case_docs)}篇")
            
            return {
                'reranked_law_docs': reranked_law_docs,
                'reranked_case_docs': reranked_case_docs,
                'total_count': len(reranked_law_docs) + len(reranked_case_docs)
            }
            
        except Exception as e:
            print(f"重排序失败: {e}")
            return {
                'reranked_law_docs': law_docs,  # 失败时返回原始文档
                'reranked_case_docs': case_docs,
                'total_count': len(law_docs) + len(case_docs)
            }
    
    def step6_web_search(self, question: str, num_results: int = 3) -> str:
        """步骤6: 联网检索"""
        try:
            web_content = search_web_serper(question, num_results)
            return web_content if web_content else ""
        except Exception as e:
            print(f"联网检索失败: {e}")
            return ""
    
    def _extract_urls_from_web_content(self, web_content: str) -> List[str]:
        """从网络搜索内容中提取网址"""
        import re
        urls = []
        
        # 使用正则表达式匹配"来源: "后面的网址
        url_pattern = r'来源: (https?://[^\s]+)'
        matches = re.findall(url_pattern, web_content)
        
        for url in matches:
            urls.append(url)
        
        return urls
    
    def _create_source_summary(self, context_docs: List[Document]) -> str:
        """使用LLM根据上下文文档生成来源摘要"""
        if not context_docs:
            return ""

        # 1. 将文档分离为法律和案例
        law_docs = [doc for doc in context_docs if doc.metadata.get('doc_type') == 'law']
        case_docs = [doc for doc in context_docs if doc.metadata.get('doc_type') == 'case']

        print(f"📊 调试输出 - 文档分类统计:")
        print(f"  法律条文文档数量: {len(law_docs)}")
        print(f"  案例文档数量: {len(case_docs)}")
        
        # 2. 准备Prompt的输入内容
        # 改进法律条文格式，提供更多元数据信息
        law_context_parts = []
        for doc in law_docs:
            source = doc.metadata.get('source', '未知来源')
            title = doc.metadata.get('title', '')
            content = doc.page_content
            
            # 尝试从title或content中提取条文号信息
            if title and '第' in title and '条' in title:
                law_context_parts.append(f"《{source}》{title}: {content}")
            else:
                law_context_parts.append(f"《{source}》: {content}")
        
        law_context_str = "\n".join(law_context_parts)
        # 对于案例，我们只提取标题（通常在元数据里），让LLM去总结
        case_context_str = "\n".join([f"《{doc.metadata.get('title', '未知案例')}》全文：{doc.page_content}" for doc in case_docs])

        # 如果没有对应类型的文档，则传入提示信息
        if not law_context_str:
            law_context_str = "无"
        if not case_context_str:
            case_context_str = "无"
            
        print(f"📝 调试输出 - 法律条文摘要部分:")
        if law_docs:
            for i, doc in enumerate(law_docs, 1):
                source = doc.metadata.get('source', '未知来源')
                content_preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                print(f"  {i}. 《{source}》: {content_preview}")
        else:
            print(f"  无法律条文文档")
            
        print(f"📝 调试输出 - 案例摘要部分:")
        if case_docs:
            for i, doc in enumerate(case_docs, 1):
                title = doc.metadata.get('title', '未知案例')
                content_preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                print(f"  {i}. 《{title}》: {content_preview}")
        else:
            print(f"  无案例文档")
            
        # 3. 构建并调用摘要生成链
        try:
            from prompt import SOURCE_SUMMARY_PROMPT
            from langchain_core.output_parsers import StrOutputParser

            summary_chain = SOURCE_SUMMARY_PROMPT | self.model | StrOutputParser()
            
            summary = summary_chain.invoke({
                "law_context": law_context_str,
                "case_context": case_context_str
            })
            
            print(f"🎯 调试输出 - 生成的完整摘要:")
            print(f"{summary.strip()}")
            
            return summary.strip()
            
        except Exception as e:
            print(f"❌ 生成来源摘要失败: {e}")
            return ""  # 出错时返回空字符串

    def step7_final_answer_generation(self, question: str, intent: str, context_docs: List = None, web_content: str = "", chat_history: List = None) -> Dict[str, str]:
        """步骤7: 最终回答生成 - 现在返回一个包含主回答和来源摘要的字典。"""
        final_answer = ""
        source_summary = ""

        try:
            if intent == "law":
                # 使用法律问答链
                from chain import get_law_chain
                from callback import OutCallbackHandler
                out_callback = OutCallbackHandler()
                law_chain = get_law_chain(config, out_callback)
                
                # 准备上下文
                context = ""
                if context_docs:
                    context = "\n\n".join([doc.page_content for doc in context_docs])
                
                if web_content:
                    context += "\n\n网络搜索结果:\n" + web_content
                
                # 准备输入
                chain_input = {
                    "question": question,
                    "context": context
                }
                
                # 如果有对话历史，添加到输入中
                if chat_history:
                    chain_input["chat_history"] = chat_history
                
                response = law_chain.invoke(chain_input)
                
                # 从响应中提取answer字段
                if isinstance(response, dict) and 'answer' in response:
                    final_answer = response['answer']
                else:
                    final_answer = str(response)

                # --- 【新增】生成来源摘要的逻辑 ---
                if context_docs:
                    print("\n✍️ 开始生成来源摘要...")
                    source_summary = self._create_source_summary(context_docs)
                    print(f"来源摘要生成完毕:\n{source_summary}")
                    
                    # --- 【新增】添加网络搜索来源网址 ---
                    if web_content:
                        web_urls = self._extract_urls_from_web_content(web_content)
                        if web_urls:
                            source_summary += "\n\n**网络搜索来源：**\n" + "\n".join(web_urls)

            else:
                # 非法律问题的友好拒绝
                from prompt import FRIENDLY_REJECTION_PROMPT
                model = get_model()
                response = model.invoke(FRIENDLY_REJECTION_PROMPT.format(question=question))
                final_answer = response.content if hasattr(response, 'content') else str(response)
                
        except Exception as e:
            print(f"回答生成失败: {e}")
            final_answer = "抱歉，系统暂时无法回答您的问题。"
        
        # --- 返回包含两部分的字典 ---
        return {
            "main_answer": final_answer,
            "source_summary": source_summary
        }
    
    def complete_qa_process(self, question: str, user_id: str = None, chat_history: List = None, 
                           top_k: int = 10, web_search: bool = False, mode = "shared_knowledge") -> Dict[str, Any]:
        """完整问答流程 - 根据用户描述的核心处理流程实现"""
        results = {
            "original_question": question,
            "user_id": user_id,
            "mode": mode
        }
        
        print(f"🚀 开始完整问答流程")
        print(f"原始问题: {question}")
        print(f"用户ID: {user_id}")
        print(f"检索模式: {mode}")
        print(f"检索数量: {top_k}")
        print(f"联网搜索: {web_search}")
        
        # 第二步：获取并处理对话上下文（已在调用前处理）
        # 转换chat_history为字符串格式，只保留用户消息用于问题补全
        chat_history_str = ""
        if chat_history:
            # 只保留用户的消息，过滤掉助手的回答，避免将助手回答当作问题补全的输入
            user_messages = []
            for msg in chat_history:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role == 'user' and content.strip():
                    user_messages.append(f"用户: {content}")
            
            chat_history_str = "\n".join(user_messages)
            print(f"对话上下文长度: {len(chat_history)} 条消息，用户消息: {len(user_messages)} 条")
            print(f"用于问题补全的历史: {chat_history_str[:200]}..." if len(chat_history_str) > 200 else f"用于问题补全的历史: {chat_history_str}")
        
        # 第三步：问题预处理与意图识别
        print("\n📝 第三步：问题预处理与意图识别")
        
        # 步骤1: 问题补全
        print("执行问题补全...")
        completed_question = self.step1_question_completion(question, chat_history_str)
        results["completed_question"] = completed_question
        print(f"补全后问题: {completed_question}")
        
        # 步骤2: 意图识别
        print("执行意图识别...")
        intent = self.step2_intent_recognition(completed_question)
        results["intent"] = intent
        print(f"识别意图: {intent}")
        
        # 第四步：根据意图执行不同逻辑分支
        print(f"\n🔀 第四步：根据意图执行不同逻辑分支")
        
        if intent == "law":
            print("✅ 意图为法律问题，执行完整法律问答流程")
            
            # 步骤3: 多查询生成
            print("\n🔍 生成多查询...")
            multi_queries = self.step3_multi_query_generation(completed_question)
            results["multi_queries"] = multi_queries
            print(f"生成查询数量: {len(multi_queries)}")
            for i, query in enumerate(multi_queries, 1):
                print(f"  查询{i}: {query}")
            
            # 【全新、简化的步骤4】
            print(f"\n📚 执行知识库检索与排序 (模式: {mode})...")
            # 直接调用新的step4，它会完成所有检索和排序，并返回最终的文档列表
            reranked_docs = self.step4_knowledge_retrieval(
                multi_queries, mode, user_id, top_k
            )
            results["retrieved_docs_count"] = len(reranked_docs)  # 更新日志key
            print(f"最终用于生成回答的文档数量: {len(reranked_docs)}")
            
            # 【彻底删除步骤5】
            # self.step5_separated_reranking(...) 整个步骤和相关的k值计算都删掉
            
            # 步骤6: 联网检索
            web_content = ""
            if web_search:
                print("\n🌐 执行联网搜索...")
                web_content = self.step6_web_search(completed_question)
                print(f"网络搜索内容长度: {len(web_content)}")
            else:
                print("\n❌ 跳过联网搜索")
            results["web_content_length"] = len(web_content)
            
            # 步骤7: 最终回答生成
            print("\n💬 生成最终回答...")
            # 【新调用方式】接收一个字典
            final_result_dict = self.step7_final_answer_generation(
                completed_question, intent, reranked_docs, web_content, chat_history
            )
            
            # 【新组装逻辑】拼接主回答和来源摘要
            main_answer = final_result_dict.get("main_answer", "")
            source_summary = final_result_dict.get("source_summary", "")
            
            final_answer_with_summary = main_answer
            # 如果来源摘要不为空，则添加
            if source_summary:
                final_answer_with_summary += f"\n\n{source_summary}"
            
            # 将拼接后的完整结果存入 results
            results["final_answer"] = final_answer_with_summary
            print(f"最终完整回答长度: {len(final_answer_with_summary)}")
            
        else:
            print("ℹ️ 意图为非法律问题，执行简化流程")
            
            # 分支A：意图为"other"(非法律问题)
            results["multi_queries"] = []
            results["retrieved_docs_count"] = 0
            results["reranked_docs_count"] = 0
            
            # 检查是否联网
            web_content = ""
            if web_search:
                print("\n🌐 执行联网搜索...")
                web_content = self.step6_web_search(completed_question)
                print(f"网络搜索内容长度: {len(web_content)}")
            else:
                print("\n❌ 跳过联网搜索")
            results["web_content_length"] = len(web_content)
            
            # 生成最终回答
            print("\n💬 生成友好回答...")
            # 【新调用方式】接收一个字典
            final_result_dict = self.step7_final_answer_generation(
                completed_question, intent, [], web_content, chat_history
            )
            
            # 【新组装逻辑】拼接主回答和来源摘要
            main_answer = final_result_dict.get("main_answer", "")
            source_summary = final_result_dict.get("source_summary", "")
            
            final_answer_with_summary = main_answer
            # 如果来源摘要不为空，则添加
            if source_summary:
                final_answer_with_summary += f"\n\n{source_summary}"
            
            # 将拼接后的完整结果存入 results
            results["final_answer"] = final_answer_with_summary
            print(f"最终完整回答长度: {len(final_answer_with_summary)}")
        
        print("\n✅ 完整问答流程结束")
        return results

# 全局问答系统实例
qa_system = CompleteQASystem()

async def download_file_from_minio(file_path: str, save_path: str = None, user_id: int = None, category: str = None) -> dict:
    """从MinIO服务下载文件到指定路径
    
    Args:
        file_path: MinIO文件路径
        save_path: 保存路径（可选，如果不提供则自动生成）
        user_id: 用户ID（用于生成路径）
        category: 文件分类（用于生成路径）
    
    Returns:
        dict: 包含下载结果的字典
    """
    try:
        print(f"[DEBUG] MinIO下载: 开始下载文件: {file_path}")
        async with aiohttp.ClientSession() as session:
            payload = {"minio_path": file_path}
            print(f"[DEBUG] MinIO下载: 请求载荷: {payload}")
            print(f"[DEBUG] MinIO下载: 请求URL: http://192.168.240.1:5000/api/file-download/download")
            async with session.post(
                "http://192.168.240.1:5000/api/file-download/download",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                print(f"[DEBUG] MinIO下载: 响应状态码: {response.status}")
                if response.status == 200:
                    print(f"[DEBUG] MinIO下载: 开始读取文件内容")
                    # 获取文件内容
                    file_content = await response.read()
                    print(f"[DEBUG] MinIO下载: 文件内容大小: {len(file_content)} bytes")
                    
                    # 获取文件名
                    filename = None
                    content_disposition = response.headers.get('Content-Disposition', '')
                    print(f"[DEBUG] MinIO下载: Content-Disposition: {content_disposition}")
                    if 'filename=' in content_disposition:
                        filename = content_disposition.split('filename=')[1].strip('"')
                    else:
                        filename = os.path.basename(file_path)
                    print(f"[DEBUG] MinIO下载: 解析的文件名: {filename}")
                    
                    # 确定保存路径
                    if save_path is None:
                        save_path = generate_save_path(filename, user_id, category)
                    print(f"[DEBUG] MinIO下载: 保存路径: {save_path}")
                    
                    # 确保目录存在
                    save_dir = os.path.dirname(save_path)
                    print(f"[DEBUG] MinIO下载: 创建目录: {save_dir}")
                    Path(save_dir).mkdir(parents=True, exist_ok=True)
                    
                    # 保存文件到指定路径
                    print(f"[DEBUG] MinIO下载: 开始写入文件")
                    async with aiofiles.open(save_path, 'wb') as f:
                        await f.write(file_content)
                    print(f"[DEBUG] MinIO下载: 文件写入完成")
                    
                    logger.info(f"文件下载成功: {save_path}")
                    
                    return {
                        "success": True,
                        "local_path": save_path,
                        "filename": filename,
                        "size": len(file_content),
                        "content_type": response.headers.get('Content-Type')
                    }
                else:
                    error_text = await response.text()
                    error_msg = f"文件下载失败: HTTP {response.status}"
                    print(f"[DEBUG] MinIO下载: 下载失败 - 状态码: {response.status}")
                    print(f"[DEBUG] MinIO下载: 错误响应内容: {error_text}")
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg
                    }
    except Exception as e:
        error_msg = f"MinIO文件下载异常: {str(e)}"
        print(f"[DEBUG] MinIO下载: 发生异常: {error_msg}")
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

def generate_save_path(filename: str, user_id: int = None, category: str = None) -> str:
    """ai写的生成保存路径的脚本"""
    import uuid
    from datetime import datetime
    
    # 基础下载目录
    base_dir = "/tmp/downloads"  # 可以通过配置文件设置
    
    # 根据用户ID和分类创建子目录
    if user_id and category:
        sub_dir = os.path.join(base_dir, category, str(user_id))
    elif user_id:
        sub_dir = os.path.join(base_dir, "users", str(user_id))
    elif category:
        sub_dir = os.path.join(base_dir, category)
    else:
        sub_dir = os.path.join(base_dir, "general")
    
    # 生成唯一文件名（避免重名）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    name, ext = os.path.splitext(filename)
    unique_filename = f"{name}_{timestamp}_{unique_id}{ext}"
    
    return os.path.join(sub_dir, unique_filename)


class ChatPara(BaseModel):
    user_id:int
    username:str
    embedding_model:str
    large_language_model:str
    top_k:int
    web_search:str
    mode:str
    question:str
    conversation_id:int
    recent_messages_count: int = 3 # 这个默认是3，
@app.post("/api/chat")
async def chat(data:ChatPara):
    '''
    用例：
    接收到用户聊天请求
    用户ID: 3
    用户名: chen
    嵌入模型: text2vec-base
    大模型: ChatGLM-6B
    topk: 20
    是否联网搜索: notUse
    是否使用知识库（模式）: knowledgeQA
    问题: 你好啊
    对话id：23
    提取最近 6 条消息作为上下文
    [{'content': '？', 'role': 'user'}, {'content': '正在思考中...', 'role': 'assistant'}, {'content': '怎么样呢', 'role': 'user'}, {'content': '正在思考中...', 'role': 'assistant'}, {'content': '傻逼', 'role': 'user'}, {'content': '正在思考中...', 'role': 'assistant'}]
    成功获取对话上下文，消息数量: 29
    '''
    try:
        print(f"接收到用户聊天请求")
        print(f"用户ID: {data.user_id}")
        print(f"用户名: {data.username}")
        print(f"嵌入模型: {data.embedding_model}")
        print(f"大模型: {data.large_language_model}")
        print(f"topk: {data.top_k}")
        print(f"是否联网搜索: {data.web_search}")
        print(f"是否使用知识库（模式）: {data.mode}")
        print(f"问题: {data.question}")
        print(f"对话id：{data.conversation_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理数据时出错: {str(e)}")
        
    conversation_context = None
    if data.conversation_id:
        try:
                # 从本机获取对话上下文
            local_api_base="http://192.168.240.1:5000"    
            context_url = f"{local_api_base}/api/conversations/{data.conversation_id}/context" 
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(context_url)
                    
            if response.status_code == 200:
                conversation_context = response.json()
                if 'messages' in conversation_context:
                        all_messages = conversation_context['messages']
                        recent_count = min(data.recent_messages_count * 2, len(all_messages))
                        recent_messages = all_messages[-recent_count:] if recent_count > 0 else []# 这个是数据库查出来的直接结果，可能包含很多没用的
                        simplified_messages = []# 只有role和content 建议使用这个
                        for msg in recent_messages:
                            simplified_messages.append({
                                'content': msg.get('content', ''),
                                'role': msg.get('role', '')
                            })        
                print(f"提取最近 {len(recent_messages)} 条消息作为上下文")
                print(simplified_messages)
                print(f"成功获取对话上下文，消息数量: {conversation_context.get('message_count', 0)}")
            elif response.status_code == 404:
                print(f"对话不存在: {data.conversation_id}")
                conversation_context = None
            else:
                print(f"获取对话上下文失败，状态码: {response.status_code}")
                conversation_context = None
                    
        except httpx.TimeoutException:
            print(f"获取对话上下文超时: {data.conversation_id}")
            conversation_context = None
        except Exception as e:
            print(f"获取对话上下文异常: {str(e)}")
            conversation_context = None
    # 使用完整问答系统处理请求
    try:
        print(f"\n=== 第一步：接收并解析用户请求 ===")
        print(f"用户ID: {data.user_id}")
        print(f"用户名: {data.username}")
        print(f"嵌入模型: {data.embedding_model}")
        print(f"大语言模型: {data.large_language_model}")
        print(f"检索数量(top_k): {data.top_k}")
        print(f"联网搜索: {data.web_search}")
        print(f"知识库模式: {data.mode}")
        print(f"问题: {data.question}")
        print(f"对话ID: {data.conversation_id}")
        
        # 验证mode参数
        valid_modes = ["shared_knowledge", "private_knowledge", "entire_knowledge", "none_knowledge", "knowledgeQA"]
        if data.mode not in valid_modes:
            print(f"❌ 无效的mode参数: {data.mode}")
            return {
                "status": "error",
                "message": f"不支持的模式: {data.mode}。支持的模式: {', '.join(valid_modes[:-1])}",
                "user_id": data.user_id,
                "conversation_id": data.conversation_id
            }
        
        # 根据mode参数决定处理方式
        if data.mode in ["shared_knowledge", "private_knowledge", "entire_knowledge", "none_knowledge"]:
            print(f"\n🚀 执行知识库问答模式: {data.mode}")
            
            # 使用完整问答系统处理
            qa_results = qa_system.complete_qa_process(
                question=data.question,
                user_id=str(data.user_id),  # 确保user_id为字符串
                chat_history=simplified_messages if conversation_context else None,
                top_k=data.top_k,
                web_search=data.web_search.lower() == "use",
                mode=data.mode
            )
            
            print(f"\n=== 处理结果摘要 ===")
            print(f"原始问题: {qa_results.get('original_question', '')}")
            print(f"补全问题: {qa_results.get('completed_question', '')}")
            print(f"意图识别: {qa_results.get('intent', 'unknown')}")
            print(f"多查询数量: {len(qa_results.get('multi_queries', []))}")
            print(f"检索文档数: {qa_results.get('retrieved_docs_count', 0)}")
            print(f"  - 法律条文: {qa_results.get('law_docs_count', 0)} 个")
            print(f"  - 案例文档: {qa_results.get('case_docs_count', 0)} 个")
            print(f"重排序后文档数: {qa_results.get('reranked_docs_count', 0)}")
            print(f"网络搜索内容长度: {qa_results.get('web_content_length', 0)}")
            print(f"最终回答长度: {len(qa_results.get('final_answer', ''))}")
            
            return {
                "status": "success",
                "message": qa_results.get("final_answer", "处理完成"),
                "user_id": data.user_id,
                "conversation_id": data.conversation_id
            }
        else:
            # 兼容旧的mode参数或未知mode
            if data.mode == "knowledgeQA":
                # 兼容旧版本，默认使用shared_knowledge模式
                print(f"\n🔄 兼容模式：将knowledgeQA转换为shared_knowledge模式")
                qa_results = qa_system.complete_qa_process(
                    question=data.question,
                    user_id=str(data.user_id),
                    chat_history=simplified_messages if conversation_context else None,
                    top_k=data.top_k,
                    web_search=data.web_search.lower() == "use",
                    mode="shared_knowledge"
                )
                
                return {
                    "status": "success",
                    "message": qa_results.get("final_answer", "处理完成"),
                    "user_id": data.user_id,
                    "conversation_id": data.conversation_id
                }
            else:
                # 这里不应该到达，因为已经在开始验证了mode参数
                return {
                    "status": "error",
                    "message": f"内部错误：未处理的模式 {data.mode}",
                    "user_id": data.user_id,
                    "conversation_id": data.conversation_id
                }
            
    except Exception as e:
        print(f"❌ 完整问答流程异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"处理请求时发生错误: {str(e)}",
            "user_id": data.user_id,
            "conversation_id": data.conversation_id
        }


@app.post("/api/receive-knowledge")
async def receive_knowledge_upload(data: KnowledgeUploadData, background_tasks: BackgroundTasks):
    '''
    用例：
    接收到知识库上传数据:
    用户ID: 4
    用户名: ghz
    文件路径: law-documents/cases/9df800525c1e46ab8fd47593e83c2885.pdf
    文件名: 陈继昀_Facebook-Cambridge数据丑闻.pdf
    文件分类: case
    知识库类型: ['public', 'private']
    文件ID: 2
    执行动作: add
    '''
    try:
        # 处理接收到的数据
        print(f"接收到知识库上传数据:")
        print(f"用户ID: {data.user_id}")
        print(f"用户名: {data.username}")
        print(f"文件路径: law-documents/{data.file_path}")
        print(f"文件名: {data.filename}")
        print(f"文件分类: {data.file_category}")
        print(f"知识库类型: {str(data.knowledge_types)}")#公有或者是私有是一个列表['public'] ['private']或者是['public','private']
        print(f"文件ID: {data.file_id}")
        print(f"执行动作: {data.action}")
        

        # 数据验证
        if not data.file_path or not data.filename:
            print(f"❌ 数据格式错误: 文件路径或文件名为空")
            return JSONResponse(
                status_code=422,
                content={
                    "status": "error",
                    "message": "数据格式错误，请检查远程服务器配置",
                    "error_code": "INVALID_DATA",
                    "file_id": data.file_id,
                    "user_id": data.user_id
                }
            )

        data.file_path ="law-documents/"+data.file_path
        
        if data.action=="add":
            print("开始处理文件上传")
            try:
                # 同步处理上传操作，以便能够返回准确的成功/失败状态
                await process_new_knowledge(data)
                
                # 返回成功响应 - HTTP 200
                print(f"成功发送到远程服务器({data.file_id}): {{response.json()}}")
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success",
                        "message": f"文件 '{data.filename}' 上传成功！",
                        "file_id": data.file_id,
                        "user_id": data.user_id,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            except Exception as e:
                # 返回失败响应 - HTTP 500
                error_message = f"远程服务器返回错误: {str(e)}"
                print(f"❌ 发送到远程服务器失败: {error_message}")
                logger.error(f"文件上传失败 {data.file_id}: {str(e)}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "message": error_message,
                        "error_code": "UPLOAD_FAILED",
                        "file_id": data.file_id,
                        "user_id": data.user_id,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                        
        elif data.action=="cancel":
            print(f"[DEBUG] 开始处理cancel操作 - 用户ID: {data.user_id}, 文件ID: {data.file_id}, 文件名: {data.filename}")
            logger.info(f"开始处理cancel操作 - 用户ID: {data.user_id}, 文件ID: {data.file_id}, 文件名: {data.filename}")
            
            try:
                result = await new_intelligent_cancel(data)
                
                # 根据结果返回相应的状态码
                if result["status"] == "success":
                    response_content = {
                        "status": "success",
                        "message": result["message"],
                        "file_id": data.file_id,
                        "user_id": data.user_id,
                        "timestamp": datetime.now().isoformat()
                    }
                    if "remaining_permissions" in result:
                        response_content["remaining_permissions"] = result["remaining_permissions"]
                    return JSONResponse(status_code=200, content=response_content)
                else:
                    return JSONResponse(status_code=500, content={
                        "status": "error",
                        "message": result["message"],
                        "error_code": "DELETE_FAILED",
                        "file_id": data.file_id,
                        "user_id": data.user_id,
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as e:
                print(f"[DEBUG] cancel操作失败 - 错误: {str(e)}")
                logger.error(f"cancel操作失败 - 错误: {str(e)}", exc_info=True)
                
                # 返回删除失败响应 - HTTP 500
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "message": f"文件 '{data.filename}' 删除失败: {str(e)}",
                        "error_code": "DELETE_FAILED",
                        "file_id": data.file_id,
                        "user_id": data.user_id,
                        "timestamp": datetime.now().isoformat()
                    }
                )
        else:
            # 不支持的操作 - HTTP 422
            return JSONResponse(
                status_code=422,
                content={
                    "status": "error",
                    "message": f"不支持的操作: {data.action}",
                    "error_code": "UNSUPPORTED_ACTION",
                    "file_id": data.file_id,
                    "user_id": data.user_id
                }
            )
            
    except Exception as e:
        logger.error(f"处理知识库上传数据时发生错误: {str(e)}", exc_info=True)
        # 返回服务器内部错误 - HTTP 500
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"服务器内部错误: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10086)
