# -*- coding: utf-8 -*-
"""
Blueprints模块初始化文件
用于注册所有蓝图模块
"""

from .auth import auth_bp
from .conversations import conversations_bp
from .documents import documents_bp
from .qa import qa_bp
from .system import system_bp
from .file_download import file_download_bp

def register_blueprints(app):
    """注册所有蓝图到Flask应用"""
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(conversations_bp, url_prefix='/api/conversations')
    app.register_blueprint(documents_bp, url_prefix='/api/files')
    app.register_blueprint(qa_bp, url_prefix='/api')
    app.register_blueprint(system_bp, url_prefix='/api')
    app.register_blueprint(file_download_bp, url_prefix='/api/file-download')