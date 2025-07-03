# coding: utf-8
from typing import List
from collections import defaultdict

from langchain.docstore.document import Document

# 将文档合并为上下文
def combine_law_docs(docs: List[Document]) -> str:
    law_books = defaultdict(list)
    for doc in docs:
        metadata = doc.metadata
        if 'book' in metadata:
            law_books[metadata["book"]].append(doc)

    law_str = ""
    for book, docs in law_books.items():
        #############下面是新添加的###############
        # 去重：使用集合存储唯一内容
        unique_contents = set()
        for doc in docs:
            content = doc.page_content.strip("\n")
            if content:  # 忽略空内容
                unique_contents.add(content)
        
        # 拼接去重后的内容
        ##############上面是新添加的#############
        law_str += f"相关法律：《{book}》\n"
        law_str += "\n".join([doc.page_content.strip("\n") for doc in docs])
        law_str += "\n"

    return law_str


def combine_web_docs(docs: List[Document]) -> str:
    web_str = ""
    for doc in docs:
        web_str += f"相关网页：{doc.metadata['title']}\n"
        web_str += f"网页地址：{doc.metadata['link']}\n"
        web_str += doc.page_content.strip("\n") + "\n"
        web_str += "\n"

    return web_str
