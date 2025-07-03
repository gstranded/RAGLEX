
##下面这个可以
from pprint import pprint
from typing import Any, List, Dict
from collections import defaultdict
from functools import lru_cache

from langchain.docstore.document import Document
from langchain.storage import LocalFileStore
from langchain.embeddings import CacheBackedEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain.indexes import SQLRecordManager, index
from langchain_chroma import Chroma
from config import config
from langchain.indexes._api import _batch
from langchain_openai import ChatOpenAI
from langchain.callbacks.manager import Callbacks
from langchain_huggingface import HuggingFaceEmbeddings
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from langchain import HuggingFacePipeline
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from FlagEmbedding import FlagReranker
from langchain.memory import ConversationBufferMemory
from openai import OpenAI
import gc
import torch

import os
os.environ["OPENAI_API_BASE"]="https://api.gptsapi.net/v1"

os.environ["DEEPSEEK_API_BASE"] = "https://api.deepseek.com/v1"

# 导入权限管理器
import permission_manager
def get_model(callbacks: Callbacks = None):
    return get_model_openai(callbacks=callbacks)

def  get_embeder():
    return get_embedder_bge()

# def get_embedder() -> CacheBackedEmbeddings:
#     fs = LocalFileStore("./.cache/embeddings")
#     underlying_embeddings = OpenAIEmbeddings()
    
#     cached_embedder = CacheBackedEmbeddings.from_bytes_store(
#         underlying_embeddings, fs, namespace=underlying_embeddings.model
#     )
#     return cached_embedder

#这是通过缓存机制加速处理过程的embedder 最初是用在openai的模型上（上面那个），不知道能不能用在bge上 所以有点问题
def get_cached_embedder1() -> CacheBackedEmbeddings:
    fs = LocalFileStore("./.cache/embeddings")
    model_name = "/home/spuser/new_law/LawBrain/models/bge-large-zh-v1.5"
    
    model_kwargs = {"device": "cpu"}  # 使用CPU进行计算
    encode_kwargs = {"normalize_embeddings": True}  # 正则化嵌入

    # 使用 HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs,
    )

    # 使用 model_name 作为 namespace
    cached_embedder = CacheBackedEmbeddings.from_bytes_store(
        embeddings, fs, namespace=model_name
    )
    # print(cached_embedder)
    return cached_embedder


# 全局变量存储embedding模型实例
_global_embedder = None

def get_embedder_bge():
    global _global_embedder
    if _global_embedder is None:
        _global_embedder = HuggingFaceBgeEmbeddings(
            model_name= str(config.EMBEDDING_PATH),
            model_kwargs={"device": "cuda"},
            encode_kwargs={"normalize_embeddings": True},
        )
        print("BGE Embedding模型已加载到GPU")
    return _global_embedder

def clear_embedder():
    """清理embedding模型"""
    global _global_embedder
    if _global_embedder is not None:
        del _global_embedder
        _global_embedder = None
        clear_gpu_memory()
        print("BGE Embedding模型已从GPU清理")


def clear_gpu_memory():
    """清理GPU内存"""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        gc.collect()
        print(f"GPU内存已清理，当前使用: {torch.cuda.memory_allocated() / 1024**3:.2f}GB")

def get_gpu_memory_info():
    """获取GPU内存使用信息"""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024**3
        cached = torch.cuda.memory_reserved() / 1024**3
        total = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"GPU内存状态: 已分配={allocated:.2f}GB, 已缓存={cached:.2f}GB, 总计={total:.2f}GB")
        return {"allocated": allocated, "cached": cached, "total": total}
    else:
        print("CUDA不可用")
        return None

def force_clear_all_gpu_memory():
    """强制清理所有GPU内存，包括embedding模型"""
    print("开始强制清理所有GPU内存...")
    clear_embedder()
    clear_gpu_memory()
    print("所有GPU内存清理完成")
    get_gpu_memory_info()


# 创建并返回一个Chroma向量数据库
def get_vectorstore(collection_name: str = "law") -> Chroma:
    # 导入 chromadb 配置以禁用遥测
    import chromadb
    from chromadb.config import Settings
    
    # 创建客户端设置，禁用遥测功能
    client_settings = Settings(
        anonymized_telemetry=False  # 禁用遥测，避免连接 posthog.com
    )
    
    vectorstore = Chroma(
        persist_directory="./chroma_db",        # 持久化存储目录
        embedding_function=get_embeder(),      # 嵌入模型
        collection_name=collection_name,        # 集合名称 数据库的表
        client_settings=client_settings)        # 客户端设置

    return vectorstore

# 获取法律条文向量数据库
def get_law_vectorstore() -> Chroma:
    return get_vectorstore("law_documents")

# 获取案例向量数据库
def get_case_vectorstore() -> Chroma:
    return get_vectorstore("case_documents")

#创建一个 SQLRecordManager 实例，用于管理向量数据库中的记录
def get_record_manager(namespace: str = "law") -> SQLRecordManager:
    return SQLRecordManager(
        f"chroma/{namespace}", db_url="sqlite:///law_record_manager_cache.sql"
    )


# 清除向量数据库
def clear_vectorstore(collection_name: str = "law") -> None:
    record_manager = get_record_manager(collection_name)
    vectorstore = get_vectorstore(collection_name)

    index([], record_manager, vectorstore, cleanup="full", source_id_key="source")


# 将 法律相关文档 批量索引 到向量数据库 并进行 记录管理
def law_index(docs: List[Document], show_progress: bool = True) -> Dict:
    """原有的统一索引函数，保持向后兼容"""
    info = defaultdict(int)

    record_manager = get_record_manager("law")
    vectorstore = get_vectorstore("law")

    pbar = None
    if show_progress:
        from tqdm import tqdm
        pbar = tqdm(total=len(docs))

    for docs in _batch(100, docs):
        result = index(
            docs,
            record_manager,
            vectorstore,
            cleanup=None,
            # cleanup="full",
            source_id_key="source",
        )
        for k, v in result.items():
            info[k] += v

        if pbar:
            pbar.update(len(docs))

    if pbar:
        pbar.close()

    return dict(info)


# ==================== 分离的索引函数 ====================

def index_law_documents(docs: List[Document], show_progress: bool = True) -> Dict:
    """
    专门索引法律条文文档到law_documents集合
    
    Args:
        docs: 法律条文文档列表
        show_progress: 是否显示进度条
    
    Returns:
        索引结果统计
    """
    info = defaultdict(int)

    record_manager = get_record_manager("law_documents")
    vectorstore = get_law_vectorstore()

    pbar = None
    if show_progress:
        from tqdm import tqdm
        pbar = tqdm(total=len(docs), desc="索引法律条文")

    for docs_batch in _batch(100, docs):
        result = index(
            docs_batch,
            record_manager,
            vectorstore,
            cleanup=None,
            source_id_key="source",
        )
        for k, v in result.items():
            info[k] += v

        if pbar:
            pbar.update(len(docs_batch))

    if pbar:
        pbar.close()

    return dict(info)

def index_case_documents(docs: List[Document], show_progress: bool = True) -> Dict:
    """
    专门索引案例文档到case_documents集合
    
    Args:
        docs: 案例文档列表
        show_progress: 是否显示进度条
    
    Returns:
        索引结果统计
    """
    info = defaultdict(int)

    record_manager = get_record_manager("case_documents")
    vectorstore = get_case_vectorstore()

    pbar = None
    if show_progress:
        from tqdm import tqdm
        pbar = tqdm(total=len(docs), desc="索引案例文档")

    for docs_batch in _batch(100, docs):
        result = index(
            docs_batch,
            record_manager,
            vectorstore,
            cleanup=None,
            source_id_key="source",
        )
        for k, v in result.items():
            info[k] += v

        if pbar:
            pbar.update(len(docs_batch))

    if pbar:
        pbar.close()

    return dict(info)

def index_all_documents_separated(law_docs: List[Document], case_docs: List[Document], show_progress: bool = True) -> Dict[str, Dict]:
    """
    分别索引法律条文和案例文档
    
    Args:
        law_docs: 法律条文文档列表
        case_docs: 案例文档列表
        show_progress: 是否显示进度条
    
    Returns:
        包含两种文档索引结果的字典
    """
    results = {}
    
    print("开始索引法律条文文档...")
    results["law_documents"] = index_law_documents(law_docs, show_progress)
    
    print("开始索引案例文档...")
    results["case_documents"] = index_case_documents(case_docs, show_progress)
    
    return results

def clear_law_vectorstore() -> None:
    """清除法律条文向量数据库"""
    record_manager = get_record_manager("law_documents")
    vectorstore = get_law_vectorstore()
    index([], record_manager, vectorstore, cleanup="full", source_id_key="source")
    print("法律条文向量数据库已清除")

def clear_case_vectorstore() -> None:
    """清除案例向量数据库"""
    record_manager = get_record_manager("case_documents")
    vectorstore = get_case_vectorstore()
    index([], record_manager, vectorstore, cleanup="full", source_id_key="source")
    print("案例向量数据库已清除")

def clear_all_separated_vectorstores() -> None:
    """清除所有分离的向量数据库"""
    clear_law_vectorstore()
    clear_case_vectorstore()
    print("所有分离的向量数据库已清除")


def get_model_openai(
        model: str = "gpt-4o-mini",
        streaming: bool = True,
        callbacks: Callbacks = None) -> ChatOpenAI:
    model = ChatOpenAI(model=model, streaming=streaming, callbacks=callbacks,temperature=0.1)
    # temperature=0 禁止创造性回答
    return model


@lru_cache(maxsize=1)
def get_model_qwen():
    """
    加载基础的Qwen模型并返回一个HuggingFacePipeline实例。
    这个函数只会被执行一次，其结果会被缓存。
    注意：这里不传入任何与单次生成相关的参数，如 temperature, top_p 等。
    """
    print("--- 正在加载Qwen模型（此消息应只出现一次） ---")
    tokenizer = AutoTokenizer.from_pretrained(r'/home/spuser/new_law/LawBrain/models/Qwen2.5-3B-Instruct', trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(r'/home/spuser/new_law/LawBrain/models/Qwen2.5-3B-Instruct', device_map="cuda", trust_remote_code=True).eval()
    
    # 创建基础pipeline，不设置具体的生成参数
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer
    )
    
    # 基础模型不带callbacks，这些将在调用时通过.bind()或.with_config()传入
    llm = HuggingFacePipeline(pipeline=pipe)
    return llm


class TruncateOnNewlineLLM:
    """
    包装类，用于在检测到换行符时截断并删除输出中的换行符
    """
    def __init__(self, base_llm):
        self.base_llm = base_llm
    
    def bind(self, **kwargs):
        # 自动添加stop=["\n"]参数以在换行符处截断
        if 'stop' not in kwargs:
            kwargs['stop'] = ["\n"]
        elif isinstance(kwargs['stop'], list) and "\n" not in kwargs['stop']:
            kwargs['stop'].append("\n")
        
        return self.base_llm.bind(**kwargs)
    
    def with_config(self, config):
        return self.base_llm.with_config(config)
    
    def __getattr__(self, name):
        return getattr(self.base_llm, name)


def get_qwen_with_params(max_new_tokens=512, top_p=0.8, temperature=0.7, callbacks=None, truncate_on_newline=False):
    """
    获取配置好参数的Qwen模型。
    
    Args:
        max_new_tokens: 最大新生成token数
        top_p: nucleus sampling参数
        temperature: 温度参数
        callbacks: 回调函数
        truncate_on_newline: 是否在换行符处截断
    
    Returns:
        配置好的模型实例
    """
    # 获取缓存的基础模型
    base_model = get_model_qwen()
    
    # 如果需要在换行符处截断，使用包装类
    if truncate_on_newline:
        base_model = TruncateOnNewlineLLM(base_model)
    
    # 使用bind方法传递参数
    configured_model = base_model.bind(
        max_new_tokens=max_new_tokens,
        top_p=top_p,
        temperature=temperature
    )
    
    # 如果有callbacks，使用with_config传入
    if callbacks:
        configured_model = configured_model.with_config({"callbacks": callbacks})
    
    return configured_model

def get_model_dpsk(
        model: str = "deepseek-chat",
        streaming: bool = True,
        callbacks: Callbacks = None) -> ChatOpenAI:
    model = ChatOpenAI(model=model, streaming=streaming, callbacks=callbacks,temperature=0)
    # temperature=0 禁止创造性回答
    return model


# 创建ConversationBufferMemory
def get_memory() -> ConversationBufferMemory:
    return ConversationBufferMemory(
        memory_key="chat_history",
        input_key="question",  # 必须与输入字段名一致
        output_key="answer",    # 必须与输出字段名一致
        return_messages=True
    )


def delete_chroma(collection_name: str = "law",persist_directory: str = "./chroma_db"):
    # 导入 chromadb 配置以禁用遥测
    import chromadb
    from chromadb.config import Settings
    
    # 创建客户端设置，禁用遥测功能
    client_settings = Settings(
        anonymized_telemetry=False  # 禁用遥测，避免连接 posthog.com
    )
    
    vectorstore = Chroma(
        collection_name=collection_name, 
        persist_directory=persist_directory,
        client_settings=client_settings
    )
    
    # 删除集合
    vectorstore.delete_collection()
    print(f"Collection '{collection_name}' deleted successfully.")
    

    # 删除集合
    # 因为如果用bge会出现这个问题
    # chromadb.errors.InvalidDimensionException: Embedding dimension 1024 does not match collection dimensionality 1536
    # 维度不匹配，csdn解决方法就是要么删除原来的，要么重新开一个路径





def rerank_documents(question: str, initial_top_n: int = 15, top_n: int = 3) -> List[Dict[str, Any]]:
    # 先使用向量相似搜索找到一些可能相关的文档
    vectorstore = get_vectorstore()
    initial_docs = vectorstore.similarity_search(question, k=initial_top_n)
    # 将这些文档和查询语句组成一个列表，每个元素是一个包含查询和文档内容的列表
    sentence_pairs = [[question, passage.page_content] for passage in initial_docs]

    # 使用FlagReranker模型对这些文档进行重新排序;将use_fp16设置为True可以提高计算速度，但性能略有下降
    reranker = FlagReranker(str(config.RERANKER_PATH))
    try:
        # 计算每个文档的得分
        scores = reranker.compute_score(sentence_pairs)
        
        # 将得分和文档内容组成一个字典列表
        score_document = [{"score": score, "content": content} for score, content in zip(scores, initial_docs)]
        # 根据得分对文档进行排序，并返回前top_n个文档
        result = sorted(score_document, key=lambda x: x['score'], reverse=True)[:top_n]
        print(result)
        return result
    finally:
        # 清理reranker模型和GPU内存
        del reranker
        clear_gpu_memory()

def rerank_documents_doc(question: str, initial_top_n: int = 15, top_n: int = 3) -> List[Document]:
    vectorstore = get_vectorstore()
    initial_docs = vectorstore.similarity_search(question, k=initial_top_n)
    sentence_pairs = [[question, passage.page_content] for passage in initial_docs]
    # print("检索内容：")
    # print(sentence_pairs)
    reranker = FlagReranker(str(config.RERANKER_PATH))
    try:
        scores = reranker.compute_score(sentence_pairs)
        
        # 只返回文档，不返回分数
        sorted_docs = [doc for _, doc in sorted(zip(scores, initial_docs), key=lambda x: x[0], reverse=True)[:top_n]]
        # print("排序后：")
        # print(sorted_docs)
        return sorted_docs  # 确保返回的是 List[Document]
    finally:
        # 清理reranker模型和GPU内存
        del reranker
        clear_gpu_memory()

def rerank_existing_documents(question: str, docs: List[Document], top_k: int = 10) -> List[Document]:
    """对已有文档列表进行重排序"""
    if not docs:
        return []
    
    # 将查询和文档内容组成句子对
    sentence_pairs = [[question, doc.page_content] for doc in docs]
    
    # 使用FlagReranker进行重排序
    reranker = FlagReranker(str(config.RERANKER_PATH))
    try:
        scores = reranker.compute_score(sentence_pairs)
        
        # 根据分数排序并返回前top_k个文档
        sorted_docs = [doc for _, doc in sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)[:top_k]]
        return sorted_docs
    finally:
        # 清理reranker模型和GPU内存
        del reranker
        clear_gpu_memory()

# ==================== 分离的检索函数 ====================

def search_law_documents(question: str, k: int = 5, use_rerank: bool = True, rerank_top_k: int = 3) -> List[Document]:
    """
    专门检索法律条文文档
    
    Args:
        question: 查询问题
        k: 初始检索数量
        use_rerank: 是否使用重排序
        rerank_top_k: 重排序后返回的文档数量
    
    Returns:
        法律条文文档列表
    """
    vectorstore = get_law_vectorstore()
    
    if use_rerank:
        # 先检索更多文档，然后重排序
        initial_docs = vectorstore.similarity_search(question, k=k*3)
        if initial_docs:
            return rerank_existing_documents(question, initial_docs, rerank_top_k)
        return []
    else:
        return vectorstore.similarity_search(question, k=k)

def extract_case_key_sections(case_content: str) -> str:
    """
    从案例文档中提取四个关键部分：基本案情、裁判理由、裁判要旨、法律条文
    
    Args:
        case_content: 案例文档的完整内容
    
    Returns:
        提取的关键部分内容
    """
    import re
    
    sections = []
    
    # 提取基本案情
    basic_facts_match = re.search(r'## 基本案情\s*([\s\S]*?)(?=##|$)', case_content)
    if basic_facts_match:
        sections.append(f"## 基本案情\n{basic_facts_match.group(1).strip()}")
    
    # 提取裁判理由
    reasoning_match = re.search(r'## 裁判理由\s*([\s\S]*?)(?=##|$)', case_content)
    if reasoning_match:
        sections.append(f"## 裁判理由\n{reasoning_match.group(1).strip()}")
    
    # 提取裁判要旨
    key_points_match = re.search(r'## 裁判要旨\s*([\s\S]*?)(?=##|$)', case_content)
    if key_points_match:
        sections.append(f"## 裁判要旨\n{key_points_match.group(1).strip()}")
    
    # 提取法律条文
    legal_articles_match = re.search(r'## 法律条文\s*([\s\S]*?)(?=##|$)', case_content)
    if legal_articles_match:
        sections.append(f"## 法律条文\n{legal_articles_match.group(1).strip()}")
    
    return "\n\n".join(sections) if sections else case_content

def search_case_documents(question: str, k: int = 5, use_rerank: bool = True, rerank_top_k: int = 3) -> List[Document]:
    """
    专门检索案例文档，并提取关键部分
    
    Args:
        question: 查询问题
        k: 初始检索数量
        use_rerank: 是否使用重排序
        rerank_top_k: 重排序后返回的文档数量
    
    Returns:
        案例文档列表（内容已提取关键部分）
    """
    vectorstore = get_case_vectorstore()
    
    if use_rerank:
        # 先检索更多文档，然后重排序
        initial_docs = vectorstore.similarity_search(question, k=k*3)
        if initial_docs:
            ranked_docs = rerank_existing_documents(question, initial_docs, rerank_top_k)
        else:
            ranked_docs = []
    else:
        ranked_docs = vectorstore.similarity_search(question, k=k)
    
    # 对每个案例文档提取关键部分
    processed_docs = []
    for doc in ranked_docs:
        # 创建新的文档对象，内容为提取的关键部分
        from langchain.docstore.document import Document
        processed_doc = Document(
            page_content=extract_case_key_sections(doc.page_content),
            metadata=doc.metadata
        )
        processed_docs.append(processed_doc)
    
    return processed_docs

def search_law_by_keywords(keywords: List[str], k: int = 5) -> List[Document]:
    """
    根据关键词检索法律条文
    
    Args:
        keywords: 关键词列表
        k: 返回文档数量
    
    Returns:
        法律条文文档列表
    """
    vectorstore = get_law_vectorstore()
    query = " ".join(keywords)
    return vectorstore.similarity_search(query, k=k)

def search_cases_by_keywords(keywords: List[str], k: int = 5) -> List[Document]:
    """
    根据关键词检索案例文档
    
    Args:
        keywords: 关键词列表
        k: 返回文档数量
    
    Returns:
        案例文档列表
    """
    vectorstore = get_case_vectorstore()
    query = " ".join(keywords)
    return vectorstore.similarity_search(query, k=k)

def search_case_documents_with_user_filter(question: str, user_id: int, k: int = 10, use_rerank: bool = True, rerank_top_k: int = 5) -> List[Document]:
    """
    搜索案例文档，支持用户权限过滤（新权限管理方案）
    
    采用两步走的"授权+检索"流程：
    1. 先从SQLite查询用户有权访问的file_id列表
    2. 再在ChromaDB中只搜索这些file_id对应的文档
    
    Args:
        question: 查询问题
        user_id: 用户ID
        k: 初始检索数量
        use_rerank: 是否使用重排序
        rerank_top_k: 重排序后返回的文档数量
    
    Returns:
        List[Document]: 搜索结果文档列表
    """
    try:
        # 第一步：权限认证 - 从SQLite获取用户可访问的文件ID列表
        pm = permission_manager.get_permission_manager()
        accessible_file_ids = pm.get_user_accessible_file_ids(user_id)
        
        print(f"[DEBUG] 用户 {user_id} 可访问的文件ID数量: {len(accessible_file_ids)}")
        print(f"[DEBUG] 可访问的文件ID列表: {accessible_file_ids[:10]}...")  # 只显示前10个
        
        if not accessible_file_ids:
            print(f"[DEBUG] 用户 {user_id} 没有可访问的文件")
            return []
        
        # 第二步：带过滤的向量检索 - 只在允许的file_id范围内搜索
        vectorstore = get_case_vectorstore()
        
        # 构建过滤条件：只搜索用户有权访问的文件
        filter_condition = {
            "file_id": {"$in": accessible_file_ids}
        }
        
        print(f"[DEBUG] 向量搜索过滤条件: file_id in {len(accessible_file_ids)} files")
        
        # 执行搜索
        docs = vectorstore.similarity_search(
            question, 
            k=k, 
            filter=filter_condition
        )
        
        print(f"[DEBUG] 向量搜索结果数量: {len(docs)}")
        
        # 如果需要重排序且有结果
        if use_rerank and docs:
            print(f"[DEBUG] 开始案例文档重排序，目标数量: {rerank_top_k}")
            docs = rerank_existing_documents(question, docs, rerank_top_k)
            print(f"[DEBUG] 案例文档重排序完成，最终数量: {len(docs)}")
        
        return docs
        
    except Exception as e:
        print(f"[ERROR] 案例文档搜索失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def update_vector_metadata(file_id: int, new_metadata: dict):
    """
    更新向量数据库中指定文件的元数据（适配新的简化元数据结构）
    
    Args:
        file_id: 文件ID
        new_metadata: 新的元数据字典，应包含file_id, source, doc_type, title, chunk_seq_id
    """
    try:
        vectorstore = get_case_vectorstore()
        
        # 获取现有文档
        existing_docs = vectorstore.get(where={'file_id': file_id})
        
        if not existing_docs or not existing_docs.get('ids'):
            print(f"[DEBUG] 未找到文件ID {file_id} 的向量数据")
            return
        
        # 准备更新数据
        ids_to_update = existing_docs['ids']
        updated_metadatas = []
        
        # 为每个文档使用新的简化元数据结构
        for i, doc_id in enumerate(ids_to_update):
            current_metadata = existing_docs['metadatas'][i]
            
            # 构建新的简化元数据
            updated_metadata = {
                'file_id': file_id,
                'source': new_metadata.get('source', current_metadata.get('source', '')),
                'doc_type': new_metadata.get('doc_type', 'case'),
                'title': new_metadata.get('title', current_metadata.get('title', '未知标题')),
                'chunk_seq_id': current_metadata.get('chunk_seq_id', i)  # 保持原有的chunk序号
            }
            updated_metadatas.append(updated_metadata)
        
        # 使用正确的 Chroma API 更新元数据
        vectorstore._collection.update(
            ids=ids_to_update,
            metadatas=updated_metadatas
        )
        
        print(f"[DEBUG] 成功更新文件ID {file_id} 的向量元数据为新的简化结构")
        
    except Exception as e:
        print(f"[ERROR] 更新向量元数据失败: {str(e)}")
        raise e

def search_cases_by_court_name(court_name: str, k: int = 5) -> List[Document]:
    """
    根据法院名称检索案例
    
    Args:
        court_name: 法院名称
        k: 返回文档数量
    
    Returns:
        案例文档列表
    """
    vectorstore = get_case_vectorstore()
    # 使用元数据过滤
    docs = vectorstore.similarity_search(
        court_name, 
        k=k*2,  # 先获取更多文档
        filter={"case_details.court": court_name}
    )
    return docs[:k]

def search_cases_by_case_type(case_type: str, k: int = 5) -> List[Document]:
    """
    根据案例类型检索案例
    
    Args:
        case_type: 案例类型（如：刑事、民事、行政等）
        k: 返回文档数量
    
    Returns:
        案例文档列表
    """
    vectorstore = get_case_vectorstore()
    # 使用元数据过滤
    docs = vectorstore.similarity_search(
        case_type, 
        k=k*2,
        filter={"case_details.case_classification": case_type}
    )
    return docs[:k]

def get_law_document_count() -> int:
    """
    获取法律条文文档数量
    
    Returns:
        法律条文文档数量
    """
    vectorstore = get_law_vectorstore()
    return vectorstore._collection.count()

def get_case_document_count() -> int:
    """
    获取案例文档数量
    
    Returns:
        案例文档数量
    """
    vectorstore = get_case_vectorstore()
    return vectorstore._collection.count()

def get_document_statistics() -> Dict[str, int]:
    """
    获取文档统计信息
    
    Returns:
        包含各类文档数量的字典
    """
    return {
        "law_documents": get_law_document_count(),
        "case_documents": get_case_document_count(),
        "total_documents": get_law_document_count() + get_case_document_count()
    }

def add_single_file_to_vectorstore(file_path: str, metadata: dict, vectorstore_type: str = 'case'):
    """统一的向量存储写入守门员函数 - 确保所有写入都使用标准化的"黄金标准"元数据结构
    
    Args:
        file_path: 文件路径
        metadata: 原始元数据字典（可能包含很多字段）
        vectorstore_type: 向量存储类型 ('case' 或 'law')
    """
    try:
        # 加载文档
        from langchain.document_loaders import TextLoader
        from langchain.text_splitter import MarkdownTextSplitter
        import logging
        
        logger = logging.getLogger(__name__)
        
        loader = TextLoader(file_path, encoding='utf-8')
        documents = loader.load()
        
        if not documents:
            raise Exception("文档加载失败或为空")
        
        # 提取标题
        title = metadata.get('title') or extract_title_from_content(documents[0].page_content)
        
        # 【黄金标准】- 只保留这5个字段，过滤掉所有其他字段
        clean_metadata = {
            'file_id': metadata.get('file_id'),
            'source': file_path,  # 统一使用实际文件路径
            'doc_type': metadata.get('doc_type', 'case' if vectorstore_type == 'case' else 'law'),
            'title': title
            # chunk_seq_id 将在下面的循环中添加
        }
        
        # 验证必需字段
        if clean_metadata['file_id'] is None:
            raise Exception("file_id 是必需字段")
        
        print(f"[GATEKEEPER] 清理后的标准元数据: {clean_metadata}")
        print(f"[GATEKEEPER] 过滤掉的字段: {set(metadata.keys()) - set(clean_metadata.keys())}")
        
        # 分割文档
        text_splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(documents)
        
        # 为每个chunk添加标准化元数据和chunk_seq_id
        for chunk_seq_id, chunk in enumerate(chunks):
            chunk.metadata = clean_metadata.copy()
            chunk.metadata['chunk_seq_id'] = chunk_seq_id
        
        # 根据类型选择正确的向量存储
        if vectorstore_type == 'law':
            vectorstore = get_law_vectorstore()
        else:
            vectorstore = get_case_vectorstore()
        
        # 写入向量存储
        vectorstore.add_documents(chunks)
        
        logger.info(f"[GATEKEEPER] 成功写入文件到{vectorstore_type}向量存储: {file_path}, 共 {len(chunks)} 个块")
        print(f"[GATEKEEPER] 文件 {clean_metadata['file_id']} 写入完成，共 {len(chunks)} 个块")
        
        return len(chunks)  # 返回写入的块数
        
    except Exception as e:
        logger.error(f"[GATEKEEPER] 向量化入库失败: {str(e)}")
        raise

def extract_title_from_content(content: str) -> str:
    """从文档内容中提取标题"""
    if not content:
        return "未知标题"
    
    lines = content.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('# '):
            return line[2:].strip()
        elif line and not line.startswith('#'):
            return line[:50] + ('...' if len(line) > 50 else '')
    return "未知标题"

if __name__ == "__main__":
    print(rerank_documents(question = "法律"))