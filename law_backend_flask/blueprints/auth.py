# -*- coding: utf-8 -*-
"""
用户认证模块
包含用户注册、登录、个人信息管理等功能
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from models import db, User
from utils.auth import (
    login_required, hash_password, verify_password, validate_email, 
    validate_password, validate_username, generate_tokens, 
    sanitize_input, log_user_activity
)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请提供注册信息'
            }), 400
        
        # 清理输入数据
        data = sanitize_input(data)
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()
        
        # 验证必填字段
        if not all([username, email, password]):
            return jsonify({
                'success': False,
                'message': '用户名、邮箱和密码为必填项'
            }), 400
        
        # 验证用户名
        valid, error_msg = validate_username(username)
        if not valid:
            return jsonify({
                'success': False,
                'message': error_msg
            }), 400
        
        # 验证邮箱
        if not validate_email(email):
            return jsonify({
                'success': False,
                'message': '邮箱格式不正确'
            }), 400
        
        # 验证密码
        valid, error_msg = validate_password(password)
        if not valid:
            return jsonify({
                'success': False,
                'message': error_msg
            }), 400
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            return jsonify({
                'success': False,
                'message': '用户名已存在'
            }), 400
        
        # 检查邮箱是否已存在
        if User.query.filter_by(email=email).first():
            return jsonify({
                'success': False,
                'message': '邮箱已被注册'
            }), 400
        
        # 创建新用户
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            real_name=full_name,
            role='user',
            is_active=True
        )
        
        db.session.add(user)
        db.session.commit()
        
        # 记录用户活动
        log_user_activity(user.id, 'register', {'username': username, 'email': email})
        
        current_app.logger.info(f"新用户注册: {username} ({email})")
        
        return jsonify({
            'success': True,
            'message': '注册成功',
            'data': {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.real_name
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"用户注册错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '注册失败，请稍后重试'
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请提供登录信息'
            }), 400
        
        # 清理输入数据
        data = sanitize_input(data)
        
        username_or_email = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not all([username_or_email, password]):
            return jsonify({
                'success': False,
                'message': '用户名/邮箱和密码为必填项'
            }), 400
        
        # 查找用户（支持用户名或邮箱登录）
        user = User.query.filter(
            (User.username == username_or_email) | 
            (User.email == username_or_email)
        ).first()
        
        if not user:
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 401
        
        if not user.is_active:
            return jsonify({
                'success': False,
                'message': '账户已被禁用'
            }), 401
        
        # 验证密码
        if not verify_password(password, user.password_hash):
            return jsonify({
                'success': False,
                'message': '密码错误'
            }), 401
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # 生成tokens
        tokens = generate_tokens(user.id)
        
        # 记录用户活动
        log_user_activity(user.id, 'login', {'username': user.username})
        
        current_app.logger.info(f"用户登录: {user.username}")
        
        return jsonify({
            'success': True,
            'message': '登录成功',
            'data': {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'full_name': user.real_name,
                    'role': user.role,
                    'last_login': user.last_login.isoformat() if user.last_login else None
                },
                'access_token': tokens['access_token'],
                'refresh_token': tokens['refresh_token']
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"用户登录错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '登录失败，请稍后重试'
        }), 500

@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile(current_user):
    """获取用户信息"""
    try:
        return jsonify({
            'success': True,
            'data': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'full_name': current_user.real_name,
                'role': current_user.role,
                'is_active': current_user.is_active,
                'created_at': current_user.created_at.isoformat(),
                'last_login': current_user.last_login.isoformat() if current_user.last_login else None
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取用户信息错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '获取用户信息失败'
        }), 500

@auth_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile(current_user):
    """更新用户信息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请提供更新信息'
            }), 400
        
        # 清理输入数据
        data = sanitize_input(data)
        
        # 可更新的字段
        if 'full_name' in data:
            current_user.real_name = data['full_name'].strip()
        
        if 'email' in data:
            email = data['email'].strip()
            if not validate_email(email):
                return jsonify({
                    'success': False,
                    'message': '邮箱格式不正确'
                }), 400
            
            # 检查邮箱是否已被其他用户使用
            existing_user = User.query.filter(
                User.email == email,
                User.id != current_user.id
            ).first()
            
            if existing_user:
                return jsonify({
                    'success': False,
                    'message': '邮箱已被其他用户使用'
                }), 400
            
            current_user.email = email
        
        current_user.updated_at = datetime.utcnow()
        db.session.commit()
        
        # 记录用户活动
        log_user_activity(current_user.id, 'update_profile', data)
        
        current_app.logger.info(f"用户更新信息: {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': '信息更新成功',
            'data': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'full_name': current_user.real_name,
                'role': current_user.role,
                'updated_at': current_user.updated_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新用户信息错误: {str(e)}")
        return jsonify({
             'success': False,
             'message': '更新失败，请稍后重试'
         }), 500