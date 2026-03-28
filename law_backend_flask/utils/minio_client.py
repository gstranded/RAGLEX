#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MinIO客户端工具
用于处理文件上传、下载和管理
"""

from minio import Minio
from minio.error import S3Error
from flask import current_app
import uuid
import os
import io
from datetime import timedelta
import logging

# 全局MinIO客户端
minio_client = None


def is_minio_disabled() -> bool:
    """Return True when MinIO integration should be skipped (local/dev without MinIO)."""
    return str(os.environ.get('MINIO_DISABLED') or '').strip().lower() in {
        '1', 'true', 'yes', 'y', 'on'
    }


def use_local_storage() -> bool:
    """MinIO 不可用时自动退化到本地文件存储。"""
    return is_minio_disabled() or minio_client is None


def get_local_storage_root() -> str:
    base_dir = current_app.config.get('DATA_FOLDER') or current_app.config.get('UPLOAD_FOLDER') or os.getcwd()
    storage_root = os.path.join(base_dir, 'local_object_store')
    os.makedirs(storage_root, exist_ok=True)
    return storage_root


def get_local_object_path(bucket_name: str, object_name: str) -> str:
    bucket_dir = os.path.abspath(os.path.join(get_local_storage_root(), bucket_name))
    os.makedirs(bucket_dir, exist_ok=True)

    safe_object_name = (object_name or '').lstrip('/').replace('\\', '/')
    candidate = os.path.abspath(os.path.normpath(os.path.join(bucket_dir, safe_object_name)))
    if not candidate.startswith(bucket_dir + os.sep) and candidate != bucket_dir:
        raise ValueError('非法对象路径')
    return candidate


def init_minio(app):
    """初始化MinIO客户端"""
    global minio_client

    if is_minio_disabled():
        app.logger.info("MinIO disabled via MINIO_DISABLED=true; skipping MinIO init")
        minio_client = None
        return

    try:
        minio_client = Minio(
            app.config['MINIO_ENDPOINT'],
            access_key=app.config['MINIO_ACCESS_KEY'],
            secret_key=app.config['MINIO_SECRET_KEY'],
            secure=app.config['MINIO_SECURE']
        )
        
        # 检查并创建bucket
        bucket_name = app.config['MINIO_BUCKET_NAME']
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            app.logger.info(f"创建MinIO bucket: {bucket_name}")
        
        app.logger.info("MinIO客户端初始化成功")
        
    except Exception as e:
        app.logger.error(f"MinIO客户端初始化失败: {str(e)}")
        minio_client = None

def get_minio_client():
    """获取MinIO客户端"""
    return minio_client

def upload_file(file_obj, original_filename, folder='documents'):
    """上传文件到MinIO
    
    Args:
        file_obj: 文件对象
        original_filename: 原始文件名
        folder: 存储文件夹
        
    Returns:
        dict: 包含上传结果的字典
    """
    try:
        # 生成唯一的文件名
        file_extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        object_name = f"{folder}/{unique_filename}"
        
        # 获取文件大小
        file_obj.seek(0, 2)  # 移动到文件末尾
        file_size = file_obj.tell()
        file_obj.seek(0)  # 重置到文件开头
        
        bucket_name = current_app.config['MINIO_BUCKET_NAME']
        if use_local_storage():
            local_path = get_local_object_path(bucket_name, object_name)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb') as local_file:
                local_file.write(file_obj.read())
            file_obj.seek(0)

            return {
                'success': True,
                'bucket': bucket_name,
                'object_name': object_name,
                'filename': unique_filename,
                'original_filename': original_filename,
                'file_size': file_size,
                'etag': None,
                'storage': 'local'
            }

        result = minio_client.put_object(
            bucket_name,
            object_name,
            file_obj,
            file_size,
            content_type=get_content_type(original_filename)
        )
        
        return {
            'success': True,
            'bucket': bucket_name,
            'object_name': object_name,
            'filename': unique_filename,
            'original_filename': original_filename,
            'file_size': file_size,
            'etag': result.etag
        }
        
    except S3Error as e:
        current_app.logger.error(f"MinIO上传错误: {str(e)}")
        return {
            'success': False,
            'error': f"文件上传失败: {str(e)}"
        }
    except Exception as e:
        current_app.logger.error(f"文件上传异常: {str(e)}")
        return {
            'success': False,
            'error': f"文件上传异常: {str(e)}"
        }

def download_file(bucket_name, object_name):
    """从MinIO下载文件
    
    Args:
        bucket_name: bucket名称
        object_name: 对象名称
        
    Returns:
        file_obj: 文件对象
    """
    try:
        if use_local_storage():
            local_path = get_local_object_path(bucket_name, object_name)
            if not os.path.exists(local_path):
                raise FileNotFoundError(f'文件不存在: {object_name}')
            with open(local_path, 'rb') as local_file:
                return io.BytesIO(local_file.read())

        response = minio_client.get_object(bucket_name, object_name)
        return response
    except S3Error as e:
        current_app.logger.error(f"MinIO下载错误: {str(e)}")
        raise Exception(f"文件下载失败: {str(e)}")
    except Exception as e:
        current_app.logger.error(f"文件下载异常: {str(e)}")
        raise Exception(f"文件下载异常: {str(e)}")

def delete_file(bucket_name, object_name):
    """从MinIO删除文件
    
    Args:
        bucket_name: bucket名称
        object_name: 对象名称
        
    Returns:
        bool: 删除是否成功
    """
    try:
        if use_local_storage():
            local_path = get_local_object_path(bucket_name, object_name)
            if os.path.exists(local_path):
                os.remove(local_path)
            return True

        minio_client.remove_object(bucket_name, object_name)
        return True
    except S3Error as e:
        current_app.logger.error(f"MinIO删除错误: {str(e)}")
        return False
    except Exception as e:
        current_app.logger.error(f"文件删除异常: {str(e)}")
        return False

def get_file_url(bucket_name, object_name, expires=timedelta(hours=1)):
    """获取文件的预签名URL
    
    Args:
        bucket_name: bucket名称
        object_name: 对象名称
        expires: 过期时间
        
    Returns:
        str: 预签名URL
    """
    try:
        if use_local_storage():
            return f"local://{bucket_name}/{object_name}"

        url = minio_client.presigned_get_object(
            bucket_name,
            object_name,
            expires=expires
        )
        return url
    except S3Error as e:
        current_app.logger.error(f"MinIO URL生成错误: {str(e)}")
        raise Exception(f"URL生成失败: {str(e)}")
    except Exception as e:
        current_app.logger.error(f"URL生成异常: {str(e)}")
        raise Exception(f"URL生成异常: {str(e)}")

def list_files(bucket_name, prefix='', recursive=True):
    """列出MinIO中的文件
    
    Args:
        bucket_name: bucket名称
        prefix: 前缀过滤
        recursive: 是否递归
        
    Returns:
        list: 文件列表
    """
    try:
        if use_local_storage():
            bucket_dir = get_local_object_path(bucket_name, '')
            files = []
            for root, _, filenames in os.walk(bucket_dir):
                for filename in filenames:
                    full_path = os.path.join(root, filename)
                    object_name = os.path.relpath(full_path, bucket_dir).replace('\\', '/')
                    if prefix and not object_name.startswith(prefix):
                        continue
                    files.append({
                        'object_name': object_name,
                        'size': os.path.getsize(full_path),
                        'last_modified': None,
                        'etag': None
                    })
            return files

        objects = minio_client.list_objects(
            bucket_name,
            prefix=prefix,
            recursive=recursive
        )
        
        files = []
        for obj in objects:
            files.append({
                'object_name': obj.object_name,
                'size': obj.size,
                'last_modified': obj.last_modified.isoformat() if obj.last_modified else None,
                'etag': obj.etag
            })
        
        return files
    except S3Error as e:
        current_app.logger.error(f"MinIO列表错误: {str(e)}")
        return []
    except Exception as e:
        current_app.logger.error(f"文件列表异常: {str(e)}")
        return []

def get_content_type(filename):
    """根据文件名获取Content-Type
    
    Args:
        filename: 文件名
        
    Returns:
        str: Content-Type
    """
    extension = os.path.splitext(filename)[1].lower()
    
    content_types = {
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.txt': 'text/plain',
        '.json': 'application/json',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif'
    }
    
    return content_types.get(extension, 'application/octet-stream')

def download_file_by_path(minio_path):
    """根据MinIO路径下载文件并返回给远程服务器
    
    Args:
        minio_path: MinIO文件路径 (格式: bucket_name/object_name 或 object_name)
        
    Returns:
        tuple: (file_data, filename, content_type) 或 None
    """
    try:
        # 解析路径
        if '/' in minio_path and not minio_path.startswith('generals/') and not minio_path.startswith('cases/'):
            # 完整路径格式: bucket_name/object_name
            parts = minio_path.split('/', 1)
            bucket_name = parts[0]
            object_name = parts[1]
        else:
            # 使用默认bucket
            bucket_name = current_app.config['MINIO_BUCKET_NAME']
            object_name = minio_path
        
        if use_local_storage():
            local_path = get_local_object_path(bucket_name, object_name)
            if not os.path.exists(local_path):
                return None
            with open(local_path, 'rb') as local_file:
                file_data = local_file.read()
        else:
            response = minio_client.get_object(bucket_name, object_name)
            file_data = response.read()
        
        # 获取文件名和内容类型
        filename = os.path.basename(object_name)
        content_type = get_content_type(filename)
        
        return file_data, filename, content_type
        
    except S3Error as e:
        current_app.logger.error(f"MinIO下载错误: {str(e)}")
        return None
    except Exception as e:
        current_app.logger.error(f"文件下载异常: {str(e)}")
        return None
    finally:
        # 确保响应流被关闭
        if 'response' in locals():
            response.close()

def check_minio_health():
    """检查MinIO连接健康状态

    Returns:
        dict: 健康状态信息
    """
    if is_minio_disabled():
        return {
            'status': 'disabled',
            'message': 'MinIO disabled via MINIO_DISABLED=true'
        }

    if not minio_client:
        return {
            'status': 'local',
            'message': 'MinIO不可用，当前使用本地文件存储兜底'
        }

    try:
        # 尝试列出buckets来测试连接
        buckets = minio_client.list_buckets()
        return {
            'status': 'healthy',
            'message': 'MinIO连接正常',
            'buckets': [bucket.name for bucket in buckets]
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'MinIO连接失败: {str(e)}'
        }
