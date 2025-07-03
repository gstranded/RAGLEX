# -*- coding: utf-8 -*-

from flask import Blueprint, request, jsonify, g, current_app
from models import db, Conversation, Message, User
from datetime import datetime
from utils.auth import login_required
import logging

# 创建蓝图
conversations_bp = Blueprint('conversations', __name__)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@conversations_bp.route('/', methods=['GET'])
@login_required
def get_conversations(current_user):
    """获取用户的所有对话历史"""
    try:
        # 使用认证用户的ID
        user_id = current_user.id
        
        # 获取用户的所有对话，按更新时间倒序
        conversations = Conversation.query.filter_by(user_id=user_id).order_by(Conversation.updated_at.desc()).all()
        
        return jsonify({
            'success': True,
            'data': [conv.to_dict() for conv in conversations]
        })
        
    except Exception as e:
        logger.error(f"获取对话历史失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取对话历史失败: {str(e)}'
        }), 500

@conversations_bp.route('/', methods=['POST'])
@login_required
def create_conversation(current_user):
    """创建新对话"""
    try:
        data = request.get_json()
        
        # 验证输入
        if not data or 'title' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必要参数: title'
            }), 400
        
        # 使用认证用户的ID
        user_id = current_user.id
        
        # 创建新对话
        conversation = Conversation(
            user_id=user_id,
            title=data['title']
        )
        
        db.session.add(conversation)
        db.session.flush()  # 获取conversation.id
        
        # 自动添加欢迎消息
        welcome_message = Message(
            conversation_id=conversation.id,
            role='assistant',
            content='您好，今天有什么可以帮到您的？'
        )
        
        db.session.add(welcome_message)
        db.session.commit()
        
        logger.info(f"用户 {user_id} 创建了新对话: {conversation.title}，并添加了欢迎消息")
        
        return jsonify({
            'success': True,
            'data': conversation.to_dict(),
            'message': '对话创建成功'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"创建对话失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'创建对话失败: {str(e)}'
        }), 500

@conversations_bp.route('/<int:conversation_id>/messages', methods=['GET'])
@login_required
def get_messages(current_user, conversation_id):
    """获取指定对话的所有消息"""
    try:
        # 验证对话是否存在且属于当前用户
        conversation = Conversation.query.filter_by(id=conversation_id, user_id=current_user.id).first()
        if not conversation:
            return jsonify({
                'success': False,
                'message': '对话不存在或无权访问'
            }), 404
        
        # 获取对话的所有消息，按创建时间正序
        messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.created_at.asc()).all()
        
        return jsonify({
            'success': True,
            'data': {
                'conversation': conversation.to_dict(),
                'messages': [msg.to_dict() for msg in messages]
            }
        })
        
    except Exception as e:
        logger.error(f"获取消息失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取消息失败: {str(e)}'
        }), 500

@conversations_bp.route('/<int:conversation_id>/messages', methods=['POST'])
@login_required
def add_message(current_user, conversation_id):
    """向指定对话添加消息"""
    try:
        data = request.get_json()
        
        # 验证输入
        if not data or 'role' not in data or 'content' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必要参数: role, content'
            }), 400
        
        # 验证角色
        if data['role'] not in ['user', 'assistant']:
            return jsonify({
                'success': False,
                'message': 'role 必须是 user 或 assistant'
            }), 400
        
        # 验证对话是否存在且属于当前用户
        conversation = Conversation.query.filter_by(id=conversation_id, user_id=current_user.id).first()
        if not conversation:
            return jsonify({
                'success': False,
                'message': '对话不存在或无权访问'
            }), 404
        
        # 创建新消息
        message = Message(
            conversation_id=conversation_id,
            role=data['role'],
            content=data['content']
        )
        
        # 更新对话的更新时间
        conversation.updated_at = datetime.utcnow()
        
        db.session.add(message)
        db.session.commit()
        
        logger.info(f"对话 {conversation_id} 添加了新消息: {data['role']}")
        
        return jsonify({
            'success': True,
            'data': message.to_dict(),
            'message': '消息添加成功'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"添加消息失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'添加消息失败: {str(e)}'
        }), 500

@conversations_bp.route('/<int:conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """删除指定对话"""
    try:
        # 验证对话是否存在
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return jsonify({
                'success': False,
                'message': '对话不存在'
            }), 404
        
        # 删除对话（级联删除消息）
        db.session.delete(conversation)
        db.session.commit()
        
        logger.info(f"删除了对话: {conversation_id}")
        
        return jsonify({
            'success': True,
            'message': '对话删除成功'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"删除对话失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'删除对话失败: {str(e)}'
        }), 500

@conversations_bp.route('/<int:conversation_id>', methods=['PUT'])
def update_conversation(conversation_id):
    """更新对话标题"""
    try:
        data = request.get_json()
        
        # 验证输入
        if not data or 'title' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必要参数: title'
            }), 400
        
        # 验证对话是否存在
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return jsonify({
                'success': False,
                'message': '对话不存在'
            }), 404
        
        # 更新对话标题
        conversation.title = data['title']
        conversation.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"更新了对话标题: {conversation_id} -> {data['title']}")
        
        return jsonify({
            'success': True,
            'data': conversation.to_dict(),
            'message': '对话更新成功'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新对话失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'更新对话失败: {str(e)}'
        }), 500

@conversations_bp.route('/<int:conversation_id>/context', methods=['GET'])
def get_conversation_context(conversation_id):
    """
    获取指定对话的完整上下文信息
    专为远程服务器调用设计，提供对话历史和元数据
    """
    try:
        # 参数验证
        if not conversation_id or conversation_id <= 0:
            current_app.logger.warning(f"无效的对话ID: {conversation_id}")
            return jsonify({
                'success': False,
                'error': '无效的对话ID',
                'conversation_id': conversation_id
            }), 400
        
        # 获取对话信息
        conversation = Conversation.query.filter_by(id=conversation_id).first()
        if not conversation:
            current_app.logger.warning(f"对话不存在: {conversation_id}")
            return jsonify({
                'success': False,
                'error': '对话不存在',
                'conversation_id': conversation_id
            }), 404
        
        # 获取对话消息，按时间顺序排列
        messages = Message.query.filter_by(
            conversation_id=conversation_id
        ).order_by(Message.created_at.asc()).all()
        
        # 构建消息列表
        message_list = []
        for msg in messages:
            message_data = {
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.created_at.isoformat(),
                'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            message_list.append(message_data)
        
        # 构建完整上下文
        context = {
            'success': True,
            'conversation_id': conversation.id,
            'title': conversation.title,
            'created_at': conversation.created_at.isoformat(),
            'updated_at': conversation.updated_at.isoformat(),
            'message_count': len(message_list),
            'messages': message_list
        }
        
        current_app.logger.info(f"成功获取对话上下文: conversation_id={conversation_id}, message_count={len(message_list)}")
        return jsonify(context), 200
        
    except Exception as e:
        current_app.logger.error(f"获取对话上下文失败: conversation_id={conversation_id}, error={str(e)}")
        return jsonify({
            'success': False,
            'error': '服务器内部错误',
            'message': '获取对话上下文失败，请稍后重试',
            'conversation_id': conversation_id
        }), 500