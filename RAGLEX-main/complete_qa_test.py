# -*- coding: utf-8 -*-
"""
完整问答系统测试函数
测试包括：问题补全、上下文补全、意图识别、多查询生成、BM25+向量检索、重排序、联网检索、最终回答生成
"""

import os
import sys
import numpy as np
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi

# 导入系统组件
from utils import (
    get_vectorstore, get_model_openai, get_memory, 
    rerank_documents_doc, get_embeder,
    get_law_vectorstore, get_case_vectorstore,
    search_law_documents, search_case_documents,
    index_all_documents_separated
)
from retriever import get_multi_query_law_retiever
from prompt import (
    PRE_QUESTION_PROMPT, CHECK_INTENT_PROMPT, 
    LAW_PROMPT_HISTORY, FRIENDLY_REJECTION_PROMPT,
    MULTI_QUERY_PROMPT_TEMPLATE
)
from combine import combine_law_docs
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
    import os
    
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
from langchain_core.documents import Document
from langchain.schema.output_parser import StrOutputParser
from langchain.memory import ConversationBufferMemory
from config import config

# 加载环境变量
load_dotenv()

class CompleteQASystemTester:
    """
    完整问答系统测试类
    """
    
    def __init__(self, load_case_data=True):
        """初始化测试系统"""
        print("🚀 初始化完整问答系统测试器...")
        
        # 初始化组件
        self.vectorstore = get_vectorstore(config.LAW_VS_COLLECTION_NAME)
        self.law_vectorstore = get_law_vectorstore()
        self.case_vectorstore = get_case_vectorstore()
        self.model = get_model_openai()
        self.memory = get_memory()
        
        # 如果需要加载案例数据
        if load_case_data:
            self._load_case_data()
        
        # 初始化BM25索引
        self.bm25_index = self._create_bm25_index()
        
        # 初始化多查询检索器
        vs_retriever = self.vectorstore.as_retriever(search_kwargs={"k": config.LAW_VS_SEARCH_K})
        self.multi_query_retriever = get_multi_query_law_retiever(vs_retriever, self.model)
        
        print("✅ 系统初始化完成")
    
    def _load_case_data(self):
        """加载案例数据到数据库"""
        print("📚 检查并加载案例数据...")
        try:
            # 检查案例数据库是否已有数据
            case_docs = self.case_vectorstore.similarity_search("", k=1)
            if case_docs:
                print(f"✅ 案例数据库已存在数据，包含文档数量: {len(case_docs)}")
                return
            
            print("📥 案例数据库为空，开始加载案例数据...")
            
            # 加载文档
            from loader import load_law_documents_only, load_case_documents_only
            
            print("📚 加载法律条文文档...")
            law_docs = load_law_documents_only()
            print(f"✅ 加载了 {len(law_docs)} 个法律条文文档")
            
            print("⚖️  加载案例文档...")
            case_docs = load_case_documents_only()
            print(f"✅ 加载了 {len(case_docs)} 个案例文档")
            
            # 使用分离索引功能加载数据
            index_all_documents_separated(law_docs, case_docs)
            print("✅ 案例数据加载完成")
            
        except Exception as e:
            print(f"❌ 案例数据加载失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _create_bm25_index(self) -> BM25Okapi:
        """创建BM25索引"""
        print("📚 创建BM25索引...")
        try:
            # 获取所有文档
            all_docs = self.vectorstore.similarity_search("", k=1000)  # 获取大量文档用于BM25
            
            # 预处理文档文本
            tokenized_docs = []
            for doc in all_docs:
                # 清理文本，保留中文分词
                text = doc.page_content.replace('\t', ' ').replace('\n', ' ')
                # 对中文文本进行字符级分词
                tokens = list(text.replace(' ', ''))
                # 过滤空字符
                tokens = [token for token in tokens if token.strip()]
                if tokens:  # 确保不为空
                    tokenized_docs.append(tokens)
            
            bm25 = BM25Okapi(tokenized_docs)
            print(f"✅ BM25索引创建完成，包含 {len(tokenized_docs)} 个文档")
            return bm25
        except Exception as e:
            print(f"❌ BM25索引创建失败: {e}")
            return None
    
    def step1_question_completion(self, question: str, chat_history: str = "") -> str:
        """步骤1: 问题补全"""
        print("\n🔍 步骤1: 问题补全")
        print(f"原始问题: {question}")
        
        try:
            # 构建输入
            input_data = {
                "question": question,
                "chat_history": chat_history
            }
            
            # 执行问题补全
            chain = PRE_QUESTION_PROMPT | self.model | StrOutputParser()
            completed_question = chain.invoke(input_data)
            
            print(f"补全后问题: {completed_question}")
            return completed_question
        except Exception as e:
            print(f"❌ 问题补全失败: {e}")
            return question
    
    def step2_intent_recognition(self, question: str) -> str:
        """步骤2: 意图识别"""
        print("\n🎯 步骤2: 意图识别")
        
        try:
            # 执行意图识别
            chain = CHECK_INTENT_PROMPT | self.model | StrOutputParser()
            intent = chain.invoke({"question": question}).strip().lower()
            
            print(f"识别意图: {intent}")
            return intent
        except Exception as e:
            print(f"❌ 意图识别失败: {e}")
            return "other"
    
    def step3_multi_query_generation(self, question: str) -> List[str]:
        """步骤3: 生成多查询"""
        print("\n🔄 步骤3: 生成多查询")
        
        try:
            # 执行多查询生成
            chain = MULTI_QUERY_PROMPT_TEMPLATE | self.model | StrOutputParser()
            multi_queries_text = chain.invoke({"question": question})
            
            # 解析多个查询
            queries = [line.strip() for line in multi_queries_text.strip().split("\n") if line.strip()]
            
            print("生成的多查询:")
            for i, query in enumerate(queries, 1):
                print(f"  {i}. {query}")
            
            return queries
        except Exception as e:
            print(f"❌ 多查询生成失败: {e}")
            return [question]
    
    def step4_separated_retrieval(self, question: str, law_k: int = 10, case_k: int = 5) -> List[Document]:
        """步骤4: 分离检索 - 先检索法律条文，再检索案例"""
        print("\n📖 步骤4: 分离检索 (法律条文 + 案例)")
        print(f"查询问题: {question}")
        print(f"法律条文检索数量: {law_k}")
        print(f"案例检索数量: {case_k}")
        
        try:
            # 4.1 法律条文检索阶段
            print("\n  4.1 法律条文检索阶段")
            print("  " + "-" * 30)
            
            law_docs = search_law_documents(
                question=question,
                k=law_k,
                use_rerank=True
            )
            
            print(f"  法律条文检索获得 {len(law_docs)} 个文档")
            
            # 显示法律条文检索前3个结果
            print("  法律条文检索前3个结果:")
            for i, doc in enumerate(law_docs[:3]):
                preview = doc.page_content[:80] + "..." if len(doc.page_content) > 80 else doc.page_content
                doc_type = doc.metadata.get('doc_type', '未知')
                print(f"    {i+1}. [{doc_type}] {preview}")
            
            # 4.2 案例检索阶段
            print("\n  4.2 案例检索阶段")
            print("  " + "-" * 30)
            
            case_docs = search_case_documents(
                question=question,
                k=case_k,
                use_rerank=True
            )
            
            print(f"  案例检索获得 {len(case_docs)} 个文档")
            
            # 显示案例检索前3个结果（显示提取的关键部分）
            print("  案例检索前3个结果（已提取关键部分）:")
            for i, doc in enumerate(case_docs[:3]):
                # 显示案例的关键部分预览
                content_lines = doc.page_content.split('\n')
                preview_lines = []
                for line in content_lines[:5]:  # 显示前5行
                    if line.strip():
                        preview_lines.append(line.strip())
                preview = ' | '.join(preview_lines)
                if len(preview) > 100:
                    preview = preview[:100] + "..."
                
                doc_type = doc.metadata.get('doc_type', '未知')
                court = doc.metadata.get('court', '未知法院')
                print(f"    {i+1}. [{doc_type}] [{court}] {preview}")
                
                # 显示包含的关键部分
                sections = []
                if '## 基本案情' in doc.page_content:
                    sections.append('基本案情')
                if '## 裁判理由' in doc.page_content:
                    sections.append('裁判理由')
                if '## 裁判要旨' in doc.page_content:
                    sections.append('裁判要旨')
                if '## 法律条文' in doc.page_content:
                    sections.append('法律条文')
                print(f"       包含部分: {', '.join(sections)}")
            
            # 4.3 分离处理结果
            print("\n  4.3 分离处理结果")
            print("  " + "-" * 30)
            
            # 返回分离的结果字典，而不是合并的列表
            separated_results = {
                'law_docs': law_docs,
                'case_docs': case_docs,
                'total_count': len(law_docs) + len(case_docs)
            }
            
            print(f"  法律条文文档: {len(law_docs)} 个")
            print(f"  案例文档: {len(case_docs)} 个（已提取关键部分）")
            print(f"  总文档数量: {separated_results['total_count']} 个")
            
            return separated_results
                
        except Exception as e:
            print(f"❌ 分离检索失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _fusion_retrieval(self, query: str, k: int = 5, alpha: float = 0.5) -> List[Document]:
        """融合检索函数（参考testbm25.py实现）"""
        try:
            # 获取所有文档
            all_docs = self.vectorstore.similarity_search("", k=1000)
            chunk_count = len(all_docs)
            
            # 获取BM25分数 - 使用正确的分词方式
            query_tokens = list(query.replace(' ', ''))
            query_tokens = [token for token in query_tokens if token.strip()]
            bm25_scores = self.bm25_index.get_scores(query_tokens)
            
            # 确保BM25分数数组长度与文档数量一致
            if len(bm25_scores) != chunk_count:
                print(f"    ⚠️ BM25分数数量({len(bm25_scores)})与文档数量({chunk_count})不匹配")
                # 调整数组长度
                if len(bm25_scores) > chunk_count:
                    bm25_scores = bm25_scores[:chunk_count]
                else:
                    # 补齐为0
                    bm25_scores = np.pad(bm25_scores, (0, chunk_count - len(bm25_scores)), 'constant')
            
            # 使用向量搜索获取相关文档及其分数
            vector_results = self.vectorstore.similarity_search_with_score(query, k=chunk_count)
            
            # 归一化分数
            vector_scores = np.array([score for _, score in vector_results])
            # 向量分数转换（距离越小越好，转换为相似度）
            if np.max(vector_scores) > np.min(vector_scores):
                vector_scores = 1 - (vector_scores - np.min(vector_scores)) / (np.max(vector_scores) - np.min(vector_scores))
            else:
                vector_scores = np.ones_like(vector_scores)
            
            # BM25分数归一化
            if np.max(bm25_scores) > np.min(bm25_scores):
                bm25_scores = (bm25_scores - np.min(bm25_scores)) / (np.max(bm25_scores) - np.min(bm25_scores))
            else:
                bm25_scores = np.zeros_like(bm25_scores)
            
            print(f"    向量分数归一化范围: {np.min(vector_scores):.4f} - {np.max(vector_scores):.4f}")
            print(f"    BM25分数归一化范围: {np.min(bm25_scores):.4f} - {np.max(bm25_scores):.4f}")
            
            # 结合分数
            combined_scores = alpha * vector_scores + (1 - alpha) * bm25_scores
            print(f"    融合权重: 向量={alpha}, BM25={1-alpha}")
            print(f"    融合分数范围: {np.min(combined_scores):.4f} - {np.max(combined_scores):.4f}")
            
            # 排序文档
            sorted_indices = np.argsort(combined_scores)[::-1]
            
            # 返回前k个文档
            return [all_docs[i] for i in sorted_indices[:k]]
            
        except Exception as e:
            print(f"    ❌ 融合检索失败: {e}")
            import traceback
            traceback.print_exc()
            # 降级到向量检索
            return self.vectorstore.similarity_search(query, k=k)
    
    def step5_reranking(self, question: str, docs: List[Document], top_k: int = 10) -> List[Document]:
        """步骤5: 文档重排序"""
        print("\n🔄 步骤5: 文档重排序")
        print(f"输入文档数量: {len(docs)}")
        print(f"目标重排序数量: {top_k}")
        print(f"重排序问题: {question}")
        
        try:
            print("\n  5.1 重排序前文档预览")
            print("  " + "-" * 30)
            for i, doc in enumerate(docs[:5]):
                preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                print(f"    {i+1}. {preview}")
            
            print("\n  5.2 执行重排序")
            print("  " + "-" * 30)
            from utils import rerank_existing_documents
            print("  正在使用FlagReranker进行重排序...")
            print(f"  输入文档数量: {len(docs)}")
            print(f"  重排序模型路径: {config.RERANKER_PATH}")
            
            # 检查模型路径是否存在
            import os
            if not os.path.exists(config.RERANKER_PATH):
                print(f"  ❌ 重排序模型路径不存在: {config.RERANKER_PATH}")
                return docs[:top_k]
            
            reranked_docs = rerank_existing_documents(question, docs, top_k)
            print(f"  重排序函数返回文档数量: {len(reranked_docs)}")
            
            print(f"  重排序完成，返回前 {len(reranked_docs)} 个文档")
            
            print("\n  5.3 重排序后文档预览")
            print("  " + "-" * 30)
            for i, doc in enumerate(reranked_docs[:5]):
                preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                print(f"    {i+1}. {preview}")
            
            return reranked_docs
            
        except Exception as e:
            print(f"❌ 重排序失败: {e}")
            import traceback
            traceback.print_exc()
            print(f"  回退到原始文档前{top_k}个")
            return docs[:top_k]
    
    def step5_separated_reranking(self, question: str, separated_results: Dict, law_top_k: int = 6, case_top_k: int = 4) -> List[Document]:
        """步骤5: 分离重排序 - 分别对法律条文和案例进行重排序"""
        print("\n🔄 步骤5: 分离重排序")
        print(f"重排序问题: {question}")
        print(f"法律条文目标数量: {law_top_k}")
        print(f"案例目标数量: {case_top_k}")
        
        try:
            law_docs = separated_results['law_docs']
            case_docs = separated_results['case_docs']
            
            print(f"\n输入文档统计:")
            print(f"  法律条文: {len(law_docs)} 个")
            print(f"  案例文档: {len(case_docs)} 个")
            
            # 5.1 法律条文重排序
            print("\n  5.1 法律条文重排序")
            print("  " + "-" * 30)
            
            reranked_law_docs = []
            if law_docs:
                print(f"  正在对 {len(law_docs)} 个法律条文进行重排序...")
                from utils import rerank_existing_documents
                reranked_law_docs = rerank_existing_documents(question, law_docs, law_top_k)
                print(f"  法律条文重排序完成，获得 {len(reranked_law_docs)} 个文档")
                
                # 显示法律条文重排序结果预览
                print("  法律条文重排序前3个结果:")
                for i, doc in enumerate(reranked_law_docs[:3]):
                    preview = doc.page_content[:80] + "..." if len(doc.page_content) > 80 else doc.page_content
                    doc_type = doc.metadata.get('doc_type', '未知')
                    print(f"    {i+1}. [{doc_type}] {preview}")
            else:
                print("  无法律条文需要重排序")
            
            # 5.2 案例重排序
            print("\n  5.2 案例重排序")
            print("  " + "-" * 30)
            
            reranked_case_docs = []
            if case_docs:
                print(f"  正在对 {len(case_docs)} 个案例进行重排序...")
                from utils import rerank_existing_documents
                reranked_case_docs = rerank_existing_documents(question, case_docs, case_top_k)
                print(f"  案例重排序完成，获得 {len(reranked_case_docs)} 个文档")
                
                # 显示案例重排序结果预览
                print("  案例重排序前3个结果（已提取关键部分）:")
                for i, doc in enumerate(reranked_case_docs[:3]):
                    content_lines = doc.page_content.split('\n')
                    preview_lines = []
                    for line in content_lines[:3]:
                        if line.strip():
                            preview_lines.append(line.strip())
                    preview = ' | '.join(preview_lines)
                    if len(preview) > 100:
                        preview = preview[:100] + "..."
                    
                    doc_type = doc.metadata.get('doc_type', '未知')
                    court = doc.metadata.get('court', '未知法院')
                    print(f"    {i+1}. [{doc_type}] [{court}] {preview}")
                    
                    # 显示包含的关键部分
                    sections = []
                    if '## 基本案情' in doc.page_content:
                        sections.append('基本案情')
                    if '## 裁判理由' in doc.page_content:
                        sections.append('裁判理由')
                    if '## 裁判要旨' in doc.page_content:
                        sections.append('裁判要旨')
                    if '## 法律条文' in doc.page_content:
                        sections.append('法律条文')
                    print(f"       包含部分: {', '.join(sections)}")
            else:
                print("  无案例需要重排序")
            
            # 5.3 合并重排序结果
            print("\n  5.3 合并重排序结果")
            print("  " + "-" * 30)
            
            # 法律条文在前，案例在后
            final_docs = reranked_law_docs + reranked_case_docs
            
            print(f"  最终文档数量: {len(final_docs)}")
            print(f"  其中法律条文: {len(reranked_law_docs)} 个")
            print(f"  其中案例文档: {len(reranked_case_docs)} 个（已提取关键部分）")
            
            return final_docs
            
        except Exception as e:
            print(f"❌ 分离重排序失败: {e}")
            import traceback
            traceback.print_exc()
            # 回退到原始文档
            law_docs = separated_results.get('law_docs', [])
            case_docs = separated_results.get('case_docs', [])
            return law_docs[:law_top_k] + case_docs[:case_top_k]
    
    def step6_web_search(self, question: str, num_results: int = 3) -> str:
        """步骤6: 联网检索"""
        print("\n🌐 步骤6: 联网检索")
        print(f"搜索问题: {question}")
        print(f"目标结果数量: {num_results}")
        
        try:
            print("\n  6.1 执行网络搜索")
            print("  " + "-" * 30)
            print("  正在使用Serper API进行网络搜索...")
            
            web_content = search_web_serper(question, num_results)
            
            if web_content:
                # 检查web_content是否包含多个结果（通过换行符分割）
                if "\n\n" in web_content:
                    # 按双换行符分割多个结果
                    results_list = [r.strip() for r in web_content.split("\n\n") if r.strip()]
                else:
                    # 单个结果
                    results_list = [web_content.strip()]
                
                print(f"  网络搜索完成，获得 {len(results_list)} 个结果")
                
                print("\n  6.2 网络搜索结果预览")
                print("  " + "-" * 30)
                for i, result in enumerate(results_list[:3], 1):
                    if result:
                        preview = result[:150] + "..." if len(result) > 150 else result
                        print(f"    结果{i}: {preview}")
                        print("    " + "-" * 20)
                
                print(f"\n  网络搜索内容总长度: {len(web_content)} 字符")
                return web_content
            else:
                print("  ⚠️ 网络搜索未返回结果")
                return ""
                
        except Exception as e:
            print(f"❌ 联网检索失败: {e}")
            import traceback
            traceback.print_exc()
            return "网络搜索不可用"
    
    def step7_final_answer_generation(self, question: str, intent: str, context_docs: List[Document] = None, web_content: str = "") -> str:
        """步骤7: 最终回答生成"""
        print("\n💡 步骤7: 最终回答生成")
        print(f"问题: {question}")
        print(f"意图识别结果: {intent}")
        print(f"上下文文档数量: {len(context_docs) if context_docs else 0}")
        print(f"网络内容长度: {len(web_content)} 字符")
        
        try:
            if intent == "law":
                print("\n  7.1 法律问答处理")
                print("  " + "-" * 30)
                
                # 使用法律问答链
                from chain import get_law_chain
                print("  正在初始化法律问答链...")
                from callback import OutCallbackHandler
                out_callback = OutCallbackHandler()
                law_chain = get_law_chain(config, out_callback)
                
                # 准备上下文
                print("  正在准备上下文信息...")
                context = ""
                if context_docs:
                    context = "\n\n".join([doc.page_content for doc in context_docs])
                    print(f"  本地知识库上下文长度: {len(context)} 字符")
                
                if web_content:
                    context += "\n\n网络搜索结果:\n" + web_content
                    print(f"  添加网络搜索内容后总长度: {len(context)} 字符")
                
                print("  正在调用法律问答模型...")
                response = law_chain.invoke({
                    "question": question,
                    "context": context
                })
                
                # 从响应中提取answer字段
                if isinstance(response, dict) and 'answer' in response:
                    final_answer = response['answer']
                else:
                    final_answer = str(response)
                
                print(f"  法律问答完成，回答长度: {len(final_answer)} 字符")
                
                # 显示回答预览
                print("\n  7.2 法律回答预览")
                print("  " + "-" * 30)
                preview = final_answer[:200] + "..." if len(final_answer) > 200 else final_answer
                print(f"  {preview}")
                
                return final_answer
            else:
                print("\n  7.1 非法律问题处理")
                print("  " + "-" * 30)
                
                # 非法律问题的友好拒绝
                from prompt import FRIENDLY_REJECTION_PROMPT
                from utils import get_model
                
                print("  正在生成友好拒绝回答...")
                model = get_model()
                response = model.invoke(FRIENDLY_REJECTION_PROMPT.format(question=question))
                
                final_response = response.content if hasattr(response, 'content') else str(response)
                print(f"  友好拒绝回答完成，长度: {len(final_response)} 字符")
                
                # 显示回答预览
                print("\n  7.2 拒绝回答预览")
                print("  " + "-" * 30)
                preview = final_response[:200] + "..." if len(final_response) > 200 else final_response
                print(f"  {preview}")
                
                return final_response
                
        except Exception as e:
            print(f"❌ 回答生成失败: {e}")
            import traceback
            traceback.print_exc()
            return "抱歉，系统暂时无法回答您的问题。"
    
    def complete_qa_test(self, question: str, chat_history: str = "") -> Dict[str, Any]:
        """完整问答系统测试"""
        print("="*80)
        print("🧪 开始完整问答系统测试")
        print("="*80)
        
        results = {
            "original_question": question,
            "chat_history": chat_history
        }
        
        # 步骤1: 问题补全
        completed_question = self.step1_question_completion(question, chat_history)
        results["completed_question"] = completed_question
        
        # 步骤2: 意图识别
        intent = self.step2_intent_recognition(completed_question)
        results["intent"] = intent
        
        # 如果是法律问题，继续完整流程
        if intent == "law":
            # 步骤3: 多查询生成
            multi_queries = self.step3_multi_query_generation(completed_question)
            results["multi_queries"] = multi_queries
            
            # 步骤4: 分离检索 (法律条文 + 案例)
            separated_results = self.step4_separated_retrieval(completed_question)
            results["retrieved_docs_count"] = separated_results['total_count']
            results["law_docs_count"] = len(separated_results['law_docs'])
            results["case_docs_count"] = len(separated_results['case_docs'])
            
            # 步骤5: 分离重排序 - 分别对法律条文和案例进行重排序
            reranked_docs = self.step5_separated_reranking(completed_question, separated_results)
            results["reranked_docs"] = reranked_docs
            results["reranked_docs_count"] = len(reranked_docs)
            
            # 步骤6: 联网检索
            web_content = self.step6_web_search(completed_question)
            results["web_content"] = web_content
            
            # 步骤7: 最终回答生成
            final_answer = self.step7_final_answer_generation(
                completed_question, intent, reranked_docs, web_content
            )
            results["final_answer"] = final_answer
        else:
            # 非法律问题直接生成友好回应
            results["multi_queries"] = []
            results["retrieved_docs_count"] = 0
            results["reranked_docs"] = []
            results["web_content"] = ""
            
            final_answer = self.step7_final_answer_generation(
                completed_question, intent, [], ""
            )
            results["final_answer"] = final_answer
        
        # 保存到记忆
        self.memory.save_context(
            {"question": completed_question}, 
            {"answer": results["final_answer"]}
        )
        
        print("\n" + "="*80)
        print("🎉 完整问答系统测试完成")
        print("="*80)
        
        return results
    
    def print_test_summary(self, results: Dict[str, Any]):
        """打印测试结果摘要"""
        print("\n" + "=" * 80)
        print("📊 测试结果摘要")
        print("=" * 80)
        
        # 基本信息
        print(f"🕐 测试时间: {results.get('timestamp', 'N/A')}")
        print(f"❓ 原始问题: {results['original_question']}")
        print(f"💬 对话历史: {results.get('chat_history', '无') or '无'}")
        
        print("\n" + "-" * 40)
        print("🔍 处理流程统计")
        print("-" * 40)
        
        print(f"✏️  问题补全: {results.get('completed_question', 'N/A')}")
        print(f"🎯 意图识别: {results.get('intent', 'N/A')}")
        
        multi_queries = results.get('multi_queries', [])
        print(f"🔄 多查询生成: {len(multi_queries)} 个查询")
        if multi_queries:
            for i, query in enumerate(multi_queries[:3], 1):
                print(f"    {i}. {query}")
            if len(multi_queries) > 3:
                print(f"    ... 还有 {len(multi_queries) - 3} 个查询")
        
        print(f"📚 分离检索: {results.get('retrieved_docs_count', 0)} 个文档 (法律条文+案例)")
        print(f"🔄 重排序后: {results.get('reranked_docs_count', 0)} 个文档")
        print(f"🌐 网络搜索: {results.get('web_content_length', 0)} 字符")
        print(f"💡 最终回答: {results.get('final_answer_length', 0)} 字符")
        
        # 错误信息
        if 'error' in results:
            print(f"\n❌ 错误信息: {results['error']}")
        
        print("\n" + "-" * 40)
        print("📝 最终回答")
        print("-" * 40)
        final_answer = results.get('final_answer', '无回答')
        if len(final_answer) > 500:
            print(final_answer[:500] + "\n... (回答已截断，完整内容请查看返回结果)")
        else:
            print(final_answer)
        
        print("\n" + "=" * 80)


def run_test_cases():
    """运行测试用例"""
    tester = CompleteQASystemTester()
    
    # 测试用例
    test_cases = [
        {
            "question": "合同违约怎么处理？",
            "chat_history": "",
            "description": "法律问题测试 - 分离检索(法律条文+案例)"
        },
        {
            "question": "交通事故责任如何认定？",
            "chat_history": "",
            "description": "法律问题测试 - 交通事故相关案例检索"
        },
        {
            "question": "今天天气怎么样？",
            "chat_history": "",
            "description": "非法律问题测试"
        },
        {
            "question": "这种情况下的赔偿标准是什么？",
            "chat_history": "Human: 我的车被追尾了\nAI: 根据交通事故处理相关法律...",
            "description": "上下文依赖问题测试 - 分离检索"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 测试用例 {i}: {test_case['description']}")
        
        results = tester.complete_qa_test(
            test_case["question"], 
            test_case["chat_history"]
        )
        
        tester.print_test_summary(results)       
        
        print("\n" + "="*100)


if __name__ == "__main__":
    print("🚀 启动完整问答系统测试")
    
    # 检查环境变量
    required_env_vars = ["OPENAI_API_KEY", "SERPER_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 缺少环境变量: {', '.join(missing_vars)}")
        print("请在.env文件中配置这些变量")
    else:
        print("✅ 环境变量检查通过")
        
        try:
            run_test_cases()
        except KeyboardInterrupt:
            print("\n⏹️ 测试被用户中断")
        except Exception as e:
            print(f"\n❌ 测试过程中发生错误: {e}")
            import traceback
            traceback.print_exc()