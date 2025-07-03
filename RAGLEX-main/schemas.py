from pydantic import BaseModel, Field
from typing import Optional, List

class KnowledgeUploadData(BaseModel):
    user_id: int
    username: str
    file_path: str
    filename: str
    file_category: str
    knowledge_types: list
    file_id: int
    action: str

class CaseStructure(BaseModel):
    """案例结构化数据模型"""
    标题: str
    关键词: List[str]
    案例类型: str
    当事人: List[str]
    争议焦点: str
    法律条文: List[str]
    判决结果: str
    案例要点: str
    适用法条: List[str]
    案例意义: str

class IdealCaseStructure(BaseModel):
    """
    符合理想格式的、更详细的案例结构化数据模型。
    """
    标题: str = Field(..., description="案件的核心、概括性标题")
    关键词: List[str] = Field(..., description="概括案件核心特征的关键词列表，例如：['执行', '企业重整']")
    案例类型: str = Field(..., description="案件的分类，例如：'执行/破产' 或 '刑事案件'")
    案例编号: Optional[str] = Field(None, description="案件的官方编号，例如：'（2019）苏0583破2号'。如果原文没有，则为null")
    基本案情: str = Field(..., description="对案件背景、起因、经过和各方诉求的详细、客观、完整的叙述段落。")
    裁判理由: str = Field(..., description="对法院为何如此判决的核心逻辑、原因和考量的详细说明段落。")
    裁判要旨: str = Field(..., description="从案件中提炼出的、具有指导意义的核心观点或原则的总结段落。")
    法律条文: List[str] = Field(..., description="案件中明确引用或适用的法律条文列表，格式为 '《法律名称》第XX条'")
    法院: Optional[str] = Field(None, description="审理该案件的法院名称，例如：'江苏省昆山市人民法院'。如果原文没有，则为null")
    判决日期: Optional[str] = Field(None, description="法院做出判决或裁定的日期，例如：'2022年2月23日'。如果原文没有，则为null")