#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户认证工具
包含JWT token生成、验证和用户权限管理
"""

from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token, create_refresh_token,
    get_jwt_identity, get_jwt, verify_jwt_in_request
)
from werkzeug.security import generate_password_hash, check_password_hash
from models import User
import re
from datetime import datetime, timedelta


jwt = JWTManager()

def init_jwt(app):
    """初始化JWT"""
    jwt.init_app(app)
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'success': False,
            'message': 'Token已过期',
            'error': 'token_expired'
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'success': False,
            'message': 'Token无效',
            'error': 'invalid_token'
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'success': False,
            'message': '缺少访问令牌',
            'error': 'authorization_required'
        }), 401

def hash_password(password):
    """密码哈希
    
    Args:
        password: 明文密码
        
    Returns:
        str: 哈希后的密码
    """
    return generate_password_hash(password)

def verify_password(password, password_hash):
    """验证密码
    
    Args:
        password: 明文密码
        password_hash: 哈希密码
        
    Returns:
        bool: 验证结果
    """
    return check_password_hash(password_hash, password)

def validate_email(email):
    """验证邮箱格式
    
    Args:
        email: 邮箱地址
        
    Returns:
        bool: 验证结果
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """验证密码强度
    
    Args:
        password: 密码
        
    Returns:
        tuple: (是否有效, 错误信息)
    """
    if len(password) < 6:
        return False, "密码长度至少6位"
    
    if len(password) > 128:
        return False, "密码长度不能超过128位"
    
    # 检查是否包含字母和数字
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    if not (has_letter and has_digit):
        return False, "密码必须包含字母和数字"
    
    return True, ""

def validate_username(username):
    """验证用户名
    
    Args:
        username: 用户名
        
    Returns:
        tuple: (是否有效, 错误信息)
    """
    if len(username) < 3:
        return False, "用户名长度至少3位"
    
    if len(username) > 50:
        return False, "用户名长度不能超过50位"
    
    # 只允许字母、数字、下划线
    pattern = r'^[a-zA-Z0-9_]+$'
    if not re.match(pattern, username):
        return False, "用户名只能包含字母、数字和下划线"
    
    return True, ""

def generate_tokens(user_id):
    """生成访问令牌和刷新令牌
    
    Args:
        user_id: 用户ID
        
    Returns:
        dict: 包含tokens的字典
    """
    access_token = create_access_token(
        identity=user_id,
        expires_delta=current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
    )
    
    refresh_token = create_refresh_token(
        identity=user_id,
        expires_delta=current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
    )
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token
    }

def get_current_user():
    """获取当前用户
    
    Returns:
        User: 用户对象或None
    """
    try:
        user_id = get_jwt_identity()
        if user_id:
            return User.query.get(user_id)
        return None
    except Exception:
        return None

def login_required(f):
    """登录装饰器"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'message': '用户不存在或已被删除'
            }), 401
        
        if not current_user.is_active:
            return jsonify({
                'success': False,
                'message': '用户账户已被禁用'
            }), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated_function

def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        if not current_user:
            return jsonify({
                'success': False,
                'message': '用户不存在或已被删除'
            }), 401
        
        if not current_user.is_active:
            return jsonify({
                'success': False,
                'message': '用户账户已被禁用'
            }), 401
        
        if current_user.role != 'admin':
            return jsonify({
                'success': False,
                'message': '需要管理员权限'
            }), 403
        
        return f(current_user, *args, **kwargs)
    
    return decorated_function

def optional_login(f):
    """可选登录装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = None
        try:
            verify_jwt_in_request(optional=True)
            current_user = get_current_user()
        except Exception:
            pass
        
        return f(current_user, *args, **kwargs)
    
    return decorated_function

def check_rate_limit(user_id, action, limit=10, window=3600):
    """检查用户操作频率限制
    
    Args:
        user_id: 用户ID
        action: 操作类型
        limit: 限制次数
        window: 时间窗口(秒)
        
    Returns:
        bool: 是否允许操作
    """
    # 这里可以使用Redis来实现更好的频率限制
    # 目前简单实现，实际项目中建议使用Redis
    return True

def sanitize_input(data):
    """清理输入数据
    
    Args:
        data: 输入数据
        
    Returns:
        清理后的数据
    """
    if isinstance(data, str):
        # 移除潜在的危险字符
        data = data.strip()
        # 可以添加更多的清理逻辑
        return data
    elif isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    else:
        return data

def log_user_activity(user_id, action, details=None):
    """记录用户活动
    
    Args:
        user_id: 用户ID
        action: 操作类型
        details: 详细信息
    """
    try:
        current_app.logger.info(
            f"用户活动 - 用户ID: {user_id}, 操作: {action}, "
            f"详情: {details}, 时间: {datetime.utcnow()}"
        )
    except Exception as e:
        current_app.logger.error(f"记录用户活动失败: {str(e)}")