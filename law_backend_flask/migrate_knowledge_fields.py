#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为UserFile表添加知识库上传状态字段
"""

import os
import sys
from sqlalchemy import text

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db

def migrate_knowledge_fields():
    """为UserFile表添加知识库上传状态字段"""
    app = create_app('development')
    
    with app.app_context():
        try:
            # 检查字段是否已存在
            result = db.session.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'user_files' AND column_name = 'public_knowledge_uploaded'"
            ))
            
            if result.fetchone():
                print("字段已存在，无需迁移")
                return
            
            print("正在添加知识库上传状态字段...")
            
            # 添加public_knowledge_uploaded字段
            db.session.execute(text(
                "ALTER TABLE user_files ADD COLUMN public_knowledge_uploaded BOOLEAN DEFAULT FALSE"
            ))
            
            # 添加private_knowledge_uploaded字段
            db.session.execute(text(
                "ALTER TABLE user_files ADD COLUMN private_knowledge_uploaded BOOLEAN DEFAULT FALSE"
            ))
            
            # 提交更改
            db.session.commit()
            
            print("知识库上传状态字段添加成功！")
            print("- public_knowledge_uploaded: 公用知识库上传状态")
            print("- private_knowledge_uploaded: 私有知识库上传状态")
            
        except Exception as e:
            db.session.rollback()
            print(f"迁移失败: {str(e)}")
            sys.exit(1)

if __name__ == '__main__':
    migrate_knowledge_fields()