#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具模块初始化文件
"""

from .minio_client import (
    init_minio,
    get_minio_client,
    upload_file,
    download_file as minio_download_file,
    delete_file as minio_delete_file,
    get_file_url,
    list_files,
    check_minio_health
)
from flask import current_app
import io

def download_file(minio_path):
    """下载文件的适配函数
    
    Args:
        minio_path: MinIO路径，格式为 bucket/object_name 或 object_name
        
    Returns:
        file_obj: 文件对象
    """
    try:
        # 检查路径格式并解析
        if '/' in minio_path and not minio_path.startswith('generals/') and not minio_path.startswith('cases/'):
            # 完整路径格式: bucket_name/object_name
            parts = minio_path.split('/', 1)
            bucket_name = parts[0]
            object_name = parts[1]
        else:
            # 只有object_name的格式，使用配置中的默认bucket
            bucket_name = current_app.config['MINIO_BUCKET_NAME']
            object_name = minio_path
        
        # 下载文件
        response = minio_download_file(bucket_name, object_name)
        
        # 将响应转换为BytesIO对象
        file_data = response.read()
        return io.BytesIO(file_data)
        
    except Exception as e:
        current_app.logger.error(f"文件下载失败: {str(e)}")
        return None

def delete_file_from_minio(minio_path):
    """删除MinIO文件的适配函数
    
    Args:
        minio_path: MinIO路径，格式为 bucket/object_name 或 object_name
        
    Returns:
        bool: 删除是否成功
    """
    try:
        # 检查路径格式并解析
        if '/' in minio_path and not minio_path.startswith('generals/') and not minio_path.startswith('cases/'):
            # 完整路径格式: bucket_name/object_name
            parts = minio_path.split('/', 1)
            bucket_name = parts[0]
            object_name = parts[1]
        else:
            # 只有object_name的格式，使用配置中的默认bucket
            bucket_name = current_app.config['MINIO_BUCKET_NAME']
            object_name = minio_path
        
        # 删除文件
        return minio_delete_file(bucket_name, object_name)
        
    except Exception as e:
        current_app.logger.error(f"文件删除失败: {str(e)}")
        return False