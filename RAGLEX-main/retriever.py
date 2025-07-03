# coding: utf-8
from typing import List

from langchain.schema.vectorstore import VectorStore
from langchain.schema import BaseRetriever, Document
from langchain.callbacks.manager import CallbackManagerForRetrieverRun
from langchain.pydantic_v1 import Field
from pydantic import BaseModel
from langchain.output_parsers import PydanticOutputParser
from langchain.text_splitter import RecursiveCharacterTextSplitter, TextSplitter
from langchain.chains import LLMChain
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_core.output_parsers import BaseOutputParser

from prompt import MULTI_QUERY_PROMPT_TEMPLATE
from utils import get_memory



# Output parser will split the LLM result into a list of queries
class LineList(BaseModel):
    # "lines" is the key (attribute name) of the parsed output
    lines: List[str] = Field(description="Lines of text")



class LineListOutputParser(BaseOutputParser):
    """纯文本分行解析器"""
    
    def get_format_instructions(self) -> str:
        return "每行一个结果，不要使用任何格式或标号"
    
    def parse(self, text: str) -> List[str]:
        return [line for line in text.strip().split("\n") if line.strip()]






def get_multi_query_law_retiever(retriever: BaseRetriever, model: BaseModel) -> BaseRetriever:
    """
    多查询检索器
    """
    output_parser = LineListOutputParser() # 创建输出解析器

    llm_chain = LLMChain(llm=model, prompt=MULTI_QUERY_PROMPT_TEMPLATE, output_parser=output_parser)

    retriever = MultiQueryRetriever(
        retriever=retriever, llm_chain=llm_chain, parser_key="lines"
    )

    return retriever

# 记忆检索器
def get_memory_retiever(retriever: BaseRetriever, model: BaseModel) -> BaseRetriever:
    """
    记忆检索器
    """
    output_parser = LineListOutputParser() # 创建输出解析器
    memory = get_memory()

    llm_chain = LLMChain(llm=model, prompt=MULTI_QUERY_PROMPT_TEMPLATE,memory = memory)

    retriever = MultiQueryRetriever(
        retriever=retriever, llm_chain=llm_chain, parser_key="lines"
    )

    return retriever