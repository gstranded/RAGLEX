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


def build_knowledge_messages(question, recent_messages, mode, knowledge_results):
    """构造带知识库上下文的模型消息。"""
    mode_descriptions = {
        'shared_knowledge': '公有知识库',
        'private_knowledge': '私有知识库',
        'entire_knowledge': '完整知识库',
        'knowledgeQA': '知识库'
    }
    mode_label = mode_descriptions.get(mode, '知识库')
    knowledge_context = format_knowledge_context(knowledge_results)

    system_prompt = (
        "你是 RAGLEX 法律问答助手。\n"
        f"当前请优先参考提供的{mode_label}检索片段回答问题。\n"
        "请遵守以下要求：\n"
        "1. 先基于检索片段作答，不要编造未提供的案件事实或法条内容。\n"
        "2. 如果检索片段不足以支撑确定结论，要明确说明资料不足，再给出一般性分析。\n"
        "3. 使用中文，结论清晰，法律建议保持审慎，并说明不构成正式法律意见。\n"
        "4. 若引用了检索片段，请在句末用“来源：[资料编号] 文件名”简要标注。\n"
        "5. 不要提到内部接口、网络错误或系统实现细节。"
    )

    user_prompt = (
        "以下是知识库检索结果：\n"
        f"{knowledge_context}\n\n"
        "请结合以上资料回答用户问题。\n"
        f"用户问题：{question}"
    )

    messages = [{'role': 'system', 'content': system_prompt}]
    messages.extend(recent_messages)
    messages.append({'role': 'user', 'content': user_prompt})
    return messages


def call_llm_with_knowledge(question, recent_messages, mode, knowledge_results, requested_model=None):
    return call_llm(
        build_knowledge_messages(question, recent_messages, mode, knowledge_results),
        temperature=0.15,
        max_tokens=1000,
        requested_model=requested_model
    )


def build_retrieval_only_answer(question, knowledge_results, max_excerpt_length=220):
    """当模型不可用时，直接返回检索到的关键资料片段。"""
    if not knowledge_results:
        return ""

    snippets = []
    for index, item in enumerate(knowledge_results[:3], start=1):
        content = str(item.get('content') or '').strip()
        if not content:
            continue
        if len(content) > max_excerpt_length:
            content = content[:max_excerpt_length].rstrip() + "..."
        snippets.append(
            f"[资料{index}] {item.get('filename')}\n{content}"
        )

    if not snippets:
        return ""

    return (
        "当前先根据已检索到的资料返回相关内容：\n\n"
        + "\n\n".join(snippets)
        + "\n\n以上内容基于知识库检索结果整理，不构成正式法律意见。"
    )



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
        knowledge_results = []
        remote_error_message = ""
        chat_service_url = get_chat_service_url()

        if mode in ('shared_knowledge', 'private_knowledge', 'entire_knowledge', 'knowledgeQA'):
            try:
                knowledge_results = search_knowledge_chunks(
                    current_user.id,
                    question,
                    mode,
                    int(top_k) if top_k is not None else 3
                )
                if knowledge_results:
                    current_app.logger.info(
                        "本地知识库检索命中: user_id=%s conversation_id=%s hits=%s",
                        current_user.id,
                        conversation_id,
                        len(knowledge_results)
                    )
                    try:
                        answer = call_llm_with_knowledge(
                            question,
                            recent_messages,
                            mode,
                            knowledge_results,
                            requested_model=large_language_model
                        )
                    except Exception as e:
                        current_app.logger.warning(
                            "知识库命中但模型生成失败，回退到检索片段直出: user_id=%s conversation_id=%s error=%s",
                            current_user.id,
                            conversation_id,
                            str(e)
                        )
                        answer = build_retrieval_only_answer(question, knowledge_results)
                else:
                    current_app.logger.info(
                        "本地知识库未命中: user_id=%s conversation_id=%s mode=%s",
                        current_user.id,
                        conversation_id,
                        mode
                    )
            except Exception as e:
                current_app.logger.error(f"本地知识库检索失败: {str(e)}")

        if not answer and chat_service_url:
            try:
                payload = {
                    'user_id': int(current_user.id),
                    'username': str(current_user.username),
                    'embedding_model': str(embedding_model),
                    'large_language_model': str(large_language_model),
                    'top_k': int(top_k) if top_k is not None else 3,
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
                answer = build_retrieval_only_answer(question, knowledge_results)
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
                'sources': [
                    {
                        'filename': item.get('filename'),
                        'knowledge_type': item.get('knowledge_type'),
                        'chunk_index': item.get('chunk_index'),
                        'score': item.get('score')
                    }
                    for item in knowledge_results
                ]
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"知识库查询错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '查询失败，请稍后重试'
        }), 500
    
