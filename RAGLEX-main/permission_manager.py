#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
权限管理模块：基于新的权限表分离方案
提供简洁、高效的权限管理功能
"""

import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

class PermissionManager:
    """
    权限管理器：负责所有文件权限相关的数据库操作
    """
    
    def __init__(self, db_path: str = 'knowledge_files.db'):
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def add_file(self, file_id: int, user_id: int, title: str, file_path: str, 
                 file_category: str = 'case') -> bool:
        """
        添加文件记录到files表
        
        Args:
            file_id: 文件ID
            user_id: 上传用户ID
            title: 文件标题
            file_path: 文件路径
            file_category: 文件分类
        
        Returns:
            bool: 是否成功
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO files 
                (file_id, user_id, title, file_path, file_category)
                VALUES (?, ?, ?, ?, ?)
            ''', (file_id, user_id, title, file_path, file_category))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ 添加文件记录失败: {e}")
            return False
        finally:
            conn.close()
    
    def add_permission(self, file_id: int, permission_type: str, owner_id: Optional[int] = None) -> bool:
        """
        为文件添加权限
        
        Args:
            file_id: 文件ID
            permission_type: 权限类型 ('public' 或 'private')
            owner_id: 权限归属者ID (private权限时必须提供)
        
        Returns:
            bool: 是否成功
        """
        if permission_type not in ['public', 'private']:
            print(f"❌ 无效的权限类型: {permission_type}")
            return False
        
        if permission_type == 'private' and owner_id is None:
            print("❌ 私有权限必须指定owner_id")
            return False
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 检查是否已存在相同的权限记录
            cursor.execute('''
                SELECT COUNT(*) FROM file_permissions 
                WHERE file_id = ? AND permission_type = ? AND owner_id = ?
            ''', (file_id, permission_type, owner_id))
            
            if cursor.fetchone()[0] > 0:
                print(f"⚠️ 权限已存在: file_id={file_id}, type={permission_type}, owner_id={owner_id}")
                return True
            
            cursor.execute('''
                INSERT INTO file_permissions 
                (file_id, permission_type, owner_id)
                VALUES (?, ?, ?)
            ''', (file_id, permission_type, owner_id))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ 添加权限失败: {e}")
            return False
        finally:
            conn.close()
    
    def remove_permission(self, file_id: int, permission_type: str, owner_id: Optional[int] = None) -> bool:
        """
        删除文件的特定权限
        
        Args:
            file_id: 文件ID
            permission_type: 权限类型
            owner_id: 权限归属者ID
        
        Returns:
            bool: 是否成功
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM file_permissions 
                WHERE file_id = ? AND permission_type = ? AND owner_id = ?
            ''', (file_id, permission_type, owner_id))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                print(f"✅ 成功删除权限: file_id={file_id}, type={permission_type}, owner_id={owner_id}")
                return True
            else:
                print(f"⚠️ 未找到要删除的权限: file_id={file_id}, type={permission_type}, owner_id={owner_id}")
                return False
            
        except Exception as e:
            print(f"❌ 删除权限失败: {e}")
            return False
        finally:
            conn.close()
    
    def get_user_accessible_file_ids(self, user_id: int) -> List[int]:
        """
        获取用户有权访问的所有文件ID列表
        
        Args:
            user_id: 用户ID
        
        Returns:
            List[int]: 文件ID列表
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 查询用户可访问的文件：公开文件 + 用户私有文件
            cursor.execute('''
                SELECT DISTINCT file_id FROM file_permissions 
                WHERE permission_type = 'public' 
                   OR (permission_type = 'private' AND owner_id = ?)
            ''', (user_id,))
            
            file_ids = [row[0] for row in cursor.fetchall()]
            return file_ids
            
        except Exception as e:
            print(f"❌ 获取用户可访问文件失败: {e}")
            return []
        finally:
            conn.close()
    
    def get_user_private_file_ids(self, user_id: int) -> List[int]:
        """
        【新增】仅获取用户私有的文件ID列表
        
        Args:
            user_id: 用户ID
        
        Returns:
            List[int]: 该用户私有文件的ID列表
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 只查询 permission_type = 'private' 且 owner_id 匹配的文件
            cursor.execute('''
                SELECT DISTINCT file_id FROM file_permissions
                WHERE permission_type = 'private' AND owner_id = ?
            ''', (user_id,))
            
            file_ids = [row[0] for row in cursor.fetchall()]
            return file_ids
            
        except Exception as e:
            print(f"❌ 获取用户私有文件失败: {e}")
            return []
        finally:
            conn.close()
    
    def get_public_file_ids(self) -> List[int]:
        """
        【新增】获取所有公共文件的ID列表
        
        Returns:
            List[int]: 公共文件的ID列表
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 只查询 permission_type = 'public' 的文件
            cursor.execute('''
                SELECT DISTINCT file_id FROM file_permissions
                WHERE permission_type = 'public'
            ''')
            
            file_ids = [row[0] for row in cursor.fetchall()]
            return file_ids
            
        except Exception as e:
            print(f"❌ 获取公共文件失败: {e}")
            return []
        finally:
            conn.close()
    
    def get_file_permissions(self, file_id: int) -> List[Dict[str, Any]]:
        """
        【修正版】获取文件的所有权限信息
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 【修正】只查询存在的列：permission_type, owner_id
            cursor.execute('''
                SELECT permission_type, owner_id
                FROM file_permissions
                WHERE file_id = ?
            ''', (file_id,))
            
            permissions = []
            for row in cursor.fetchall():
                # 【修正】只处理查询出的两列数据
                permissions.append({
                    'permission_type': row[0],
                    'owner_id': row[1]
                })
            
            return permissions
            
        except Exception as e:
            print(f"❌ 获取文件权限失败: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def is_file_accessible_by_user(self, file_id: int, user_id: int) -> bool:
        """
        检查用户是否有权访问特定文件
        
        Args:
            file_id: 文件ID
            user_id: 用户ID
        
        Returns:
            bool: 是否有权访问
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) FROM file_permissions 
                WHERE file_id = ? AND (
                    permission_type = 'public' 
                    OR (permission_type = 'private' AND owner_id = ?)
                )
            ''', (file_id, user_id))
            
            return cursor.fetchone()[0] > 0
            
        except Exception as e:
            print(f"❌ 检查文件访问权限失败: {e}")
            return False
        finally:
            conn.close()
    
    def set_file_permissions(self, file_id: int, knowledge_types: List[str], user_id: int) -> bool:
        """
        根据knowledge_types设置文件权限（兼容旧接口）
        
        Args:
            file_id: 文件ID
            knowledge_types: 权限类型列表 ['public', 'private']
            user_id: 用户ID
        
        Returns:
            bool: 是否成功
        """
        try:
            # 先清除该文件的所有权限
            self.clear_file_permissions(file_id)
            
            success = True
            
            for knowledge_type in knowledge_types:
                if knowledge_type == 'public':
                    success &= self.add_permission(file_id, 'public')
                elif knowledge_type == 'private':
                    success &= self.add_permission(file_id, 'private', user_id)
                else:
                    print(f"⚠️ 未知的权限类型: {knowledge_type}")
            
            return success
            
        except Exception as e:
            print(f"❌ 设置文件权限失败: {e}")
            return False
    
    def clear_file_permissions(self, file_id: int) -> bool:
        """
        清除文件的所有权限
        
        Args:
            file_id: 文件ID
        
        Returns:
            bool: 是否成功
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM file_permissions WHERE file_id = ?', (file_id,))
            conn.commit()
            
            return True
            
        except Exception as e:
            print(f"❌ 清除文件权限失败: {e}")
            return False
        finally:
            conn.close()
    
    def delete_file(self, file_id: int) -> bool:
        """
        删除文件及其所有权限（CASCADE删除）
        
        Args:
            file_id: 文件ID
        
        Returns:
            bool: 是否成功
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 由于设置了ON DELETE CASCADE，删除files表记录会自动删除相关权限
            cursor.execute('DELETE FROM files WHERE file_id = ?', (file_id,))
            conn.commit()
            
            return True
            
        except Exception as e:
            print(f"❌ 删除文件失败: {e}")
            return False
        finally:
            conn.close()
    
    def get_file_info(self, file_id: int) -> Optional[Dict[str, Any]]:
        """
        获取文件的基本信息
        
        Args:
            file_id: 文件ID
        
        Returns:
            Optional[Dict]: 文件信息
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT file_id, user_id, title, file_path, file_category, created_at
                FROM files WHERE file_id = ?
            ''', (file_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'file_id': row[0],
                    'user_id': row[1],
                    'title': row[2],
                    'file_path': row[3],
                    'file_category': row[4],
                    'created_at': row[5]
                }
            return None
        except Exception as e:
            print(f"❌ 获取文件信息失败: {e}")
            return None
    
    def update_file_path(self, file_id: int, new_file_path: str) -> bool:
        """
        更新文件路径
        
        Args:
            file_id: 文件ID
            new_file_path: 新的文件路径
        
        Returns:
            bool: 是否成功
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE files SET file_path = ? WHERE file_id = ?
            ''', (new_file_path, file_id))
            
            conn.commit()
            conn.close()
            
            print(f"✅ 文件路径更新成功: file_id={file_id}, new_path={new_file_path}")
            return True
            
        except Exception as e:
            print(f"❌ 更新文件路径失败: {e}")
            return False
        finally:
            conn.close()
    
    def get_user_files_with_permissions(self, user_id: int) -> List[Dict[str, Any]]:
        """
        获取用户可访问的所有文件及其权限信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            List[Dict]: 文件和权限信息列表
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT f.file_id, f.user_id, f.title, f.file_path, f.file_category, f.created_at,
                       GROUP_CONCAT(fp.permission_type || ':' || COALESCE(fp.owner_id, 'NULL')) as permissions
                FROM files f
                INNER JOIN file_permissions fp ON f.file_id = fp.file_id
                WHERE fp.permission_type = 'public' 
                   OR (fp.permission_type = 'private' AND fp.owner_id = ?)
                GROUP BY f.file_id
                ORDER BY f.created_at DESC
            ''', (user_id,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'file_id': row[0],
                    'user_id': row[1],
                    'title': row[2],
                    'file_path': row[3],
                    'file_category': row[4],
                    'created_at': row[5],
                    'permissions': row[6]
                })
            
            return results
            
        except Exception as e:
            print(f"❌ 获取用户文件列表失败: {e}")
            return []
        finally:
            conn.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取权限管理统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 文件总数
            cursor.execute('SELECT COUNT(*) FROM files')
            total_files = cursor.fetchone()[0]
            
            # 权限总数
            cursor.execute('SELECT COUNT(*) FROM file_permissions')
            total_permissions = cursor.fetchone()[0]
            
            # 权限类型分布
            cursor.execute('SELECT permission_type, COUNT(*) FROM file_permissions GROUP BY permission_type')
            permission_distribution = dict(cursor.fetchall())
            
            # 用户文件分布
            cursor.execute('SELECT user_id, COUNT(*) FROM files GROUP BY user_id ORDER BY COUNT(*) DESC LIMIT 10')
            user_file_distribution = cursor.fetchall()
            
            return {
                'total_files': total_files,
                'total_permissions': total_permissions,
                'permission_distribution': permission_distribution,
                'top_users': user_file_distribution
            }
            
        except Exception as e:
            print(f"❌ 获取统计信息失败: {e}")
            return {}
        finally:
            conn.close()

# 全局权限管理器实例
_permission_manager = None

def get_permission_manager() -> PermissionManager:
    """
    获取全局权限管理器实例
    
    Returns:
        PermissionManager: 权限管理器实例
    """
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager

# 全局权限管理器实例
_permission_manager: Optional[PermissionManager] = None

def get_permission_manager() -> PermissionManager:
    """
    获取全局权限管理器实例
    
    Returns:
        PermissionManager: 权限管理器实例
    """
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager

# 便捷函数
def add_file_with_permissions(file_id: int, user_id: int, title: str, file_path: str, 
                             knowledge_types: List[str], file_category: str = 'case') -> bool:
    """
    添加文件并设置权限的便捷函数
    
    Args:
        file_id: 文件ID
        user_id: 用户ID
        title: 文件标题
        file_path: 文件路径
        knowledge_types: 权限类型列表
        file_category: 文件分类
    
    Returns:
        bool: 是否成功
    """
    pm = get_permission_manager()
    
    # 添加文件
    if not pm.add_file(file_id, user_id, title, file_path, file_category):
        return False
    
    # 设置权限
    return pm.set_file_permissions(file_id, knowledge_types, user_id)

def get_user_accessible_files(user_id: int) -> List[int]:
    """
    获取用户可访问的文件ID列表的便捷函数
    
    Args:
        user_id: 用户ID
    
    Returns:
        List[int]: 文件ID列表
    """
    pm = get_permission_manager()
    return pm.get_user_accessible_file_ids(user_id)

def get_user_private_files(user_id: int) -> List[int]:
    """
    【新增】获取用户私有文件ID列表的便捷函数
    
    Args:
        user_id: 用户ID
    
    Returns:
        List[int]: 用户私有文件ID列表
    """
    pm = get_permission_manager()
    return pm.get_user_private_file_ids(user_id)

def get_public_files() -> List[int]:
    """
    【新增】获取公共文件ID列表的便捷函数
    
    Returns:
        List[int]: 公共文件ID列表
    """
    pm = get_permission_manager()
    return pm.get_public_file_ids()

def remove_file_permission(file_id: int, permission_type: str, user_id: int) -> bool:
    """
    删除文件特定权限的便捷函数
    
    Args:
        file_id: 文件ID
        permission_type: 权限类型 ('public' 或 'private')
        user_id: 用户ID
    
    Returns:
        bool: 是否成功
    """
    pm = get_permission_manager()
    owner_id = None if permission_type == 'public' else user_id
    return pm.remove_permission(file_id, permission_type, owner_id)