from flask import Blueprint, request, jsonify, send_file
from utils.minio_client import download_file_by_path
import io

file_download_bp = Blueprint('file_download', __name__)

@file_download_bp.route('/download', methods=['POST'])
def download_file():
    """接收远程服务器发送的MinIO路径，返回文件
    
    请求格式:
    {
        "minio_path": "bucket_name/object_name" 或 "object_name"
    }
    
    返回:
    - 成功: 直接返回文件流
    - 失败: 返回错误信息的JSON
    """
    try:
        # 获取请求数据
        data = request.get_json()
        if not data or 'minio_path' not in data:
            return jsonify({
                'error': '缺少minio_path参数',
                'code': 400
            }), 400
        
        minio_path = data['minio_path']
        if not minio_path:
            return jsonify({
                'error': 'minio_path不能为空',
                'code': 400
            }), 400
        
        # 调用下载函数
        result = download_file_by_path(minio_path)
        if result is None:
            return jsonify({
                'error': '文件下载失败或文件不存在',
                'code': 404
            }), 404
        
        file_data, filename, content_type = result
        
        # 创建文件流并返回
        file_stream = io.BytesIO(file_data)
        file_stream.seek(0)
        
        return send_file(
            file_stream,
            as_attachment=True,
            download_name=filename,
            mimetype=content_type
        )
        
    except Exception as e:
        return jsonify({
            'error': f'服务器内部错误: {str(e)}',
            'code': 500
        }), 500

@file_download_bp.route('/info', methods=['POST'])
def get_file_info():
    """获取文件信息（不下载文件内容）
    
    请求格式:
    {
        "minio_path": "bucket_name/object_name" 或 "object_name"
    }
    
    返回:
    {
        "filename": "文件名",
        "content_type": "文件类型",
        "size": "文件大小（字节）",
        "exists": true/false
    }
    """
    try:
        # 获取请求数据
        data = request.get_json()
        if not data or 'minio_path' not in data:
            return jsonify({
                'error': '缺少minio_path参数',
                'code': 400
            }), 400
        
        minio_path = data['minio_path']
        if not minio_path:
            return jsonify({
                'error': 'minio_path不能为空',
                'code': 400
            }), 400
        
        # 调用下载函数获取文件信息
        result = download_file_by_path(minio_path)
        if result is None:
            return jsonify({
                'filename': None,
                'content_type': None,
                'size': 0,
                'exists': False
            })
        
        file_data, filename, content_type = result
        
        return jsonify({
            'filename': filename,
            'content_type': content_type,
            'size': len(file_data),
            'exists': True
        })
        
    except Exception as e:
        return jsonify({
            'error': f'服务器内部错误: {str(e)}',
            'code': 500
        }), 500