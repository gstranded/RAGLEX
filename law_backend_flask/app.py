# -*- coding: utf-8 -*-
"""
RAGLEX 法律问答系统后端
基于Flask的RESTful API服务
集成MySQL数据库、MinIO文件存储和用户认证
"""

from flask import Flask, jsonify, current_app
from flask_cors import CORS
import logging
import os
from config import Config
from models import db
from utils.auth import init_jwt
from utils.minio_client import init_minio
from blueprints import register_blueprints

def create_app(config_name='development'):
    """应用工厂函数"""
    app = Flask(__name__)
    
    # 根据配置名称加载对应配置
    if config_name == 'development':
        from config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)
    elif config_name == 'production':
        from config import ProductionConfig
        app.config.from_object(ProductionConfig)
    elif config_name == 'testing':
        from config import TestingConfig
        app.config.from_object(TestingConfig)
    else:
        from config import Config
        app.config.from_object(Config)
    
    # 初始化数据库
    db.init_app(app)
    
    # 初始化JWT
    init_jwt(app)
    
    # 初始化MinIO
    init_minio(app)
    
    # 初始化CORS
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # 配置日志
    if not app.debug:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        )
    
    # 创建必要的目录
    os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # 创建数据库表
    with app.app_context():
        try:
            db.create_all()
            current_app.logger.info("数据库表创建成功")
        except Exception as e:
            current_app.logger.error(f"数据库表创建失败: {str(e)}")
    
    # 注册蓝图
    register_blueprints(app)
    
    # 注册基础路由
    register_basic_routes(app)
    
    return app

def register_basic_routes(app):
    """注册基础路由"""
    
    @app.route('/')
    def index():
        """根路径，返回API信息"""
        return jsonify({
            'message': 'RAGLEX 法律问答系统 API',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'health': '/api/system/health',
                'auth': {
                    'register': '/api/auth/register',
                    'login': '/api/auth/login',
                    'profile': '/api/auth/profile'
                },

                'documents': '/api/documents',
                'qa': {
                    'query': '/api/qa/query',
                    'history': '/api/qa/history'
                },
                'system': {
                    'config': '/api/system/config',
                    'stats': '/api/system/stats',
                    'health': '/api/system/health'
                }
            }
        })
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': '接口不存在'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        current_app.logger.error(f"服务器内部错误: {str(error)}")
        return jsonify({'error': '服务器内部错误'}), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': '权限不足'}), 403
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': '未授权访问'}), 401

# 创建应用实例（用于开发环境）
app = create_app()

if __name__ == '__main__':
    app.run(
        host=app.config.get('HOST', '0.0.0.0'),
        port=app.config.get('PORT', 5000),
        debug=app.config.get('DEBUG', False)
    )