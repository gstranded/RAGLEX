import os
from datetime import timedelta

class Config:
    """基础配置类"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://root:Mysql123!@localhost:3306/law_system'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # JWT配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-string'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # MinIO配置
    MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT') or 'localhost:9000'
    MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY') or 'minioadmin'
    MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY') or 'minioadmin'
    MINIO_SECURE = os.environ.get('MINIO_SECURE', 'False').lower() == 'true'
    MINIO_BUCKET_NAME = os.environ.get('MINIO_BUCKET_NAME') or 'law-documents'
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB for PDF files
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'json'}
    
    # 数据存储配置
    DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    
    # CORS配置
    CORS_ORIGINS = ['http://localhost:13000', 'http://127.0.0.1:13000', 'http://localhost:13001', 'http://127.0.0.1:13001']
    
    # API配置
    API_VERSION = 'v1'
    API_PREFIX = '/api'
    
    # 分页配置
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    PAGINATION = {
        'DEFAULT_PAGE_SIZE': 20,
        'MAX_PAGE_SIZE': 100
    }
    
    # 缓存配置
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 创建必要的目录
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.DATA_FOLDER, exist_ok=True)
        
        # 初始化数据库
        from models import db
        db.init_app(app)
        
        # 初始化JWT
        from flask_jwt_extended import JWTManager
        jwt = JWTManager(app)
        
        # 初始化MinIO客户端
        from utils.minio_client import init_minio
        init_minio(app)

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    # Local/dev defaults: allow SQLite without requiring MySQL.
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DEV_DATABASE_URL')
        or os.environ.get('DATABASE_URL')
        or f"sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'raglex-dev.sqlite3')}"
    )

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    
    # 生产环境安全配置
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # 生产环境数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://root:Mysql123!@localhost:3306/law_system'
    
class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:Mysql123!@localhost:3306/law_system_test'

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# 模型配置
MODEL_CONFIG = {
    'embedding_models': {
        'text2vec-base': {
            'name': 'text2vec-base',
            'description': '基础文本向量模型',
            'dimension': 768,
            'max_length': 512
        },
        'RAGLEX': {
            'name': 'RAGLEX',
            'description': 'RAGLEX专用向量模型',
            'dimension': 1024,
            'max_length': 1024
        }
    },
    'language_models': {
        'ChatGLM-6B': {
            'name': 'ChatGLM-6B',
            'description': '智谱AI大语言模型',
            'max_tokens': 2048,
            'temperature': 0.7
        },
        'Qwen-7B': {
            'name': 'Qwen-7B',
            'description': '通义千问大语言模型',
            'max_tokens': 2048,
            'temperature': 0.7
        }
    }
}

# 知识库配置
KNOWLEDGE_CONFIG = {
    'types': {
        'criminalLaw': {
            'name': '法律条文',
            'description': '刑法、民法等法律条文',
            'color': '#ff6b6b'
        },
        'criminalBook': {
            'name': '历史案例',
            'description': '历史法律案例库',
            'color': '#4ecdc4'
        },
        'civilLaw': {
            'name': '民事法律',
            'description': '民事相关法律条文',
            'color': '#45b7d1'
        },
        'administrativeLaw': {
            'name': '行政法律',
            'description': '行政相关法律条文',
            'color': '#f9ca24'
        }
    },
    'search': {
        'default_top_k': 20,
        'max_top_k': 50,
        'min_similarity': 0.6
    }
}

# 案例类型配置
CASE_TYPES = {
    '刑事': {
        'name': '刑事案例',
        'color': '#e74c3c',
        'icon': '⚖️'
    },
    '民事': {
        'name': '民事案例',
        'color': '#3498db',
        'icon': '📋'
    },
    '行政': {
        'name': '行政案例',
        'color': '#f39c12',
        'icon': '🏛️'
    },
    '商事': {
        'name': '商事案例',
        'color': '#27ae60',
        'icon': '💼'
    }
}