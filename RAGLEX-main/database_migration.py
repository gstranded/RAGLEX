#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：实现权限表分离方案
将现有的file_records表重构为files表和file_permissions表
"""

import sqlite3
import os
from typing import List, Dict, Any
from datetime import datetime

def backup_existing_data() -> List[Dict[str, Any]]:
    """
    备份现有的file_records表数据
    
    Returns:
        List[Dict]: 现有数据的列表
    """
    conn = sqlite3.connect('knowledge_files.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM file_records')
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        
        backup_data = []
        for row in rows:
            backup_data.append(dict(zip(columns, row)))
        
        print(f"✅ 成功备份 {len(backup_data)} 条记录")
        return backup_data
        
    except sqlite3.OperationalError as e:
        print(f"⚠️ 备份数据时出错: {e}")
        return []
    finally:
        conn.close()

def create_new_tables():
    """
    创建新的表结构：files表和file_permissions表
    """
    conn = sqlite3.connect('knowledge_files.db')
    cursor = conn.cursor()
    
    try:
        # 创建files表（只存文件本身的信息）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                file_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,          -- 文件上传者的ID
                title TEXT NOT NULL,
                file_path TEXT UNIQUE NOT NULL,    -- 文件物理路径，应该是唯一的
                file_category TEXT,                -- 'case', 'general' 等
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建file_permissions表（专门管理权限）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_permissions (
                permission_id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,                    -- 关联到哪个文件
                permission_type TEXT NOT NULL,               -- 权限类型: 'public' 或 'private'
                owner_id INTEGER,                            -- 权限归属者: 如果是private，则为user_id；如果是public，可以为NULL
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files (file_id) ON DELETE CASCADE
            )
        ''')
        
        # 创建索引以提高查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_permissions_file_id ON file_permissions(file_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_permissions_type ON file_permissions(permission_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_permissions_owner ON file_permissions(owner_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_user_id ON files(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_path ON files(file_path)')
        
        conn.commit()
        print("✅ 成功创建新的表结构")
        
    except Exception as e:
        print(f"❌ 创建表时出错: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def migrate_data(backup_data: List[Dict[str, Any]]):
    """
    将备份的数据迁移到新的表结构中
    
    Args:
        backup_data: 备份的原始数据
    """
    if not backup_data:
        print("⚠️ 没有数据需要迁移")
        return
    
    conn = sqlite3.connect('knowledge_files.db')
    cursor = conn.cursor()
    
    try:
        migrated_files = 0
        migrated_permissions = 0
        
        for record in backup_data:
            file_id = record['file_id']
            user_id = record['user_id']
            title = record.get('title', '无标题')
            file_path = record['file_path']
            file_category = record.get('file_category', 'case')
            created_at = record.get('created_at')
            knowledge_types = record.get('knowledge_types', '')
            
            # 插入到files表
            cursor.execute('''
                INSERT OR REPLACE INTO files 
                (file_id, user_id, title, file_path, file_category, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (file_id, user_id, title, file_path, file_category, created_at))
            migrated_files += 1
            
            # 解析knowledge_types并插入到file_permissions表
            if knowledge_types:
                # 处理旧的knowledge_types格式（如"public,private"或"system,4"）
                types = [t.strip() for t in knowledge_types.split(',') if t.strip()]
                
                for type_or_id in types:
                    if type_or_id == 'public' or type_or_id == 'system':
                        # 公开权限
                        cursor.execute('''
                            INSERT INTO file_permissions 
                            (file_id, permission_type, owner_id)
                            VALUES (?, ?, ?)
                        ''', (file_id, 'public', None))
                        migrated_permissions += 1
                    elif type_or_id == 'private' or type_or_id.isdigit():
                        # 私有权限
                        owner_id = user_id if type_or_id == 'private' else int(type_or_id)
                        cursor.execute('''
                            INSERT INTO file_permissions 
                            (file_id, permission_type, owner_id)
                            VALUES (?, ?, ?)
                        ''', (file_id, 'private', owner_id))
                        migrated_permissions += 1
            else:
                # 如果没有knowledge_types，默认为私有权限
                cursor.execute('''
                    INSERT INTO file_permissions 
                    (file_id, permission_type, owner_id)
                    VALUES (?, ?, ?)
                ''', (file_id, 'private', user_id))
                migrated_permissions += 1
        
        conn.commit()
        print(f"✅ 成功迁移 {migrated_files} 个文件记录和 {migrated_permissions} 个权限记录")
        
    except Exception as e:
        print(f"❌ 迁移数据时出错: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def rename_old_table():
    """
    重命名旧的file_records表为file_records_backup
    """
    conn = sqlite3.connect('knowledge_files.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('ALTER TABLE file_records RENAME TO file_records_backup')
        conn.commit()
        print("✅ 成功将旧表重命名为file_records_backup")
    except Exception as e:
        print(f"❌ 重命名表时出错: {e}")
        raise
    finally:
        conn.close()

def verify_migration():
    """
    验证迁移结果
    """
    conn = sqlite3.connect('knowledge_files.db')
    cursor = conn.cursor()
    
    try:
        # 检查files表
        cursor.execute('SELECT COUNT(*) FROM files')
        files_count = cursor.fetchone()[0]
        
        # 检查file_permissions表
        cursor.execute('SELECT COUNT(*) FROM file_permissions')
        permissions_count = cursor.fetchone()[0]
        
        # 检查权限类型分布
        cursor.execute('SELECT permission_type, COUNT(*) FROM file_permissions GROUP BY permission_type')
        permission_stats = cursor.fetchall()
        
        print(f"\n📊 迁移验证结果:")
        print(f"   - files表: {files_count} 条记录")
        print(f"   - file_permissions表: {permissions_count} 条记录")
        print(f"   - 权限分布:")
        for ptype, count in permission_stats:
            print(f"     * {ptype}: {count} 条")
        
        # 显示一些示例数据
        print(f"\n📋 示例数据:")
        cursor.execute('''
            SELECT f.file_id, f.title, f.user_id, 
                   GROUP_CONCAT(fp.permission_type || ':' || COALESCE(fp.owner_id, 'NULL')) as permissions
            FROM files f
            LEFT JOIN file_permissions fp ON f.file_id = fp.file_id
            GROUP BY f.file_id
            LIMIT 5
        ''')
        
        examples = cursor.fetchall()
        for file_id, title, user_id, permissions in examples:
            print(f"   - 文件{file_id}: {title[:30]}... (上传者:{user_id}) -> 权限: {permissions}")
        
    except Exception as e:
        print(f"❌ 验证时出错: {e}")
    finally:
        conn.close()

def run_migration():
    """
    执行完整的数据库迁移流程
    """
    print("🚀 开始数据库迁移：权限表分离方案")
    print("=" * 50)
    
    try:
        # 步骤1：备份现有数据
        print("\n📦 步骤1：备份现有数据...")
        backup_data = backup_existing_data()
        
        # 步骤2：创建新表
        print("\n🏗️ 步骤2：创建新的表结构...")
        create_new_tables()
        
        # 步骤3：迁移数据
        print("\n📋 步骤3：迁移数据到新表...")
        migrate_data(backup_data)
        
        # 步骤4：重命名旧表
        print("\n🔄 步骤4：重命名旧表为备份...")
        rename_old_table()
        
        # 步骤5：验证迁移
        print("\n✅ 步骤5：验证迁移结果...")
        verify_migration()
        
        print("\n🎉 数据库迁移完成！")
        print("\n💡 提示：")
        print("   - 旧数据已保存在 file_records_backup 表中")
        print("   - 新的权限管理系统已启用")
        print("   - 可以开始使用新的权限管理函数")
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        print("\n🔧 建议：")
        print("   - 检查数据库文件权限")
        print("   - 确保没有其他程序正在使用数据库")
        print("   - 查看详细错误信息并修复问题")
        raise

if __name__ == "__main__":
    run_migration()