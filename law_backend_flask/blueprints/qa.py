# -*- coding: utf-8 -*-
"""
问答系统模块
包含知识库问答功能
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from models import db
from utils.auth import login_required, sanitize_input
from utils.knowledge_base import search_knowledge_chunks, format_knowledge_context
from utils.web_search import (
    format_web_search_context,
    is_web_search_requested,
    search_web
)
import requests
import os

qa_bp = Blueprint('qa', __name__)

DEFAULT_LLM_BASE_URL = "http://127.0.0.1:11434/v1"
DEFAULT_LLM_MODEL = "qwen2.5:7b"
DEFAULT_LLM_API_KEY = "ollama"
DEFAULT_CONTEXT_MESSAGE_COUNT = 6
LEGACY_UI_MODELS = {"ChatGLM-6B", "Qwen-7B"}


def get_chat_service_url():
    """可选外部 RAG 服务；未配置时返回空字符串，走本地 LLM 回退。"""
    return (os.environ.get('CHAT_SERVICE_URL') or '').strip()


def get_llm_base_url():
    base_url = (
        os.environ.get('OPENAI_COMPAT_BASE_URL')
        or os.environ.get('OPENAI_API_BASE')
        or DEFAULT_LLM_BASE_URL
    )
    return base_url.rstrip('/')


def get_llm_api_key():
    return (
        os.environ.get('OPENAI_COMPAT_API_KEY')
        or os.environ.get('OPENAI_API_KEY')
        or DEFAULT_LLM_API_KEY
    )


def get_llm_model(requested_model=None):
    requested_model = (requested_model or '').strip()
    if requested_model and requested_model not in LEGACY_UI_MODELS:
        return requested_model
    return os.environ.get('OPENAI_CHAT_MODEL') or DEFAULT_LLM_MODEL


def get_llm_timeout():
    try:
        return int(os.environ.get('OPENAI_CHAT_TIMEOUT_SECONDS', '60'))
    except ValueError:
        return 60


def get_context_message_count():
    try:
        return int(os.environ.get('QA_CONTEXT_MESSAGES', str(DEFAULT_CONTEXT_MESSAGE_COUNT)))
    except ValueError:
        return DEFAULT_CONTEXT_MESSAGE_COUNT


def load_conversation_context(current_user, conversation_id):
    """从本地数据库提取最近几条对话上下文。"""
    if not conversation_id:
        return None, []

    from models import Conversation, Message

    conversation = Conversation.query.filter_by(
        id=conversation_id,
        user_id=current_user.id
    ).first()

    if not conversation:
        return None, []

    messages = (
        Message.query.filter_by(conversation_id=conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )
    recent_messages = [
        {'role': message.role, 'content': message.content}
        for message in messages[-get_context_message_count():]
        if message.content
    ]
    return conversation, recent_messages


def build_fallback_messages(question, recent_messages, mode):
    """构造回退到通用模型时的消息列表。"""
    mode_descriptions = {
        'shared_knowledge': '用户希望参考共享知识库；如果当前没有检索到相关资料，请先明确说明。',
        'private_knowledge': '用户希望参考私有知识库；如果当前没有检索到相关资料，请先明确说明。',
        'entire_knowledge': '用户希望参考完整知识库；如果当前没有检索到相关资料，请先明确说明。',
        'none_knowledge': '当前问题不要求使用知识库，直接进行模型回答。',
        'knowledgeQA': '用户希望进行知识库问答；如果当前没有检索到相关资料，请先明确说明。'
    }
    mode_hint = mode_descriptions.get(mode, '当前外部知识库服务不可用。')
    system_prompt = (
        "你是 RAGLEX 法律问答助手。\n"
        f"{mode_hint}\n"
        "请直接基于你的通用知识先回答，并遵守以下要求：\n"
        "1. 使用中文，结论清晰。\n"
        "2. 对法律问题给出审慎说明，明确这只是一般性信息，不构成正式法律意见。\n"
        "3. 如果信息不足，先指出还需要哪些关键事实。\n"
        "4. 不要提到内部接口、网络错误或系统实现细节。"
    )

    messages = [{'role': 'system', 'content': system_prompt}]
    messages.extend(recent_messages)
    messages.append({'role': 'user', 'content': question})
    return messages


def call_llm(messages, temperature=0.2, max_tokens=800, requested_model=None):
    """调用本机可用的 OpenAI 兼容模型接口。"""
    response = requests.post(
        f"{get_llm_base_url()}/chat/completions",
        headers={
            'Authorization': f"Bearer {get_llm_api_key()}",
            'Content-Type': 'application/json'
        },
        json={
            'model': get_llm_model(requested_model),
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens
        },
        timeout=get_llm_timeout()
    )
    response.raise_for_status()
    data = response.json()
    answer = (
        data.get('choices', [{}])[0]
        .get('message', {})
        .get('content', '')
    )
    if not answer:
        raise ValueError('LLM 接口未返回有效内容')
    return answer.strip()


def call_llm_fallback(question, recent_messages, mode, requested_model=None):
    return call_llm(
        build_fallback_messages(question, recent_messages, mode),
        temperature=0.2,
        max_tokens=800,
        requested_model=requested_model
    )


def build_knowledge_messages(question, recent_messages, mode, knowledge_results, web_results=None):
    """构造带知识库和联网搜索上下文的模型消息。"""
    mode_descriptions = {
        'shared_knowledge': '公有知识库',
        'private_knowledge': '私有知识库',
        'entire_knowledge': '完整知识库',
        'knowledgeQA': '知识库'
    }
    mode_label = mode_descriptions.get(mode, '知识库')
    knowledge_context = format_knowledge_context(knowledge_results)
    web_context = format_web_search_context(web_results or [])

    system_prompt = (
        "你是 RAGLEX 法律问答助手。\n"
        f"当前请优先参考提供的{mode_label}检索片段回答问题。\n"
        "请遵守以下要求：\n"
        "1. 先基于检索片段作答，不要编造未提供的案件事实或法条内容。\n"
        "2. 如果同时提供了联网搜索结果，可将其作为补充参考，但不能覆盖已检索到的知识库事实。\n"
        "3. 如果检索片段不足以支撑确定结论，要明确说明资料不足，再给出一般性分析。\n"
        "4. 使用中文，结论清晰，法律建议保持审慎，并说明不构成正式法律意见。\n"
        "5. 若引用了检索片段，请在句末用“来源：[资料编号] 文件名”简要标注。\n"
        "6. 若引用了联网搜索结果，请在句末用“来源：[网页编号] 标题”简要标注。\n"
        "7. 不要提到内部接口、网络错误或系统实现细节。"
    )

    context_parts = []
    if knowledge_context:
        context_parts.append(f"以下是知识库检索结果：\n{knowledge_context}")
    if web_context:
        context_parts.append(f"以下是联网搜索结果：\n{web_context}")

    user_prompt = (
        "\n\n".join(context_parts)
        + "\n\n请结合以上资料回答用户问题。\n"
        f"用户问题：{question}"
    )

    messages = [{'role': 'system', 'content': system_prompt}]
    messages.extend(recent_messages)
    messages.append({'role': 'user', 'content': user_prompt})
    return messages


def build_web_messages(question, recent_messages, web_results):
    """构造仅基于联网搜索结果的模型消息。"""
    web_context = format_web_search_context(web_results)

    system_prompt = (
        "你是 RAGLEX 法律问答助手。\n"
        "当前没有直接提供知识库命中内容，请优先参考联网搜索结果回答。\n"
        "请遵守以下要求：\n"
        "1. 先基于提供的网页标题、摘要和链接作答，不要把搜索摘要当成已核实全文。\n"
        "2. 如果搜索结果不足以支持确定结论，要明确说明信息不足。\n"
        "3. 使用中文，结论清晰，法律问题要保持审慎，并说明不构成正式法律意见。\n"
        "4. 若引用了搜索结果，请在句末用“来源：[网页编号] 标题”简要标注。\n"
        "5. 不要提到内部接口、网络错误或系统实现细节。"
    )

    user_prompt = (
        "以下是联网搜索结果：\n"
        f"{web_context}\n\n"
        "请结合以上结果回答用户问题。\n"
        f"用户问题：{question}"
    )

    messages = [{'role': 'system', 'content': system_prompt}]
    messages.extend(recent_messages)
    messages.append({'role': 'user', 'content': user_prompt})
    return messages


def call_llm_with_knowledge(question, recent_messages, mode, knowledge_results, web_results=None, requested_model=None):
    return call_llm(
        build_knowledge_messages(
            question,
            recent_messages,
            mode,
            knowledge_results,
            web_results=web_results
        ),
        temperature=0.15,
        max_tokens=1000,
        requested_model=requested_model
    )


def call_llm_with_web(question, recent_messages, web_results, requested_model=None):
    return call_llm(
        build_web_messages(question, recent_messages, web_results),
        temperature=0.15,
        max_tokens=900,
        requested_model=requested_model
    )


def _build_knowledge_snippets(knowledge_results, max_excerpt_length=220):
    snippets = []
    for index, item in enumerate(knowledge_results[:3], start=1):
        content = str(item.get('content') or '').strip()
        if not content:
            continue
        if len(content) > max_excerpt_length:
            content = content[:max_excerpt_length].rstrip() + "..."
        snippets.append(f"[资料{index}] {item.get('filename')}\n{content}")
    return snippets


def _build_web_snippets(web_results, max_excerpt_length=220):
    snippets = []
    for index, item in enumerate(web_results[:3], start=1):
        snippet = str(item.get('snippet') or '').strip() or '搜索结果未提供摘要'
        if len(snippet) > max_excerpt_length:
            snippet = snippet[:max_excerpt_length].rstrip() + "..."
        snippets.append(
            f"[网页{index}] {item.get('title')}\n"
            f"来源: {item.get('source')}\n"
            f"链接: {item.get('link')}\n"
            f"摘要: {snippet}"
        )
    return snippets


def build_source_only_answer(knowledge_results=None, web_results=None):
    """当模型不可用时，直接返回已获取到的知识与搜索片段。"""
    sections = []

    knowledge_snippets = _build_knowledge_snippets(knowledge_results or [])
    if knowledge_snippets:
        sections.append("知识库检索片段：\n" + "\n\n".join(knowledge_snippets))

    web_snippets = _build_web_snippets(web_results or [])
    if web_snippets:
        sections.append("联网搜索结果：\n" + "\n\n".join(web_snippets))

    if not sections:
        return ""

    return (
        "当前先根据已获取到的资料返回相关内容：\n\n"
        + "\n\n".join(sections)
        + "\n\n以上内容基于知识库检索或联网搜索结果整理，不构成正式法律意见。"
    )


def build_retrieval_only_answer(question, knowledge_results, max_excerpt_length=220):
    """当模型不可用时，直接返回检索到的关键资料片段。"""
    snippets = _build_knowledge_snippets(knowledge_results, max_excerpt_length=max_excerpt_length)
    if not snippets:
        return ""

    return (
        "当前先根据已检索到的资料返回相关内容：\n\n"
        + "\n\n".join(snippets)
        + "\n\n以上内容基于知识库检索结果整理，不构成正式法律意见。"
    )


def build_web_only_answer(web_results, max_excerpt_length=220):
    snippets = _build_web_snippets(web_results, max_excerpt_length=max_excerpt_length)
    if not snippets:
        return ""

    return (
        "当前先根据已获取到的联网搜索结果返回相关内容：\n\n"
        + "\n\n".join(snippets)
        + "\n\n以上内容基于联网搜索结果整理，不构成正式法律意见。"
    )


def build_response_sources(knowledge_results, web_results):
    sources = [
        {
            'source_type': 'knowledge',
            'filename': item.get('filename'),
            'knowledge_type': item.get('knowledge_type'),
            'chunk_index': item.get('chunk_index'),
            'score': item.get('score')
        }
        for item in knowledge_results
    ]
    sources.extend([
        {
            'source_type': 'web',
            'title': item.get('title'),
            'link': item.get('link'),
            'snippet': item.get('snippet'),
            'provider': item.get('provider'),
            'source': item.get('source')
        }
        for item in web_results
    ])
    return sources



@qa_bp.route('/query', methods=['POST'])
@login_required
def knowledge_query(current_user):
    """知识库问答接口"""
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({
                'success': False,
                'message': '请提供问题内容'
            }), 400
        
        question = sanitize_input(data['question'])
        conversation_id = data.get('conversation_id')  # 可选的对话ID
        if conversation_id is not None:
            conversation_id = int(conversation_id)
        
        # 获取配置参数
        embedding_model = data.get('embedding_model')
        large_language_model = data.get('large_language_model')
        top_k = data.get('top_k')
        web_search = data.get('web_search')
        mode = data.get('mode')
        
        effective_model = get_llm_model(large_language_model)

        # 打印接收到的配置参数
        print(f"用户ID: {current_user.id}")
        print(f"用户名: {current_user.username}")
        print(f"嵌入模型: {embedding_model}")
        print(f"大语言模型: {large_language_model}")
        print(f"实际使用模型: {effective_model}")
        print(f"Top K: {top_k}")
        print(f"网络搜索: {web_search}")
        print(f"模式: {mode}")
        print(f"问题: {question}")
        print(f"对话ID: {conversation_id}")

        if not question.strip():
            return jsonify({
                'success': False,
                'message': '问题内容不能为空'
            }), 400

        from models import Message

        conversation, recent_messages = load_conversation_context(current_user, conversation_id)

        # 如果提供了conversation_id，先保存用户消息到本地对话中
        if conversation_id and conversation:
            user_message = Message(
                conversation_id=conversation_id,
                role='user',
                content=question
            )
            db.session.add(user_message)
            conversation.updated_at = datetime.utcnow()
            db.session.commit()
            current_app.logger.info(f"保存用户消息到对话 {conversation_id}: {question[:50]}")
        elif conversation_id:
            current_app.logger.warning(f"对话 {conversation_id} 不存在或不属于用户 {current_user.id}")

        answer = ""
        top_k_value = int(top_k) if top_k is not None else 3
        web_requested = is_web_search_requested(web_search)
        knowledge_results = []
        web_results = []
        remote_error_message = ""
        chat_service_url = get_chat_service_url()

        if web_requested:
            try:
                web_results = search_web(question, top_k_value)
                current_app.logger.info(
                    "联网搜索完成: user_id=%s conversation_id=%s requested=%s hits=%s",
                    current_user.id,
                    conversation_id,
                    web_search,
                    len(web_results)
                )
            except Exception as e:
                current_app.logger.warning(
                    "联网搜索失败: user_id=%s conversation_id=%s error=%s",
                    current_user.id,
                    conversation_id,
                    str(e)
                )

        if mode in ('shared_knowledge', 'private_knowledge', 'entire_knowledge', 'knowledgeQA'):
            try:
                knowledge_results = search_knowledge_chunks(
                    current_user.id,
                    question,
                    mode,
                    top_k_value
                )
                if knowledge_results or web_results:
                    current_app.logger.info(
                        "知识增强资料可用: user_id=%s conversation_id=%s knowledge_hits=%s web_hits=%s",
                        current_user.id,
                        conversation_id,
                        len(knowledge_results),
                        len(web_results)
                    )
                    try:
                        answer = call_llm_with_knowledge(
                            question,
                            recent_messages,
                            mode,
                            knowledge_results,
                            web_results=web_results,
                            requested_model=large_language_model
                        )
                    except Exception as e:
                        current_app.logger.warning(
                            "知识增强回答生成失败，回退到资料直出: user_id=%s conversation_id=%s error=%s",
                            current_user.id,
                            conversation_id,
                            str(e)
                        )
                        answer = build_source_only_answer(knowledge_results, web_results)
                else:
                    current_app.logger.info(
                        "本地知识库与联网搜索均未命中: user_id=%s conversation_id=%s mode=%s",
                        current_user.id,
                        conversation_id,
                        mode
                    )
            except Exception as e:
                current_app.logger.error(f"本地知识库检索失败: {str(e)}")

        if not answer and web_results:
            try:
                answer = call_llm_with_web(
                    question,
                    recent_messages,
                    web_results,
                    requested_model=large_language_model
                )
            except Exception as e:
                current_app.logger.warning(
                    "联网搜索命中但模型生成失败，回退到搜索片段直出: user_id=%s conversation_id=%s error=%s",
                    current_user.id,
                    conversation_id,
                    str(e)
                )
                answer = build_web_only_answer(web_results)

        if not answer and chat_service_url:
            try:
                payload = {
                    'user_id': int(current_user.id),
                    'username': str(current_user.username),
                    'embedding_model': str(embedding_model),
                    'large_language_model': str(large_language_model),
                    'top_k': top_k_value,
                    'web_search': str(web_search),
                    'mode': str(mode),
                    'question': str(question),
                    'conversation_id': conversation_id or 0,
                    'recent_messages_count': 3
                }
                response = requests.post(
                    f"{chat_service_url.rstrip('/')}/api/chat",
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                remote_response = response.json()
                current_app.logger.info(f"成功发送到外部问答服务: {chat_service_url}")

                if remote_response.get('status') == 'success' and remote_response.get('message'):
                    answer = remote_response['message']
                elif remote_response.get('answer'):
                    answer = remote_response['answer']
                elif remote_response.get('data', {}).get('answer'):
                    answer = remote_response['data']['answer']
                elif remote_response.get('response'):
                    answer = remote_response['response']
                else:
                    remote_error_message = '外部问答服务未返回有效答案'
            except Exception as e:
                remote_error_message = str(e)
                current_app.logger.warning(f"外部问答服务调用失败，准备回退到本地模型: {remote_error_message}")

        if not answer:
            try:
                answer = call_llm_fallback(
                    question,
                    recent_messages,
                    mode,
                    requested_model=large_language_model
                )
                if remote_error_message:
                    current_app.logger.info("已回退到本地 OpenAI 兼容模型接口")
            except Exception as e:
                current_app.logger.error(f"本地模型回退失败: {str(e)}")
                answer = build_source_only_answer(knowledge_results, web_results)
                if not answer:
                    answer = "抱歉，当前问答服务暂时不可用，请稍后重试。"

        # 如果有对话ID且对话存在，也保存AI回复
        if conversation_id and conversation:
            ai_message = Message(
                conversation_id=conversation_id,
                role='assistant',
                content=answer
            )
            db.session.add(ai_message)
            conversation.updated_at = datetime.utcnow()
            db.session.commit()
            current_app.logger.info(f"保存AI回复到对话 {conversation_id}: {answer[:50]}")
        
        current_app.logger.info(f"用户 {current_user.username} 进行知识库查询: {question[:50]}")
        
        return jsonify({
            'success': True,
            'data': {
                'question': question,
                'answer': answer,
                'conversation_id': conversation_id,
                'sources': build_response_sources(knowledge_results, web_results),
                'web_search_used': web_requested,
                'web_result_count': len(web_results)
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"知识库查询错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '查询失败，请稍后重试'
        }), 500
    
