# coding: utf-8


from pathlib import Path


class Config:
    # 法律文档配置
    LAW_BOOK_PATH = "./law_docs/法律条文"
    LAW_BOOK_CHUNK_SIZE = 100
    LAW_BOOK_CHUNK_OVERLAP = 20
    LAW_VS_COLLECTION_NAME = "law"
    LAW_VS_SEARCH_K = 2

    # 案例文档配置
    CASE_DOCS_PATH = "./law_docs/案例"  # 保持兼容性，但实际会使用下面的路径
    PRIVATE_CASE_DOCS_PATH = "./law_docs/私有案例"
    PUBLIC_CASE_DOCS_PATH = "./law_docs/共有案例"
    CASE_CHUNK_SIZE = 200
    CASE_CHUNK_OVERLAP = 50
    
    # 统一向量存储配置
    UNIFIED_COLLECTION_NAME = "law_and_cases"
    UNIFIED_SEARCH_K = 5
    
    # 分离的向量存储配置
    LAW_DOCUMENTS_COLLECTION = "law_documents"
    CASE_DOCUMENTS_COLLECTION = "case_documents"
    SEPARATED_SEARCH_K = 5
    
    # 文档类型定义
    DOC_TYPE_LAW = "law"
    DOC_TYPE_PRIVATE_CASE = "private_case"
    DOC_TYPE_PUBLIC_CASE = "public_case"
    
    # 系统用户ID
    SYSTEM_OWNER_ID = "system"

    WEB_VS_COLLECTION_NAME = "web"
    WEB_VS_SEARCH_K = 2

    WEB_HOST = "0.0.0.0"
    WEB_PORT = 7860
    WEB_USERNAME = "username"
    WEB_PASSWORD = "password"
    MAX_HISTORY_LENGTH = 5

    
    ABSOLUTE_PATH = Path(r"xxx/models")  # 使用 Path 替换自己的目录
    EMBEDDING_PATH = ABSOLUTE_PATH / "bge-large-zh-v1.5"  # 使用 / 拼接路径
    RERANKER_PATH = ABSOLUTE_PATH / "bge-reranker-v2-m3"

    

config = Config()
