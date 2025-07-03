# -*- coding: utf-8 -*-
"""
问答系统模块
包含知识库问答功能
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from models import db
from utils.auth import login_required, sanitize_input
import requests

qa_bp = Blueprint('qa', __name__)



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
        
        # 获取配置参数
        embedding_model = data.get('embedding_model')
        large_language_model = data.get('large_language_model')
        top_k = data.get('top_k')
        web_search = data.get('web_search')
        mode = data.get('mode')
        
        # 打印接收到的配置参数
        print(f"用户ID: {current_user.id}")
        print(f"用户名: {current_user.username}")
        print(f"嵌入模型: {embedding_model}")
        print(f"大语言模型: {large_language_model}")
        print(f"Top K: {top_k}")
        print(f"网络搜索: {web_search}")
        print(f"模式: {mode}")
        print(f"问题: {question}")
        print(f"对话ID: {conversation_id}")

        # 初始化答案为"正在思考中..."
        answer = "正在思考中..."
        upload_success = False
        error_message = ""
        
        try:
            payload={
                    'user_id':int(current_user.id),
                    'username':str(current_user.username),
                    'embedding_model':str(embedding_model),
                    'large_language_model':str(large_language_model),
                    'top_k':int(top_k),
                    'web_search':str(web_search),
                    'mode':str(mode),
                    'question':str(question),
                    'conversation_id':int(conversation_id),
                    'recent_messages_count':3
            }
            response = requests.post(
                "http://192.168.240.3:10086/api/chat",
                json=payload,
                timeout=30  # 增加超时时间
            )
            if response.status_code == 200:
                remote_response = response.json()
                print(f"成功发送到远程服务器: {remote_response}")
                upload_success = True
                
                # 从远程服务器响应中提取答案
                if 'status' in remote_response and remote_response['status'] == 'success':
                    # 处理新的响应格式: {"status": "success", "message": "...", "user_id": 123, "conversation_id": 42}
                    if 'message' in remote_response:
                        answer = remote_response['message']
                    else:
                        answer = "远程服务器返回成功但未包含消息内容"
                elif 'answer' in remote_response:
                    # 兼容旧格式
                    answer = remote_response['answer']
                elif 'data' in remote_response and 'answer' in remote_response['data']:
                    # 兼容嵌套格式
                    answer = remote_response['data']['answer']
                elif 'response' in remote_response:
                    # 兼容其他格式
                    answer = remote_response['response']
                elif 'status' in remote_response and remote_response['status'] != 'success':
                    # 处理错误状态
                    error_msg = remote_response.get('message', '未知错误')
                    answer = f"远程服务器处理失败: {error_msg}"
                else:
                    answer = "远程服务器未返回有效答案"
            else:
                print(f"发送到远程服务器失败: {response.status_code}")
                if response.status_code == 422:
                    error_message = "数据格式错误，请检查远程服务器配置"
                    answer = "抱歉，数据格式错误，请稍后重试"
                else:
                    error_message = f"远程服务器返回错误: {response.status_code}"
                    answer = "抱歉，服务暂时不可用，请稍后重试"
                
        except requests.exceptions.RequestException as e:
            print(f"发送到远程服务器时出错: {str(e)}")
            error_message = f"网络连接错误: {str(e)}"
            answer = "抱歉，网络连接失败，请检查网络后重试"

        if not question.strip():
            return jsonify({
                'success': False,
                'message': '问题内容不能为空'
            }), 400
        
        # 如果提供了conversation_id，保存用户消息到对话中
        conversation = None
        if conversation_id:
            from models import Conversation, Message
            
            # 验证对话是否存在且属于当前用户
            conversation = Conversation.query.filter_by(
                id=conversation_id, 
                user_id=current_user.id
            ).first()
            
            if conversation:
                # 保存用户消息
                user_message = Message(
                    conversation_id=conversation_id,
                    role='user',
                    content=question
                )
                db.session.add(user_message)
                
                # 更新对话时间
                conversation.updated_at = datetime.utcnow()
                
                # 立即提交用户消息
                db.session.commit()
                current_app.logger.info(f"保存用户消息到对话 {conversation_id}: {question[:50]}")
            else:
                current_app.logger.warning(f"对话 {conversation_id} 不存在或不属于用户 {current_user.id}")
        
        # 如果远程服务器调用失败，确保有默认回答
        if not upload_success and answer == "正在思考中...":
            answer = "抱歉，服务暂时不可用，请稍后重试"
        
        # 如果有对话ID且对话存在，也保存AI回复
        if conversation_id and conversation:
            ai_message = Message(
                conversation_id=conversation_id,
                role='assistant',
                content=answer
            )
            db.session.add(ai_message)
            db.session.commit()
            current_app.logger.info(f"保存AI回复到对话 {conversation_id}: {answer[:50]}")
        
        current_app.logger.info(f"用户 {current_user.username} 进行知识库查询: {question[:50]}")
        
        return jsonify({
            'success': True,
            'data': {
                'question': question,
                'answer': answer,
                'conversation_id': conversation_id
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"知识库查询错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '查询失败，请稍后重试'
        }), 500
    