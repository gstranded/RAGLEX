# coding: utf-8
from typing import Any, List
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.docstore.document import Document
from config import config
import os

class LawLoader(DirectoryLoader):
    """Load law books."""
    def __init__(self, path: str, **kwargs: Any) -> None:
        loader_cls = TextLoader
        glob = "**/*.md"
        loader_kwargs = {"encoding": "utf-8"}
        super().__init__(path, loader_cls=loader_cls, glob=glob,loader_kwargs=loader_kwargs, **kwargs)

class SeparatedLawLoader(DirectoryLoader):
    """专门加载法律条文文档（排除案例目录）"""
    def __init__(self, path: str, **kwargs: Any) -> None:
        loader_cls = TextLoader
        glob = "**/*.md"
        loader_kwargs = {"encoding": "utf-8"}
        super().__init__(path, loader_cls=loader_cls, glob=glob, loader_kwargs=loader_kwargs, **kwargs)
    
    def load(self) -> List[Document]:
        """加载法律条文文档，排除案例目录"""
        docs = super().load()
        # 过滤掉案例目录中的文档
        filtered_docs = []
        file_id_counter = 1
        
        # 按source分组文档
        docs_by_source = {}
        for doc in docs:
            source = doc.metadata.get("source", "")
            if "案例" not in source:
                if source not in docs_by_source:
                    docs_by_source[source] = []
                docs_by_source[source].append(doc)
        
        # 为每个文件分配file_id和chunk_seq_id
        for source, source_docs in docs_by_source.items():
            # 提取标题
            title = self._extract_title_from_content(source_docs[0].page_content if source_docs else "")
            
            for chunk_seq_id, doc in enumerate(source_docs):
                # 使用新的简化元数据结构
                doc.metadata = {
                    "file_id": file_id_counter,
                    "source": source,
                    "doc_type": "law",
                    "title": title,
                    "chunk_seq_id": chunk_seq_id
                }
                filtered_docs.append(doc)
            
            file_id_counter += 1
        
        return filtered_docs
    
    def _extract_title_from_content(self, content: str) -> str:
        """从文档内容中提取标题"""
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
            elif line and not line.startswith('#'):
                return line[:50] + ('...' if len(line) > 50 else '')
        return "未知标题"

class CaseLoader(DirectoryLoader):
    """专门加载案例文档"""
    def __init__(self, path: str, **kwargs: Any) -> None:
        loader_cls = TextLoader
        glob = "**/*.md"
        loader_kwargs = {"encoding": "utf-8"}
        super().__init__(path, loader_cls=loader_cls, glob=glob, loader_kwargs=loader_kwargs, **kwargs)
    
    def load(self) -> List[Document]:
        """加载案例文档并添加元数据"""
        docs = super().load()
        file_id_counter = 1000  # 从1000开始，避免与法律文档ID冲突
        
        # 按source分组文档
        docs_by_source = {}
        for doc in docs:
            source = doc.metadata.get("source", "")
            if source not in docs_by_source:
                docs_by_source[source] = []
            docs_by_source[source].append(doc)
        
        # 为每个文件分配file_id和chunk_seq_id
        processed_docs = []
        for source, source_docs in docs_by_source.items():
            # 提取标题
            title = self._extract_title_from_content(source_docs[0].page_content if source_docs else "")
            
            for chunk_seq_id, doc in enumerate(source_docs):
                # 使用新的简化元数据结构
                doc.metadata = {
                    "file_id": file_id_counter,
                    "source": source,
                    "doc_type": "case",
                    "title": title,
                    "chunk_seq_id": chunk_seq_id
                }
                processed_docs.append(doc)
            
            file_id_counter += 1
        
        return processed_docs
    
    def _extract_title_from_content(self, content: str) -> str:
        """从文档内容中提取标题"""
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
            elif line and not line.startswith('#'):
                return line[:50] + ('...' if len(line) > 50 else '')
        return "未知标题"

def load_law_documents_only() -> List[Document]:
    """加载法律条文文档（不包括案例）"""
    loader = SeparatedLawLoader(config.LAW_BOOK_PATH)
    return loader.load()

def load_private_case_documents() -> List[Document]:
    """加载私有案例文档"""
    import os
    if os.path.exists(config.PRIVATE_CASE_DOCS_PATH):
        loader = CaseLoader(config.PRIVATE_CASE_DOCS_PATH)
        docs = loader.load()
        # 标记为私有案例
        for doc in docs:
            doc.metadata["doc_type"] = config.DOC_TYPE_PRIVATE_CASE
        return docs
    return []

def load_public_case_documents() -> List[Document]:
    """加载共有案例文档"""
    import os
    if os.path.exists(config.PUBLIC_CASE_DOCS_PATH):
        loader = CaseLoader(config.PUBLIC_CASE_DOCS_PATH)
        docs = loader.load()
        # 标记为共有案例
        for doc in docs:
            doc.metadata["doc_type"] = config.DOC_TYPE_PUBLIC_CASE
        return docs
    return []

def load_case_documents_only() -> List[Document]:
    """加载所有案例文档（私有案例 + 共有案例）"""
    all_case_docs = []
    
    # 加载私有案例
    private_docs = load_private_case_documents()
    all_case_docs.extend(private_docs)
    
    # 加载共有案例
    public_docs = load_public_case_documents()
    all_case_docs.extend(public_docs)
    
    # 如果新路径都不存在，尝试加载旧路径（向后兼容）
    if not all_case_docs:
        import os
        if os.path.exists(config.CASE_DOCS_PATH):
            loader = CaseLoader(config.CASE_DOCS_PATH)
            all_case_docs = loader.load()
    
    return all_case_docs

def load_all_documents_separated() -> tuple[List[Document], List[Document]]:
    """分别加载法律条文和案例文档
    
    Returns:
        tuple: (法律条文文档列表, 案例文档列表)
    """
    law_docs = load_law_documents_only()
    case_docs = load_case_documents_only()
    return law_docs, case_docs
