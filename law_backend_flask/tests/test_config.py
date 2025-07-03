#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试配置文件
管理测试环境的配置参数
"""

import os
from typing import Dict, Any


class TestConfig:
    """测试配置类"""
    
    # 基础配置
    BASE_URL = os.getenv('TEST_BASE_URL', 'http://localhost:5000')
    TIMEOUT = int(os.getenv('TEST_TIMEOUT', '30'))
    
    # 测试用户配置
    ADMIN_USERNAME = os.getenv('TEST_ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('TEST_ADMIN_PASSWORD', 'admin123')
    ADMIN_EMAIL = os.getenv('TEST_ADMIN_EMAIL', 'admin@test.com')
    
    # 测试用户配置
    TEST_USER_PREFIX = 'test_user_'
    TEST_EMAIL_DOMAIN = '@test.com'
    DEFAULT_PASSWORD = 'test123456'
    
    # API端点配置
    API_ENDPOINTS = {
        'health': '/api/health',
        'register': '/api/register',
        'login': '/api/login',
        'profile': '/api/profile',
        'cases': '/api/cases',
        'knowledge': '/api/knowledge',
        'files': '/api/files',
        'history': '/api/history',
        'config': '/api/config',
        'stats': '/api/stats'
    }
    
    # 测试数据配置
    TEST_CASE_DATA = {
        'case_number': 'TEST-CASE-001',
        'case_title': '测试案件标题',
        'case_type': '合同纠纷',
        'case_description': '这是一个用于测试的案件描述',
        'case_status': '进行中',
        'plaintiff': '测试原告',
        'defendant': '测试被告',
        'court': '测试法院',
        'judge': '测试法官',
        'lawyer': '测试律师'
    }
    
    # 文件上传配置
    FILE_UPLOAD_CONFIG = {
        'max_file_size': 10 * 1024 * 1024,  # 10MB
        'allowed_extensions': ['txt', 'pdf', 'doc', 'docx', 'json'],
        'forbidden_extensions': ['exe', 'bat', 'sh', 'js', 'php'],
        'test_file_content': '这是一个测试文件的内容，用于验证文件上传功能。'
    }
    
    # 知识库查询配置
    KNOWLEDGE_QUERY_CONFIG = {
        'test_questions': [
            '什么是合同法？',
            '如何处理合同纠纷？',
            '劳动法的基本原则是什么？',
            '知识产权保护的范围包括哪些？',
            '民事诉讼的基本程序是什么？'
        ],
        'invalid_questions': [
            '',  # 空问题
            ' ',  # 空白问题
            'a' * 1000,  # 超长问题
            '!@#$%^&*()',  # 特殊字符
        ],
        'max_question_length': 500,
        'timeout': 30
    }
    
    # 性能测试配置
    PERFORMANCE_CONFIG = {
        'concurrent_users': 5,
        'requests_per_user': 10,
        'max_response_time': 5.0,  # 秒
        'acceptable_error_rate': 0.05  # 5%
    }
    
    # 数据库配置（如果需要直接访问数据库）
    DATABASE_CONFIG = {
        'host': os.getenv('TEST_DB_HOST', 'localhost'),
        'port': int(os.getenv('TEST_DB_PORT', '3306')),
        'username': os.getenv('TEST_DB_USERNAME', 'root'),
        'password': os.getenv('TEST_DB_PASSWORD', ''),
        'database': os.getenv('TEST_DB_NAME', 'raglex_test')
    }
    
    # 日志配置
    LOGGING_CONFIG = {
        'level': os.getenv('TEST_LOG_LEVEL', 'INFO'),
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file': os.getenv('TEST_LOG_FILE', 'tests.log')
    }
    
    # 重试配置
    RETRY_CONFIG = {
        'max_retries': 3,
        'retry_delay': 1,  # 秒
        'backoff_factor': 2
    }
    
    @classmethod
    def get_test_user_data(cls, suffix: str = None) -> Dict[str, Any]:
        """生成测试用户数据"""
        import time
        
        if suffix is None:
            suffix = str(int(time.time()))
        
        return {
            'username': f'{cls.TEST_USER_PREFIX}{suffix}',
            'email': f'{cls.TEST_USER_PREFIX}{suffix}{cls.TEST_EMAIL_DOMAIN}',
            'password': cls.DEFAULT_PASSWORD,
            'full_name': f'测试用户{suffix}',
            'phone': f'1380000{suffix[-4:].zfill(4)}',
            'department': '测试部门',
            'position': '测试职位'
        }
    
    @classmethod
    def get_test_case_data(cls, suffix: str = None) -> Dict[str, Any]:
        """生成测试案件数据"""
        import time
        
        if suffix is None:
            suffix = str(int(time.time()))
        
        case_data = cls.TEST_CASE_DATA.copy()
        case_data.update({
            'case_number': f'TEST-CASE-{suffix}',
            'case_title': f'测试案件标题-{suffix}',
            'case_description': f'这是一个用于测试的案件描述-{suffix}'
        })
        
        return case_data
    
    @classmethod
    def get_api_url(cls, endpoint: str) -> str:
        """获取API完整URL"""
        if endpoint.startswith('/'):
            return f'{cls.BASE_URL}{endpoint}'
        elif endpoint in cls.API_ENDPOINTS:
            return f'{cls.BASE_URL}{cls.API_ENDPOINTS[endpoint]}'
        else:
            return f'{cls.BASE_URL}/api/{endpoint}'
    
    @classmethod
    def is_development_mode(cls) -> bool:
        """检查是否为开发模式"""
        return os.getenv('TEST_ENV', 'development').lower() == 'development'
    
    @classmethod
    def should_cleanup_data(cls) -> bool:
        """检查是否应该清理测试数据"""
        return os.getenv('TEST_CLEANUP', 'true').lower() == 'true'
    
    @classmethod
    def get_environment_info(cls) -> Dict[str, Any]:
        """获取测试环境信息"""
        return {
            'base_url': cls.BASE_URL,
            'timeout': cls.TIMEOUT,
            'development_mode': cls.is_development_mode(),
            'cleanup_data': cls.should_cleanup_data(),
            'log_level': cls.LOGGING_CONFIG['level'],
            'max_retries': cls.RETRY_CONFIG['max_retries']
        }


# 环境特定配置
class DevelopmentTestConfig(TestConfig):
    """开发环境测试配置"""
    BASE_URL = 'http://localhost:5000'
    TIMEOUT = 30


class StagingTestConfig(TestConfig):
    """预发布环境测试配置"""
    BASE_URL = os.getenv('STAGING_BASE_URL', 'http://staging.raglex.com')
    TIMEOUT = 60


class ProductionTestConfig(TestConfig):
    """生产环境测试配置（仅用于只读测试）"""
    BASE_URL = os.getenv('PROD_BASE_URL', 'http://raglex.com')
    TIMEOUT = 120
    
    # 生产环境不允许创建测试数据
    @classmethod
    def should_cleanup_data(cls) -> bool:
        return False


# 根据环境变量选择配置
def get_test_config() -> TestConfig:
    """根据环境变量获取测试配置"""
    env = os.getenv('TEST_ENV', 'development').lower()
    
    if env == 'staging':
        return StagingTestConfig()
    elif env == 'production':
        return ProductionTestConfig()
    else:
        return DevelopmentTestConfig()


# 全局配置实例
config = get_test_config()