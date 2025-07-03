from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import re
from pathlib import Path

from config import config
from utils import get_vectorstore
from retriever import get_multi_query_law_retiever
from utils import get_model_openai

# 创建路由
router = APIRouter(prefix="/laws", tags=["法规查询"])

# 模型定义
class LawArticle(BaseModel):
    """法律条文模型"""
    id: str
    title: str
    content: str
    law_name: str
    chapter: Optional[str] = None
    section: Optional[str] = None
    article_number: Optional[str] = None
    effective_date: Optional[str] = None
    source: str = "中华人民共和国法律库"

class LawSearchResult(BaseModel):
    """法律搜索结果模型"""
    total: int
    results: List[LawArticle]
    query: str

class LawCategory(BaseModel):
    """法律分类模型"""
    id: str
    name: str
    description: str
    count: int

# 辅助函数
def load_law_categories() -> List[Dict[str, Any]]:
    """加载法律分类信息"""
    # 这里可以从数据库或文件中加载实际的分类信息
    # 示例数据
    return [
        {"id": "constitution", "name": "宪法", "description": "国家根本大法", "count": 5},
        {"id": "civil_code", "name": "民法典", "description": "民事基本法律", "count": 1260},
        {"id": "criminal_law", "name": "刑法", "description": "刑事基本法律", "count": 452},
        {"id": "administrative_law", "name": "行政法", "description": "行政管理法律", "count": 328},
        {"id": "procedural_law", "name": "诉讼法", "description": "诉讼程序法律", "count": 215},
        {"id": "commercial_law", "name": "商法", "description": "商事法律", "count": 187},
        {"id": "economic_law", "name": "经济法", "description": "经济管理法律", "count": 203},
        {"id": "social_law", "name": "社会法", "description": "社会保障法律", "count": 156},
    ]

def extract_law_info(doc) -> LawArticle:
    """从文档中提取法律信息"""
    # 这里需要根据实际的文档结构进行解析
    # 示例实现
    content = doc.page_content
    metadata = doc.metadata
    
    # 尝试从内容中提取法律名称和条文号
    law_name_match = re.search(r'《(.+?)》', content)
    law_name = law_name_match.group(1) if law_name_match else metadata.get("source", "未知法律")
    
    article_match = re.search(r'第([\d一二三四五六七八九十百千]+)条', content)
    article_number = article_match.group(1) if article_match else None
    
    return LawArticle(
        id=metadata.get("id", f"law-{hash(content) % 10000}"),
        title=metadata.get("title", f"{law_name}第{article_number}条" if article_number else law_name),
        content=content,
        law_name=law_name,
        chapter=metadata.get("chapter"),
        section=metadata.get("section"),
        article_number=article_number,
        effective_date=metadata.get("effective_date"),
        source=metadata.get("source", "中华人民共和国法律库")
    )

# 路由定义
@router.get("/categories", response_model=List[LawCategory])
async def get_law_categories():
    """获取所有法律分类"""
    categories = load_law_categories()
    return [LawCategory(**category) for category in categories]

@router.get("/search", response_model=LawSearchResult)
async def search_laws(
    query: str = Query(..., description="搜索关键词"),
    category: Optional[str] = Query(None, description="法律分类ID"),
    limit: int = Query(10, description="返回结果数量", ge=1, le=50)
):
    """搜索法律条文"""
    try:
        # 获取向量存储和检索器
        law_vs = get_vectorstore(config.LAW_VS_COLLECTION_NAME)
        vs_retriever = law_vs.as_retriever(search_kwargs={"k": limit})
        
        # 使用多查询检索器增强搜索效果
        multi_query_retriever = get_multi_query_law_retiever(vs_retriever, get_model_openai())
        
        # 执行检索
        docs = multi_query_retriever.get_relevant_documents(query)
        
        # 如果指定了分类，进行过滤
        if category:
            # 这里需要根据实际的元数据结构进行过滤
            docs = [doc for doc in docs if doc.metadata.get("category_id") == category]
        
        # 转换为API响应格式
        results = [extract_law_info(doc) for doc in docs]
        
        return LawSearchResult(
            total=len(results),
            results=results,
            query=query
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索法律条文时发生错误: {str(e)}")

@router.get("/{law_id}", response_model=LawArticle)
async def get_law_by_id(law_id: str):
    """根据ID获取特定法律条文"""
    try:
        # 这里应该从数据库或向量存储中获取特定ID的法律条文
        # 示例实现 - 实际应用中需要替换为真实的数据获取逻辑
        law_vs = get_vectorstore(config.LAW_VS_COLLECTION_NAME)
        
        # 这里假设我们可以通过元数据过滤来获取特定ID的文档
        # 实际实现可能需要根据向量存储的API进行调整
        filter_dict = {"id": law_id}
        docs = law_vs.similarity_search("", k=1, filter=filter_dict)
        
        if not docs:
            raise HTTPException(status_code=404, detail=f"未找到ID为{law_id}的法律条文")
        
        return extract_law_info(docs[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取法律条文时发生错误: {str(e)}")

@router.get("/by-name/{law_name}")
async def get_laws_by_name(
    law_name: str,
    limit: int = Query(20, description="返回结果数量", ge=1, le=100)
):
    """根据法律名称获取所有相关条文"""
    try:
        # 获取向量存储
        law_vs = get_vectorstore(config.LAW_VS_COLLECTION_NAME)
        
        # 这里假设我们可以通过元数据过滤来获取特定法律名称的文档
        # 实际实现可能需要根据向量存储的API进行调整
        filter_dict = {"source": {"$eq": law_name}}
        docs = law_vs.similarity_search("", k=limit, filter=filter_dict)
        
        results = [extract_law_info(doc) for doc in docs]
        
        return LawSearchResult(
            total=len(results),
            results=results,
            query=f"法律名称:{law_name}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取法律条文时发生错误: {str(e)}")

@router.get("/article/{law_name}/{article_number}")
async def get_specific_article(
    law_name: str,
    article_number: str
):
    """获取特定法律的特定条文"""
    try:
        # 获取向量存储
        law_vs = get_vectorstore(config.LAW_VS_COLLECTION_NAME)
        
        # 构建查询
        query = f"{law_name}第{article_number}条"
        
        # 执行检索
        docs = law_vs.similarity_search(query, k=5)
        
        # 过滤结果，找到最匹配的条文
        for doc in docs:
            content = doc.page_content
            if law_name in content and f"第{article_number}条" in content:
                return extract_law_info(doc)
        
        raise HTTPException(status_code=404, detail=f"未找到{law_name}第{article_number}条")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取法律条文时发生错误: {str(e)}")