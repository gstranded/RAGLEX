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
from datetime import timedelta
import logging

# 全局MinIO客户端
minio_client = None

def init_minio(app):
    """初始化MinIO客户端"""
    global minio_client
    
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
    if not minio_client:
        raise Exception("MinIO客户端未初始化")
    
    try:
        # 生成唯一的文件名
        file_extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        object_name = f"{folder}/{unique_filename}"
        
        # 获取文件大小
        file_obj.seek(0, 2)  # 移动到文件末尾
        file_size = file_obj.tell()
        file_obj.seek(0)  # 重置到文件开头
        
        # 上传文件
        bucket_name = current_app.config['MINIO_BUCKET_NAME']
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
    if not minio_client:
        raise Exception("MinIO客户端未初始化")
    
    try:
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
    if not minio_client:
        raise Exception("MinIO客户端未初始化")
    
    try:
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
    if not minio_client:
        raise Exception("MinIO客户端未初始化")
    
    try:
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
    if not minio_client:
        raise Exception("MinIO客户端未初始化")
    
    try:
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
    if not minio_client:
        raise Exception("MinIO客户端未初始化")
    
    try:
        # 解析路径
        if '/' in minio_path:
            # 如果路径包含bucket名称
            parts = minio_path.split('/', 1)
            bucket_name = parts[0]
            object_name = parts[1]
        else:
            # 使用默认bucket
            bucket_name = current_app.config['MINIO_BUCKET_NAME']
            object_name = minio_path
        
        # 下载文件
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
    if not minio_client:
        return {
            'status': 'error',
            'message': 'MinIO客户端未初始化'
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