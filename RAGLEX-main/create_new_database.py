#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建新的SQLite数据库结构
按照用户提供的设计方案创建knowledge_files.db数据库
"""

import sqlite3
import os
from datetime import datetime

def create_new_database():
    """创建新的knowledge_files.db数据库"""
    db_path = '/home/spuser/new_law/redebug_lawbrain/LawBrain/knowledge_files.db'
    
    # 如果数据库已存在，先备份
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.rename(db_path, backup_path)
        print(f"已备份现有数据库到: {backup_path}")
    
    # 创建新数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. 创建files表 (文件信息总表)
        cursor.execute('''
            CREATE TABLE files (
                file_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                file_path TEXT NOT NULL UNIQUE,
                file_category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ 创建files表成功")
        
        # 2. 创建file_permissions表 (文件权限关系表)
        cursor.execute('''
            CREATE TABLE file_permissions (
                permission_id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                permission_type TEXT NOT NULL CHECK (permission_type IN ('public', 'private')),
                owner_id INTEGER,
                FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE
            )
        ''')
        print("✓ 创建file_permissions表成功")
        
        # 3. 创建索引以提高查询性能
        cursor.execute('CREATE INDEX idx_files_user_id ON files(user_id)')
        cursor.execute('CREATE INDEX idx_files_file_path ON files(file_path)')
        cursor.execute('CREATE INDEX idx_permissions_file_id ON file_permissions(file_id)')
        cursor.execute('CREATE INDEX idx_permissions_type ON file_permissions(permission_type)')
        cursor.execute('CREATE INDEX idx_permissions_owner ON file_permissions(owner_id)')
        print("✓ 创建索引成功")
        
        # 4. 插入一些示例数据
        sample_files = [
            (1, 1, '合同法案例分析', '/path/to/docs/共有案例/合同法案例.md', 'case'),
            (2, 1, '刑法条文解读', '/path/to/docs/法律条文/刑法.md', 'law'),
            (3, 2, '私人案例研究', '/path/to/docs/私有案例/2/私人案例.md', 'case')
        ]
        
        cursor.executemany('''
            INSERT INTO files (file_id, user_id, title, file_path, file_category)
            VALUES (?, ?, ?, ?, ?)
        ''', sample_files)
        
        sample_permissions = [
            (1, 'public', None),
            (2, 'public', None),
            (3, 'private', 2)
        ]
        
        cursor.executemany('''
            INSERT INTO file_permissions (file_id, permission_type, owner_id)
            VALUES (?, ?, ?)
        ''', sample_permissions)
        
        print("✓ 插入示例数据成功")
        
        # 提交事务
        conn.commit()
        print(f"\n🎉 新数据库创建成功: {db_path}")
        
        # 验证数据库结构
        print("\n=== 数据库结构验证 ===")
        
        # 查看表结构
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"表数量: {len(tables)}")
        for table in tables:
            print(f"  - {table[0]}")
        
        # 查看files表结构
        cursor.execute("PRAGMA table_info(files)")
        files_columns = cursor.fetchall()
        print("\nfiles表结构:")
        for col in files_columns:
            print(f"  - {col[1]} {col[2]} {'NOT NULL' if col[3] else ''} {'PRIMARY KEY' if col[5] else ''}")
        
        # 查看file_permissions表结构
        cursor.execute("PRAGMA table_info(file_permissions)")
        permissions_columns = cursor.fetchall()
        print("\nfile_permissions表结构:")
        for col in permissions_columns:
            print(f"  - {col[1]} {col[2]} {'NOT NULL' if col[3] else ''} {'PRIMARY KEY' if col[5] else ''}")
        
        # 查看示例数据
        print("\n=== 示例数据 ===")
        cursor.execute("SELECT * FROM files")
        files_data = cursor.fetchall()
        print(f"files表记录数: {len(files_data)}")
        
        cursor.execute("SELECT * FROM file_permissions")
        permissions_data = cursor.fetchall()
        print(f"file_permissions表记录数: {len(permissions_data)}")
        
    except Exception as e:
        print(f"❌ 数据库创建失败: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

def test_database_operations():
    """测试数据库基本操作"""
    db_path = '/home/spuser/new_law/redebug_lawbrain/LawBrain/knowledge_files.db'
    
    if not os.path.exists(db_path):
        print("❌ 数据库不存在，请先运行create_new_database()")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("\n=== 测试数据库操作 ===")
        
        # 测试查询所有公开文件
        cursor.execute('''
            SELECT f.file_id, f.title, f.file_path, fp.permission_type
            FROM files f
            JOIN file_permissions fp ON f.file_id = fp.file_id
            WHERE fp.permission_type = 'public'
        ''')
        public_files = cursor.fetchall()
        print(f"\n公开文件数量: {len(public_files)}")
        for file_info in public_files:
            print(f"  - ID: {file_info[0]}, 标题: {file_info[1]}, 权限: {file_info[3]}")
        
        # 测试查询特定用户的私有文件
        user_id = 2
        cursor.execute('''
            SELECT f.file_id, f.title, f.file_path, fp.permission_type, fp.owner_id
            FROM files f
            JOIN file_permissions fp ON f.file_id = fp.file_id
            WHERE fp.permission_type = 'private' AND fp.owner_id = ?
        ''', (user_id,))
        private_files = cursor.fetchall()
        print(f"\n用户{user_id}的私有文件数量: {len(private_files)}")
        for file_info in private_files:
            print(f"  - ID: {file_info[0]}, 标题: {file_info[1]}, 所有者: {file_info[4]}")
        
        # 测试添加新文件
        new_file_id = 4
        cursor.execute('''
            INSERT INTO files (file_id, user_id, title, file_path, file_category)
            VALUES (?, ?, ?, ?, ?)
        ''', (new_file_id, 1, '测试文件', '/path/to/test.md', 'test'))
        
        cursor.execute('''
            INSERT INTO file_permissions (file_id, permission_type, owner_id)
            VALUES (?, ?, ?)
        ''', (new_file_id, 'public', None))
        
        print(f"\n✓ 成功添加新文件 ID: {new_file_id}")
        
        # 测试删除文件（级联删除权限）
        cursor.execute('DELETE FROM files WHERE file_id = ?', (new_file_id,))
        print(f"✓ 成功删除文件 ID: {new_file_id}")
        
        conn.commit()
        print("\n🎉 数据库操作测试完成")
        
    except Exception as e:
        print(f"❌ 数据库操作测试失败: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    print("=== 创建新的SQLite数据库结构 ===")
    create_new_database()
    test_database_operations()
    print("\n=== 完成 ===")