#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # 用户基本信息
    real_name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    position = db.Column(db.String(100), nullable=True)
    
    # 用户状态
    is_active = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(20), default='user')  # admin, user
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # 关联关系
    files = db.relationship('UserFile', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_sensitive=False):
        """转换为字典"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'real_name': self.real_name,
            'phone': self.phone,
            'department': self.department,
            'position': self.position,
            'is_active': self.is_active,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'file_count': self.files.count()
        }
        return data
    
    def __repr__(self):
        return f'<User {self.username}>'

class UserFile(db.Model):
    """用户文件模型"""
    __tablename__ = 'user_files'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)  # 原始文件名
    file_category = db.Column(db.String(50), nullable=False, default='general')  # 文件分类
    case_title = db.Column(db.String(255), nullable=True)  # 案件标题
    case_summary = db.Column(db.Text, nullable=True)  # 案件摘要
    minio_path = db.Column(db.String(500), nullable=False)  # MinIO存储路径
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 用户ID
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)  # 上传时间
    public_knowledge_uploaded = db.Column(db.Boolean, default=False)  # 是否已上传到公用知识库
    private_knowledge_uploaded = db.Column(db.Boolean, default=False)  # 是否已上传到私有知识库
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'filename': self.filename,
            'file_category': self.file_category,
            'case_title': self.case_title,
            'case_summary': self.case_summary,
            'minio_path': self.minio_path,
            'user_id': self.user_id,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'owner_name': self.owner.username if self.owner else None,
            'public_knowledge_uploaded': self.public_knowledge_uploaded,
            'private_knowledge_uploaded': self.private_knowledge_uploaded
        }
    
    def __repr__(self):
        return f'<UserFile {self.filename}>'

class SystemConfig(db.Model):
    """系统配置模型"""
    __tablename__ = 'system_config'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<SystemConfig {self.key}>'





class Conversation(db.Model):
    """对话模型"""
    __tablename__ = 'conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)  # 对话标题
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    user = db.relationship('User', backref='conversations')
    messages = db.relationship('Message', backref='conversation', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'message_count': self.messages.count()
        }
    
    def __repr__(self):
        return f'<Conversation {self.id}: {self.title}>'

class Message(db.Model):
    """消息模型"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # user, assistant
    content = db.Column(db.Text, nullable=False)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Message {self.id}: {self.role}>'