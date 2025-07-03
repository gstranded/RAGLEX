#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
用于创建数据库表和初始数据
"""

import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User, UserFile, SystemConfig
from config import Config

def init_database():
    """初始化数据库"""
    app = create_app('development')
    
    with app.app_context():
        try:
            # 删除所有表（谨慎使用）
            print("正在删除现有表...")
            db.drop_all()
            
            # 创建所有表
            print("正在创建数据库表...")
            db.create_all()
            
            # 创建默认管理员用户
            print("正在创建默认管理员用户...")
            admin_user = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123'),
                role='admin',
                real_name='系统管理员',
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.session.add(admin_user)
            
            # 创建测试用户
            print("正在创建测试用户...")
            test_user = User(
                username='testuser',
                email='test@example.com',
                password_hash=generate_password_hash('test123'),
                role='user',
                real_name='测试用户',
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.session.add(test_user)
            
            # 创建系统配置
            print("正在创建系统配置...")
            configs = [
                SystemConfig(
                    key='system_name',
                    value='用户文件管理系统',
                    description='系统名称'
                ),
                SystemConfig(
                    key='system_version',
                    value='1.0.0',
                    description='系统版本'
                ),
                SystemConfig(
                    key='max_upload_size',
                    value='52428800',  # 50MB
                    description='最大上传文件大小（字节）'
                ),
                SystemConfig(
                    key='allowed_file_types',
                    value='pdf,doc,docx,txt,jpg,jpeg,png,zip,rar',
                    description='允许上传的文件类型'
                )
            ]
            
            for config in configs:
                db.session.add(config)
            
            # 提交所有更改
            db.session.commit()
            
            print("\n数据库初始化完成！")
            print("默认管理员账户:")
            print("  用户名: admin")
            print("  密码: admin123")
            print("\n测试用户账户:")
            print("  用户名: testuser")
            print("  密码: test123")
            
        except Exception as e:
            db.session.rollback()
            print(f"数据库初始化失败: {str(e)}")
            raise

def reset_database():
    """重置数据库（删除所有数据并重新初始化）"""
    print("警告：此操作将删除所有现有数据！")
    confirm = input("确认要重置数据库吗？(yes/no): ")
    
    if confirm.lower() in ['yes', 'y']:
        init_database()
    else:
        print("操作已取消。")

def create_tables_only():
    """仅创建表结构，不插入数据"""
    app = create_app('development')
    
    with app.app_context():
        try:
            print("正在创建数据库表...")
            db.create_all()
            print("数据库表创建完成！")
            
        except Exception as e:
            print(f"创建数据库表失败: {str(e)}")
            raise

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库初始化工具')
    parser.add_argument('--reset', action='store_true', help='重置数据库（删除所有数据）')
    parser.add_argument('--tables-only', action='store_true', help='仅创建表结构')
    
    args = parser.parse_args()
    
    if args.reset:
        reset_database()
    elif args.tables_only:
        create_tables_only()
    else:
        init_database()