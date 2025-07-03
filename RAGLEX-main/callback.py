# coding: utf-8
import asyncio
from typing import Any, Dict, List
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain_core.callbacks import BaseCallbackHandler

class OutCallbackHandler(AsyncIteratorCallbackHandler):
    """优化的输出回调处理器，提供更好的流式输出体验"""
    
    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[Dict[str, Any]]],
        **kwargs: Any,
    ) -> Any:
        """在聊天模型开始运行时执行。"""
        pass

class OutputLogger(BaseCallbackHandler):
    """输出日志记录器，用于记录模型生成结果"""
    def on_llm_end(self, response, **kwargs):
        # 移除调试输出，保持界面整洁
        pass

