# -*- coding: utf-8 -*-
"""
文档管理模块
包含文件上传、下载、删除等功能
"""

from flask import Blueprint, request, jsonify, send_file, current_app, Response
import json
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename
from models import db, UserFile
from utils.auth import login_required, sanitize_input, log_user_activity
from utils.minio_client import upload_file, get_file_url
from utils import download_file, delete_file_from_minio
import requests

documents_bp = Blueprint('documents', __name__)

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@documents_bp.route('/upload', methods=['POST'])
@login_required
def upload_user_file(current_user):
    """用户文件上传接口"""
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '请选择要上传的文件'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '请选择要上传的文件'
            }), 400
        
        # 获取表单数据
        file_category = request.form.get('file_category', 'general')
        case_subject = request.form.get('case_subject', '')  # 案件主题
        case_notes = request.form.get('case_notes', '')     # 备注
        
        # 验证文件类型
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'message': '不支持的文件类型'
            }), 400
        
        # 生成MinIO存储路径
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        minio_path = f"{file_category}s/{datetime.now().strftime('%Y/%m')}/{unique_filename}"
        
        # 上传到MinIO
        upload_result = upload_file(file, file.filename, f"{file_category}s")
        
        if not upload_result['success']:
            return jsonify({
                'success': False,
                'message': upload_result['error']
            }), 500
        
        # 检查是否已存在相同文件名的文件
        existing_file = UserFile.query.filter_by(
            filename=file.filename,
            user_id=current_user.id
        ).first()
        
        if existing_file:
            return jsonify({
                'success': False,
                'message': f'文件 "{file.filename}" 已存在，请选择其他文件或重命名后上传'
            }), 400
        
        # 保存到数据库
        user_file = UserFile(
            filename=file.filename,
            file_category=file_category,
            case_title=case_subject if file_category == 'case' else None,  # 使用案件主题
            case_summary=case_notes if file_category == 'case' else None,   # 使用备注
            minio_path=upload_result['object_name'],
            user_id=current_user.id
        )
        
        db.session.add(user_file)
        db.session.commit()
        
        # 记录用户活动
        log_user_activity(current_user.id, 'upload_file', {
            'file_id': user_file.id,
            'filename': user_file.filename,
            'file_category': user_file.file_category
        })
        
        current_app.logger.info(f"用户 {current_user.username} 上传文件: {user_file.filename}")
        
        return jsonify({
            'success': True,
            'message': '文件上传成功',
            'data': user_file.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"文件上传错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '文件上传失败，请稍后重试'
        }), 500

@documents_bp.route('/batch-upload', methods=['POST'])
@login_required
def batch_upload_files(current_user):
    """批量文件上传接口"""
    try:
        # 检查是否有文件
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'message': '请选择要上传的文件'
            }), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({
                'success': False,
                'message': '请选择要上传的文件'
            }), 400
        
        # 获取表单数据
        file_category = request.form.get('file_category', 'general')
        case_subject = request.form.get('case_subject', '')  # 案件主题
        case_notes = request.form.get('case_notes', '')     # 备注
        
        successful_files = []
        failed_files = []
        
        for file in files:
            if file.filename == '':
                continue
                
            try:
                # 验证文件类型
                if not allowed_file(file.filename):
                    failed_files.append({
                        'filename': file.filename,
                        'error': '不支持的文件类型'
                    })
                    continue
                
                # 检查是否已存在相同文件名的文件
                existing_file = UserFile.query.filter_by(
                    filename=file.filename,
                    user_id=current_user.id
                ).first()
                
                if existing_file:
                    failed_files.append({
                        'filename': file.filename,
                        'error': '文件已存在'
                    })
                    continue
                
                # 上传到MinIO
                upload_result = upload_file(file, file.filename, f"{file_category}s")
                
                if not upload_result['success']:
                    failed_files.append({
                        'filename': file.filename,
                        'error': upload_result['error']
                    })
                    continue
                
                # 保存到数据库
                user_file = UserFile(
                    filename=file.filename,
                    file_category=file_category,
                    case_title=case_subject if file_category == 'case' else None,
                    case_summary=case_notes if file_category == 'case' else None,
                    minio_path=upload_result['object_name'],
                    user_id=current_user.id
                )
                
                db.session.add(user_file)
                db.session.flush()  # 获取ID但不提交
                
                # 记录用户活动
                log_user_activity(current_user.id, 'upload_file', {
                    'file_id': user_file.id,
                    'filename': user_file.filename,
                    'file_category': user_file.file_category
                })
                
                successful_files.append({
                    'filename': file.filename,
                    'file_id': user_file.id,
                    'data': user_file.to_dict()
                })
                
            except Exception as e:
                current_app.logger.error(f"单个文件上传错误 {file.filename}: {str(e)}")
                failed_files.append({
                    'filename': file.filename,
                    'error': '文件上传失败'
                })
        
        # 提交所有成功的文件
        if successful_files:
            db.session.commit()
            current_app.logger.info(f"用户 {current_user.username} 批量上传文件: {len(successful_files)}个成功, {len(failed_files)}个失败")
        else:
            db.session.rollback()
        
        return jsonify({
            'success': True,
            'message': f'批量上传完成: {len(successful_files)}个成功, {len(failed_files)}个失败',
            'data': {
                'successful_files': successful_files,
                'failed_files': failed_files,
                'total_count': len(files),
                'success_count': len(successful_files),
                'failed_count': len(failed_files)
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"批量文件上传错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '批量文件上传失败，请稍后重试'
        }), 500

@documents_bp.route('', methods=['GET'])
@login_required
def get_user_files(current_user):
    """获取用户文件列表"""
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)
        file_category = request.args.get('file_category')
        search = request.args.get('search', '').strip()
        
        # 构建查询
        query = UserFile.query.filter_by(user_id=current_user.id)
        
        if file_category:
            query = query.filter_by(file_category=file_category)
        
        if search:
            query = query.filter(
                db.or_(
                    UserFile.filename.contains(search),
                    UserFile.case_title.contains(search),
                    UserFile.case_summary.contains(search)
                )
            )
        
        # 分页查询
        pagination = query.order_by(UserFile.uploaded_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        files = [file.to_dict() for file in pagination.items]
        
        return jsonify({
            'success': True,
            'data': {
                'files': files,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_prev': pagination.has_prev,
                    'has_next': pagination.has_next
                }
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取文件列表错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '获取文件列表失败'
        }), 500

@documents_bp.route('/<int:file_id>/download', methods=['GET'])
@login_required
def download_user_file(current_user, file_id):
    """下载用户文件"""
    try:
        # 查找文件
        user_file = UserFile.query.filter_by(
            id=file_id, 
            user_id=current_user.id
        ).first_or_404()
        
        # 从MinIO下载文件
        file_data = download_file(user_file.minio_path)
        
        if not file_data:
            return jsonify({
                'success': False,
                'message': '查无此文件'
            }), 500
        
        # 记录用户活动
        log_user_activity(current_user.id, 'download_file', {
            'file_id': user_file.id,
            'filename': user_file.filename
        })
        
        return send_file(
            file_data,
            as_attachment=True,
            download_name=user_file.filename
        )
        
    except Exception as e:
        current_app.logger.error(f"下载文档错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '文件下载失败'
        }), 500

@documents_bp.route('/<int:file_id>', methods=['DELETE'])
@login_required
def delete_user_file(current_user, file_id):
    """删除用户文件"""
    try:
        # 查找文件
        user_file = UserFile.query.filter_by(
            id=file_id, 
            user_id=current_user.id
        ).first_or_404()
        
        # 检查文件是否已上传到知识库，如果是则先从远程服务器删除
        knowledge_types_to_delete = []
        if user_file.public_knowledge_uploaded:
            knowledge_types_to_delete.append('public')
        if user_file.private_knowledge_uploaded:
            knowledge_types_to_delete.append('private')
        
        # 如果文件已上传到知识库，先从远程服务器删除
        if knowledge_types_to_delete:
            try:
                payload = {
                    "user_id": current_user.id,
                    "username": current_user.username,
                    "file_path": user_file.minio_path,
                    "filename": user_file.filename,
                    "file_category": user_file.file_category,
                    "knowledge_types": knowledge_types_to_delete,
                    "file_id": user_file.id,
                    "action": "cancel"  # 标识这是取消操作
                }
                
                response = requests.post(
                    "http://192.168.240.3:10086/api/receive-knowledge",
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    current_app.logger.info(f"成功从远程服务器删除文件({knowledge_types_to_delete}): {user_file.filename}")
                else:
                    current_app.logger.warning(f"从远程服务器删除文件失败: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                current_app.logger.warning(f"发送删除请求到远程服务器时出错: {str(e)}")
                # 继续删除本地文件，即使远程删除失败
        
        # 从MinIO删除文件
        try:
            delete_file_from_minio(user_file.minio_path)
        except Exception as e:
            current_app.logger.warning(f"MinIO文件删除失败: {str(e)}")
            # 继续删除数据库记录，即使MinIO删除失败
        
        # 记录用户活动
        log_user_activity(current_user.id, 'delete_file', {
            'file_id': user_file.id,
            'filename': user_file.filename,
            'knowledge_types_deleted': knowledge_types_to_delete
        })
        
        # 从数据库删除记录
        db.session.delete(user_file)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '文件删除成功'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"文件删除错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '文件删除失败'
        }), 500

@documents_bp.route('/preview/<path:filename>', methods=['GET'])
@login_required
def preview_file(current_user, filename):
    """预览文件"""
    try:
        # 查找文件
        user_file = UserFile.query.filter_by(
            filename=filename,
            user_id=current_user.id
        ).first_or_404()
        
        # 从MinIO获取文件
        file_data = download_file(user_file.minio_path)
        
        if not file_data:
            return jsonify({
                'success': False,
                'message': '文件预览失败'
            }), 500
        
        # 获取文件类型
        from utils.minio_client import get_content_type
        content_type = get_content_type(user_file.filename)
        
        # 记录用户活动
        log_user_activity(current_user.id, 'preview_file', {
            'file_id': user_file.id,
            'filename': user_file.filename
        })
        
        return send_file(
            file_data,
            mimetype=content_type,
            as_attachment=False,
            download_name=user_file.filename
        )
        
    except Exception as e:
        current_app.logger.error(f"文件预览错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '文件预览失败'
        }), 500

@documents_bp.route('/<int:file_id>/upload-knowledge', methods=['POST'])
@login_required
def upload_to_knowledge(current_user, file_id):
    """上传文件到知识库"""
    try:
        # 获取请求数据
        data = request.get_json() or {}
        
        # 支持单个类型（向后兼容）和多个类型
        if 'knowledge_types' in data:
            knowledge_types = data.get('knowledge_types', [])
        elif 'knowledge_type' in data:
            knowledge_types = [data.get('knowledge_type')]
        else:
            knowledge_types = ['public']  # 默认为公有知识库
        
        # 验证knowledge_types参数
        if not knowledge_types or not isinstance(knowledge_types, list):
            return jsonify({
                'success': False,
                'message': '请提供有效的知识库类型列表'
            }), 400
            
        for knowledge_type in knowledge_types:
            if knowledge_type not in ['public', 'private']:
                return jsonify({
                    'success': False,
                    'message': f'无效的知识库类型: {knowledge_type}，必须是public或private'
                }), 400
        
        # 查找文件
        user_file = UserFile.query.filter_by(
            id=file_id, 
            user_id=current_user.id
        ).first_or_404()
        
        # 检查是否已经上传过，过滤掉已上传的类型
        types_to_upload = []
        for knowledge_type in knowledge_types:
            if knowledge_type == 'public' and user_file.public_knowledge_uploaded:
                continue
            if knowledge_type == 'private' and user_file.private_knowledge_uploaded:
                continue
            types_to_upload.append(knowledge_type)
        
        if not types_to_upload:
            return jsonify({
                'success': False,
                'message': '所选知识库类型均已上传'
            }), 400
        
        # 打印用户ID和文件路径（测试用）
        print(f"用户ID: {current_user.id}")
        print(f"用户名: {current_user.username}")
        print(f"文件路径: {user_file.minio_path}")
        print(f"文件名: {user_file.filename}")
        print(f"文件分类: {user_file.file_category}")
        print(f"知识库类型: {type(types_to_upload)}")
        
        # 发送到远程服务器（一次性发送所有知识库类型）
        upload_success = False
        error_message = ""
        
        try:
            payload = {
                "user_id": current_user.id,
                "username": current_user.username,
                "file_path": user_file.minio_path,
                "filename": user_file.filename,
                "file_category": user_file.file_category,
                "knowledge_types": types_to_upload,  # 发送所有类型
                "file_id": user_file.id,
                "action":"add"
            }
            
            response = requests.post(
                "http://192.168.240.3:10086/api/receive-knowledge",
                json=payload,
                timeout=20
            )
            
            if response.status_code == 200:
                print(f"成功发送到远程服务器({types_to_upload}): {response.json()}")
                upload_success = True
            else:
                print(f"发送到远程服务器失败: {response.status_code}")
                if response.status_code == 422:
                    error_message = "数据格式错误，请检查远程服务器配置"
                else:
                    error_message = f"远程服务器返回错误: {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            print(f"发送到远程服务器时出错: {str(e)}")
            error_message = f"网络连接错误: {str(e)}"
        
        # 只有在远程上传成功时才更新数据库状态
        if not upload_success:
            return jsonify({
                'success': False,
                'message': f'上传到知识库失败: {error_message}'
            }), 500
        
        # 更新上传状态（只有在远程上传成功后才执行）
        uploaded_types = []
        for knowledge_type in types_to_upload:
            if knowledge_type == 'public':
                user_file.public_knowledge_uploaded = True
                uploaded_types.append('公有知识库')
            elif knowledge_type == 'private':
                user_file.private_knowledge_uploaded = True
                uploaded_types.append('私有知识库')
        
        # 提交数据库更改
        try:
            db.session.commit()
        except Exception as db_error:
            db.session.rollback()
            current_app.logger.error(f"数据库更新失败: {str(db_error)}")
            return jsonify({
                'success': False,
                'message': '数据库更新失败，请联系管理员'
            }), 500
        
        # 记录用户活动
        log_user_activity(current_user.id, 'upload_to_knowledge', {
            'file_id': user_file.id,
            'filename': user_file.filename,
            'minio_path': user_file.minio_path,
            'knowledge_types': types_to_upload
        })
        
        knowledge_names = '和'.join(uploaded_types)
        current_app.logger.info(f"用户 {current_user.username} 上传文件到{knowledge_names}: {user_file.filename}")
        
        return jsonify({
            'success': True,
            'message': f'文件已成功上传到{knowledge_names}',
            'data': user_file.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"上传知识库错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '上传知识库失败，请稍后重试'
        }), 500


@documents_bp.route('/<int:file_id>/cancel-knowledge', methods=['POST'])
@login_required
def cancel_knowledge_upload(current_user, file_id):
    """取消知识库上传"""
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请提供有效的请求数据'
            }), 400
        
        knowledge_types = data.get('knowledge_types', [])
        
        # 验证knowledge_types参数
        if not knowledge_types or not isinstance(knowledge_types, list):
            return jsonify({
                'success': False,
                'message': '请提供有效的知识库类型列表'
            }), 400
            
        for knowledge_type in knowledge_types:
            if knowledge_type not in ['public', 'private']:
                return jsonify({
                    'success': False,
                    'message': f'无效的知识库类型: {knowledge_type}，必须是public或private'
                }), 400
        
        # 查找文件
        user_file = UserFile.query.filter_by(
            id=file_id, 
            user_id=current_user.id
        ).first_or_404()
        
        # 检查哪些类型需要取消（只能取消已上传的类型）
        types_to_cancel = []
        for knowledge_type in knowledge_types:
            if knowledge_type == 'public' and user_file.public_knowledge_uploaded:
                types_to_cancel.append(knowledge_type)
            elif knowledge_type == 'private' and user_file.private_knowledge_uploaded:
                types_to_cancel.append(knowledge_type)
        
        if not types_to_cancel:
            return jsonify({
                'success': False,
                'message': '所选知识库类型均未上传，无法取消'
            }), 400
        
        # 打印取消信息（测试用）
        print(f"用户ID: {current_user.id}")
        print(f"用户名: {current_user.username}")
        print(f"文件路径: {user_file.minio_path}")
        print(f"文件名: {user_file.filename}")
        print(f"取消知识库类型: {types_to_cancel}")
        
        # 发送取消请求到远程服务器
        cancel_success = False
        error_message = ""
        
        try:
            payload = {
                "user_id": current_user.id,
                "username": current_user.username,
                "file_path": user_file.minio_path,
                "filename": user_file.filename,
                "file_category": user_file.file_category,
                "knowledge_types": types_to_cancel,
                "file_id": user_file.id,
                "action": "cancel"  # 标识这是取消操作
            }
            
            response = requests.post(
                "http://192.168.240.3:10086/api/receive-knowledge",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"成功发送取消请求到远程服务器({types_to_cancel}): {response.json()}")
                cancel_success = True
            else:
                print(f"发送取消请求到远程服务器失败: {response.status_code}")
                if response.status_code == 422:
                    error_message = "数据格式错误，请检查远程服务器配置"
                elif response.status_code == 404:
                    error_message = "远程服务器不支持取消操作"
                else:
                    error_message = f"远程服务器返回错误: {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            print(f"发送取消请求到远程服务器时出错: {str(e)}")
            error_message = f"网络连接错误: {str(e)}"
        
        # 只有在远程取消成功时才更新数据库状态
        if not cancel_success:
            return jsonify({
                'success': False,
                'message': f'取消知识库上传失败: {error_message}'
            }), 500
        
        # 更新取消状态（只有在远程取消成功后才执行）
        cancelled_types = []
        for knowledge_type in types_to_cancel:
            if knowledge_type == 'public':
                user_file.public_knowledge_uploaded = False
                cancelled_types.append('公有知识库')
            elif knowledge_type == 'private':
                user_file.private_knowledge_uploaded = False
                cancelled_types.append('私有知识库')
        
        # 提交数据库更改
        try:
            db.session.commit()
        except Exception as db_error:
            db.session.rollback()
            current_app.logger.error(f"数据库更新失败: {str(db_error)}")
            return jsonify({
                'success': False,
                'message': '数据库更新失败，请联系管理员'
            }), 500
        
        # 记录用户活动
        log_user_activity(current_user.id, 'cancel_knowledge_upload', {
            'file_id': user_file.id,
            'filename': user_file.filename,
            'minio_path': user_file.minio_path,
            'knowledge_types': types_to_cancel
        })
        
        knowledge_names = '和'.join(cancelled_types)
        current_app.logger.info(f"用户 {current_user.username} 取消文件从{knowledge_names}的上传: {user_file.filename}")
        
        return jsonify({
            'success': True,
            'message': f'已成功取消文件从{knowledge_names}的上传',
            'data': user_file.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"取消知识库上传错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '取消知识库上传失败，请稍后重试'
        }), 500


@documents_bp.route('/batch-upload-knowledge', methods=['POST'])
@login_required
def batch_upload_to_knowledge(current_user):
    """批量上传文件到知识库"""
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请提供有效的请求数据'
            }), 400
        
        file_ids = data.get('file_ids', [])
        knowledge_types = data.get('knowledge_types', [])
        
        # 验证参数
        if not file_ids or not isinstance(file_ids, list):
            return jsonify({
                'success': False,
                'message': '请提供有效的文件ID列表'
            }), 400
            
        if not knowledge_types or not isinstance(knowledge_types, list):
            return jsonify({
                'success': False,
                'message': '请提供有效的知识库类型列表'
            }), 400
        
        # 验证知识库类型
        valid_types = ['public', 'private']
        for knowledge_type in knowledge_types:
            if knowledge_type not in valid_types:
                return jsonify({
                    'success': False,
                    'message': f'无效的知识库类型: {knowledge_type}'
                }), 400
        
        # 批量处理结果
        results = {
            'success_files': [],
            'failed_files': [],
            'total_count': len(file_ids),
            'success_count': 0,
            'failed_count': 0
        }
        
        # 逐个处理文件
        for file_id in file_ids:
            try:
                # 查找文件
                user_file = UserFile.query.filter_by(
                    id=file_id,
                    user_id=current_user.id
                ).first()
                
                if not user_file:
                    results['failed_files'].append({
                        'file_id': file_id,
                        'error': '文件不存在或无权限访问'
                    })
                    results['failed_count'] += 1
                    continue
                
                # 检查文件是否已上传到指定知识库
                types_to_upload = []
                already_uploaded = []
                
                for knowledge_type in knowledge_types:
                    if knowledge_type == 'public' and not user_file.public_knowledge_uploaded:
                        types_to_upload.append('public')
                    elif knowledge_type == 'private' and not user_file.private_knowledge_uploaded:
                        types_to_upload.append('private')
                    else:
                        type_name = '公有知识库' if knowledge_type == 'public' else '私有知识库'
                        already_uploaded.append(type_name)
                
                if not types_to_upload:
                    uploaded_names = '和'.join(already_uploaded)
                    results['failed_files'].append({
                        'file_id': file_id,
                        'filename': user_file.filename,
                        'error': f'文件已上传到{uploaded_names}'
                    })
                    results['failed_count'] += 1
                    continue
                
                # 构建发送到远程服务器的数据
                payload = {
                    'user_id': current_user.id,
                    'username': current_user.username,
                    'file_path': user_file.minio_path,
                    'filename': user_file.filename,
                    'file_category': user_file.file_category,
                    'knowledge_types': types_to_upload,
                    'file_id': user_file.id,
                    'action': 'add'
                }
                
                # 发送到远程服务器
                upload_success = False
                error_message = ""
                
                try:
                    response = requests.post(
                        'http://192.168.240.3:10086/api/receive-knowledge',
                        json=payload,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        upload_success = True
                    else:
                        if response.status_code == 422:
                            error_message = "数据格式错误"
                        else:
                            error_message = f"远程服务器错误: {response.status_code}"
                        
                except requests.exceptions.RequestException as e:
                    error_message = f"网络连接错误: {str(e)}"
                
                # 处理上传结果
                if upload_success:
                    # 更新数据库状态
                    uploaded_types = []
                    for knowledge_type in types_to_upload:
                        if knowledge_type == 'public':
                            user_file.public_knowledge_uploaded = True
                            uploaded_types.append('公有知识库')
                        elif knowledge_type == 'private':
                            user_file.private_knowledge_uploaded = True
                            uploaded_types.append('私有知识库')
                    
                    # 记录用户活动
                    log_user_activity(current_user.id, 'batch_upload_to_knowledge', {
                        'file_id': user_file.id,
                        'filename': user_file.filename,
                        'minio_path': user_file.minio_path,
                        'knowledge_types': types_to_upload
                    })
                    
                    knowledge_names = '和'.join(uploaded_types)
                    results['success_files'].append({
                        'file_id': file_id,
                        'filename': user_file.filename,
                        'message': f'已成功上传到{knowledge_names}'
                    })
                    results['success_count'] += 1
                    
                else:
                    results['failed_files'].append({
                        'file_id': file_id,
                        'filename': user_file.filename,
                        'error': f'上传失败: {error_message}'
                    })
                    results['failed_count'] += 1
                    
            except Exception as file_error:
                current_app.logger.error(f"处理文件 {file_id} 时出错: {str(file_error)}")
                results['failed_files'].append({
                    'file_id': file_id,
                    'error': f'处理文件时出错: {str(file_error)}'
                })
                results['failed_count'] += 1
        
        # 提交数据库更改
        try:
            db.session.commit()
        except Exception as db_error:
            db.session.rollback()
            current_app.logger.error(f"批量上传数据库更新失败: {str(db_error)}")
            return jsonify({
                'success': False,
                'message': '数据库更新失败，请联系管理员'
            }), 500
        
        # 构建响应消息
        if results['success_count'] > 0 and results['failed_count'] == 0:
            message = f'批量上传成功，共处理 {results["success_count"]} 个文件'
            success = True
        elif results['success_count'] > 0 and results['failed_count'] > 0:
            message = f'部分上传成功，成功 {results["success_count"]} 个，失败 {results["failed_count"]} 个'
            success = True
        else:
            message = f'批量上传失败，共 {results["failed_count"]} 个文件上传失败'
            success = False
        
        current_app.logger.info(f"用户 {current_user.username} 批量上传文件到知识库: {message}")
        
        return jsonify({
            'success': success,
            'message': message,
            'data': results
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"批量上传知识库错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '批量上传知识库失败，请稍后重试'
        }), 500

@documents_bp.route('/<int:file_id>', methods=['PUT'])
@login_required
def update_file_info(current_user, file_id):
    """更新文件信息"""
    try:
        # 获取文件记录
        user_file = UserFile.query.filter_by(
            id=file_id,
            user_id=current_user.id
        ).first()
        
        if not user_file:
            return jsonify({
                'success': False,
                'message': '文件不存在或无权限访问'
            }), 404
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请提供更新数据'
            }), 400
        
        # 清理输入数据
        data = sanitize_input(data)
        
        # 更新允许的字段
        if 'file_category' in data:
            user_file.file_category = data['file_category']
        
        if 'case_title' in data:
            user_file.case_title = data['case_title'] if data['case_title'] else None
        
        if 'case_summary' in data:
            user_file.case_summary = data['case_summary'] if data['case_summary'] else None
        
        # 保存更改
        db.session.commit()
        
        # 记录用户活动
        log_user_activity(current_user.id, 'update_file', {
            'file_id': user_file.id,
            'filename': user_file.filename,
            'updated_fields': list(data.keys())
        })
        
        current_app.logger.info(f"用户 {current_user.username} 更新文件信息: {user_file.filename}")
        
        return jsonify({
            'success': True,
            'message': '文件信息更新成功',
            'data': user_file.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新文件信息错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '更新文件信息失败，请稍后重试'
        }), 500


@documents_bp.route('/batch-upload-knowledge-progress', methods=['POST'])
@login_required
def batch_upload_to_knowledge_with_progress(current_user):
    """批量上传文件到知识库（带实时进度反馈）"""
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请提供有效的请求数据'
            }), 400
        
        file_ids = data.get('file_ids', [])
        knowledge_types = data.get('knowledge_types', [])
        
        # 验证参数
        if not file_ids or not isinstance(file_ids, list):
            return jsonify({
                'success': False,
                'message': '请提供有效的文件ID列表'
            }), 400
            
        if not knowledge_types or not isinstance(knowledge_types, list):
            return jsonify({
                'success': False,
                'message': '请提供有效的知识库类型列表'
            }), 400
        
        # 验证知识库类型
        valid_types = ['public', 'private']
        for knowledge_type in knowledge_types:
            if knowledge_type not in valid_types:
                return jsonify({
                    'success': False,
                    'message': f'无效的知识库类型: {knowledge_type}'
                }), 400
        
        # 获取当前应用实例（在生成器外部获取）
        app = current_app._get_current_object()
        
        def generate_progress():
            """生成器函数，用于实时返回进度"""
            
            # 批量处理结果
            results = {
                'success_files': [],
                'failed_files': [],
                'total_count': len(file_ids),
                'success_count': 0,
                'failed_count': 0
            }
            
            # 发送初始进度
            yield f"data: {json.dumps({'type': 'progress', 'completed': 0, 'total': len(file_ids), 'currentFile': '', 'errors': []})}\n\n"
            
            # 在应用上下文中处理文件
            with app.app_context():
                # 逐个处理文件
                for index, file_id in enumerate(file_ids):
                    try:
                        # 查找文件
                        user_file = UserFile.query.filter_by(
                            id=file_id,
                            user_id=current_user.id
                        ).first()
                        
                        if not user_file:
                            error_info = {
                                'file_id': file_id,
                                'filename': f'文件ID: {file_id}',
                                'error': '文件不存在或无权限访问'
                            }
                            results['failed_files'].append(error_info)
                            results['failed_count'] += 1
                            
                            # 发送进度更新
                            yield f"data: {json.dumps({'type': 'progress', 'completed': index + 1, 'total': len(file_ids), 'currentFile': '', 'errors': [error_info]})}\n\n"
                            continue
                        
                        # 发送当前处理文件信息
                        yield f"data: {json.dumps({'type': 'progress', 'completed': index, 'total': len(file_ids), 'currentFile': user_file.filename, 'errors': []})}\n\n"
                        
                        # 检查文件是否已上传到指定知识库
                        types_to_upload = []
                        already_uploaded = []
                        
                        for knowledge_type in knowledge_types:
                            if knowledge_type == 'public':
                                if user_file.public_knowledge_uploaded:
                                    already_uploaded.append('公有知识库')
                                else:
                                    types_to_upload.append('public')
                            elif knowledge_type == 'private':
                                if user_file.private_knowledge_uploaded:
                                    already_uploaded.append('私有知识库')
                                else:
                                    types_to_upload.append('private')
                        
                        # 如果有任何知识库已上传，显示警告但继续处理未上传的部分
                        if already_uploaded:
                            # 构建精确的警告信息
                            uploaded_names = '和'.join(already_uploaded)
                            warning_message = f'{uploaded_names}已经上传'
                            
                            error_info = {
                                'file_id': file_id,
                                'filename': user_file.filename,
                                'error': warning_message,
                                'type': 'warning'  # 标记为警告类型
                            }
                            results['failed_files'].append(error_info)
                            results['failed_count'] += 1
                            
                            # 发送进度更新
                            yield f"data: {json.dumps({'type': 'progress', 'completed': index + 1, 'total': len(file_ids), 'currentFile': '', 'errors': [error_info]})}\n\n"
                            
                            # 如果没有需要上传的类型，跳过
                            if not types_to_upload:
                                continue
                        
                        # 构建发送到远程服务器的数据
                        payload = {
                            'user_id': current_user.id,
                            'username': current_user.username,
                            'file_path': user_file.minio_path,
                            'filename': user_file.filename,
                            'file_category': user_file.file_category,
                            'knowledge_types': types_to_upload,
                            'file_id': user_file.id,
                            'action': 'add'
                        }
                        
                        # 发送到远程服务器
                        upload_success = False
                        error_message = ""
                        
                        try:
                            response = requests.post(
                                'http://192.168.240.3:10086/api/receive-knowledge',
                                json=payload,
                                timeout=30
                            )
                            
                            if response.status_code == 200:
                                upload_success = True
                            else:
                                if response.status_code == 422:
                                    error_message = "数据格式错误"
                                else:
                                    error_message = f"远程服务器错误: {response.status_code}"
                                
                        except requests.exceptions.RequestException as e:
                            error_message = f"网络连接错误: {str(e)}"
                        
                        # 处理上传结果
                        if upload_success:
                            # 更新数据库状态
                            uploaded_types = []
                            for knowledge_type in types_to_upload:
                                if knowledge_type == 'public':
                                    user_file.public_knowledge_uploaded = True
                                    uploaded_types.append('公有知识库')
                                elif knowledge_type == 'private':
                                    user_file.private_knowledge_uploaded = True
                                    uploaded_types.append('私有知识库')
                            
                            # 记录用户活动
                            log_user_activity(current_user.id, 'batch_upload_to_knowledge', {
                                'file_id': user_file.id,
                                'filename': user_file.filename,
                                'minio_path': user_file.minio_path,
                                'knowledge_types': types_to_upload
                            })
                            
                            knowledge_names = '和'.join(uploaded_types)
                            results['success_files'].append({
                                'file_id': file_id,
                                'filename': user_file.filename,
                                'message': f'已成功上传到{knowledge_names}'
                            })
                            results['success_count'] += 1
                            
                            # 发送成功进度更新
                            yield f"data: {json.dumps({'type': 'progress', 'completed': index + 1, 'total': len(file_ids), 'currentFile': '', 'errors': []})}\n\n"
                            
                        else:
                            # 构建具体的失败知识库类型信息
                            failed_types = []
                            for knowledge_type in types_to_upload:
                                if knowledge_type == 'public':
                                    failed_types.append('公有知识库')
                                elif knowledge_type == 'private':
                                    failed_types.append('私有知识库')
                            
                            failed_type_text = '和'.join(failed_types)
                            error_info = {
                                'file_id': file_id,
                                'filename': user_file.filename,
                                'error': f'上传到{failed_type_text}失败: {error_message}'
                            }
                            results['failed_files'].append(error_info)
                            results['failed_count'] += 1
                            
                            # 发送失败进度更新
                            yield f"data: {json.dumps({'type': 'progress', 'completed': index + 1, 'total': len(file_ids), 'currentFile': '', 'errors': [error_info]})}\n\n"
                            
                    except Exception as file_error:
                        app.logger.error(f"处理文件 {file_id} 时出错: {str(file_error)}")
                        error_info = {
                            'file_id': file_id,
                            'filename': f'文件ID: {file_id}',
                            'error': f'处理失败: {str(file_error)}'
                        }
                        results['failed_files'].append(error_info)
                        results['failed_count'] += 1
                        
                        # 发送错误进度更新
                        yield f"data: {json.dumps({'type': 'progress', 'completed': index + 1, 'total': len(file_ids), 'currentFile': '', 'errors': [error_info]})}\n\n"
                        
                        # 回滚数据库事务
                        db.session.rollback()
            
                # 提交数据库更改
                try:
                    db.session.commit()
                except Exception as db_error:
                    db.session.rollback()
                    app.logger.error(f"批量上传数据库更新失败: {str(db_error)}")
                    yield f"data: {json.dumps({'type': 'error', 'message': '数据库更新失败，请联系管理员'})}\n\n"
                    return
                
                # 构建最终结果
                if results['success_count'] > 0 and results['failed_count'] == 0:
                    message = f'批量上传成功，共处理 {results["success_count"]} 个文件'
                    success = True
                elif results['success_count'] > 0 and results['failed_count'] > 0:
                    message = f'部分上传成功，成功 {results["success_count"]} 个，失败 {results["failed_count"]} 个'
                    success = True
                else:
                    message = f'批量上传失败，共 {results["failed_count"]} 个文件上传失败'
                    success = False
                
                app.logger.info(f"用户 {current_user.username} 批量上传文件到知识库: {message}")
                
                # 发送最终结果
                yield f"data: {json.dumps({'type': 'complete', 'success': success, 'message': message, 'data': results})}\n\n"
        
        return Response(generate_progress(), mimetype='text/plain')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"批量上传知识库错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '批量上传知识库失败，请稍后重试'
        }), 500