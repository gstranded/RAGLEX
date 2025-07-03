#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库重新加载脚本
用于在法律条文和案例文件路径变更后，重新加载数据到向量数据库中
"""

import os
import sys
from typing import List, Dict
from langchain.docstore.document import Document

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from loader import load_all_documents_separated, load_law_documents_only, load_case_documents_only
from utils import (
    clear_all_separated_vectorstores, 
    index_all_documents_separated,
    clear_law_vectorstore,
    clear_case_vectorstore,
    index_law_documents,
    index_case_documents
)
from splitter import MdSplitter

def reload_all_databases(clear_existing: bool = True) -> Dict[str, Dict]:
    """
    重新加载所有数据库（法律条文和案例）
    
    Args:
        clear_existing: 是否清除现有数据库，默认为True
    
    Returns:
        索引结果统计
    """
    print("=" * 50)
    print("开始重新加载所有数据库")
    print("=" * 50)
    
    # 1. 清除现有数据库（如果需要）
    if clear_existing:
        print("\n1. 清除现有向量数据库...")
        clear_all_separated_vectorstores()
        print("现有数据库已清除")
    
    # 2. 加载文档
    print("\n2. 从新路径加载文档...")
    print(f"法律条文路径: {config.LAW_BOOK_PATH}")
    print(f"私有案例路径: {config.PRIVATE_CASE_DOCS_PATH}")
    print(f"共有案例路径: {config.PUBLIC_CASE_DOCS_PATH}")
    
    try:
        law_docs, case_docs = load_all_documents_separated()
        print(f"成功加载法律条文文档: {len(law_docs)} 个")
        print(f"成功加载案例文档: {len(case_docs)} 个")
    except Exception as e:
        print(f"加载文档时出错: {e}")
        return {}
    
    # 3. 分割文档
    print("\n3. 分割文档...")
    try:
        law_splitter = MdSplitter(chunk_size=config.LAW_BOOK_CHUNK_SIZE, chunk_overlap=config.LAW_BOOK_CHUNK_OVERLAP)
        case_splitter = MdSplitter(chunk_size=config.CASE_CHUNK_SIZE, chunk_overlap=config.CASE_CHUNK_OVERLAP)
        
        law_chunks = law_splitter.split_documents(law_docs)
        case_chunks = case_splitter.split_documents(case_docs)
        print(f"法律条文分割后: {len(law_chunks)} 个块")
        print(f"案例文档分割后: {len(case_chunks)} 个块")
    except Exception as e:
        print(f"分割文档时出错: {e}")
        return {}
    
    # 4. 索引到向量数据库
    print("\n4. 索引到向量数据库...")
    try:
        results = index_all_documents_separated(law_chunks, case_chunks, show_progress=True)
        print("\n索引完成！")
        
        # 显示结果统计
        print("\n=== 索引结果统计 ===")
        for db_name, stats in results.items():
            print(f"\n{db_name}:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        return results
    except Exception as e:
        print(f"索引文档时出错: {e}")
        return {}

def reload_law_database_only(clear_existing: bool = True) -> Dict:
    """
    仅重新加载法律条文数据库
    
    Args:
        clear_existing: 是否清除现有数据库，默认为True
    
    Returns:
        索引结果统计
    """
    print("=" * 50)
    print("重新加载法律条文数据库")
    print("=" * 50)
    
    # 1. 清除现有法律条文数据库
    if clear_existing:
        print("\n1. 清除现有法律条文向量数据库...")
        clear_law_vectorstore()
    
    # 2. 加载法律条文文档
    print("\n2. 加载法律条文文档...")
    print(f"法律条文路径: {config.LAW_BOOK_PATH}")
    
    try:
        law_docs = load_law_documents_only()
        print(f"成功加载法律条文文档: {len(law_docs)} 个")
    except Exception as e:
        print(f"加载法律条文文档时出错: {e}")
        return {}
    
    # 3. 分割文档
    print("\n3. 分割法律条文文档...")
    try:
        law_splitter = MdSplitter(chunk_size=config.LAW_BOOK_CHUNK_SIZE, chunk_overlap=config.LAW_BOOK_CHUNK_OVERLAP)
        law_chunks = law_splitter.split_documents(law_docs)
        print(f"法律条文分割后: {len(law_chunks)} 个块")
    except Exception as e:
        print(f"分割法律条文文档时出错: {e}")
        return {}
    
    # 4. 索引到向量数据库
    print("\n4. 索引法律条文到向量数据库...")
    try:
        result = index_law_documents(law_chunks, show_progress=True)
        print("\n法律条文索引完成！")
        
        # 显示结果统计
        print("\n=== 法律条文索引结果统计 ===")
        for key, value in result.items():
            print(f"  {key}: {value}")
        
        return result
    except Exception as e:
        print(f"索引法律条文时出错: {e}")
        return {}

def reload_case_database_only(clear_existing: bool = True) -> Dict:
    """
    仅重新加载案例数据库
    
    Args:
        clear_existing: 是否清除现有数据库，默认为True
    
    Returns:
        索引结果统计
    """
    print("=" * 50)
    print("重新加载案例数据库")
    print("=" * 50)
    
    # 1. 清除现有案例数据库
    if clear_existing:
        print("\n1. 清除现有案例向量数据库...")
        clear_case_vectorstore()
    
    # 2. 加载案例文档
    print("\n2. 加载案例文档...")
    print(f"私有案例路径: {config.PRIVATE_CASE_DOCS_PATH}")
    print(f"共有案例路径: {config.PUBLIC_CASE_DOCS_PATH}")
    
    try:
        case_docs = load_case_documents_only()
        print(f"成功加载案例文档: {len(case_docs)} 个")
    except Exception as e:
        print(f"加载案例文档时出错: {e}")
        return {}
    
    # 3. 分割文档
    print("\n3. 分割案例文档...")
    try:
        case_splitter = MdSplitter(chunk_size=config.CASE_CHUNK_SIZE, chunk_overlap=config.CASE_CHUNK_OVERLAP)
        case_chunks = case_splitter.split_documents(case_docs)
        print(f"案例文档分割后: {len(case_chunks)} 个块")
    except Exception as e:
        print(f"分割案例文档时出错: {e}")
        return {}
    
    # 4. 索引到向量数据库
    print("\n4. 索引案例到向量数据库...")
    try:
        result = index_case_documents(case_chunks, show_progress=True)
        print("\n案例索引完成！")
        
        # 显示结果统计
        print("\n=== 案例索引结果统计 ===")
        for key, value in result.items():
            print(f"  {key}: {value}")
        
        return result
    except Exception as e:
        print(f"索引案例时出错: {e}")
        return {}

def check_file_paths() -> bool:
    """
    检查配置的文件路径是否存在
    
    Returns:
        所有路径都存在返回True，否则返回False
    """
    print("检查文件路径...")
    
    law_path = config.LAW_BOOK_PATH
    private_case_path = config.PRIVATE_CASE_DOCS_PATH
    public_case_path = config.PUBLIC_CASE_DOCS_PATH
    
    law_exists = os.path.exists(law_path)
    private_case_exists = os.path.exists(private_case_path)
    public_case_exists = os.path.exists(public_case_path)
    
    print(f"法律条文路径 ({law_path}): {'存在' if law_exists else '不存在'}")
    print(f"私有案例路径 ({private_case_path}): {'存在' if private_case_exists else '不存在'}")
    print(f"共有案例路径 ({public_case_path}): {'存在' if public_case_exists else '不存在'}")
    
    if not law_exists:
        print(f"警告: 法律条文路径不存在: {law_path}")
    if not private_case_exists:
        print(f"警告: 私有案例路径不存在: {private_case_path}")
    if not public_case_exists:
        print(f"警告: 共有案例路径不存在: {public_case_path}")
    
    # 至少法律条文路径和一个案例路径存在即可
    case_exists = private_case_exists or public_case_exists
    return law_exists and case_exists

def main():
    """
    主函数 - 提供交互式选择
    """
    print("数据库重新加载工具")
    print("=" * 30)
    
    # 检查路径
    if not check_file_paths():
        print("\n错误: 部分文件路径不存在，请检查config.py中的路径配置")
        return
    
    print("\n请选择操作:")
    print("1. 重新加载所有数据库（法律条文 + 案例）")
    print("2. 仅重新加载法律条文数据库")
    print("3. 仅重新加载案例数据库")
    print("4. 退出")
    
    while True:
        try:
            choice = input("\n请输入选择 (1-4): ").strip()
            
            if choice == "1":
                reload_all_databases()
                break
            elif choice == "2":
                reload_law_database_only()
                break
            elif choice == "3":
                reload_case_database_only()
                break
            elif choice == "4":
                print("退出程序")
                break
            else:
                print("无效选择，请输入1-4")
        except KeyboardInterrupt:
            print("\n\n程序被用户中断")
            break
        except Exception as e:
            print(f"发生错误: {e}")
            break

if __name__ == "__main__":
    main()