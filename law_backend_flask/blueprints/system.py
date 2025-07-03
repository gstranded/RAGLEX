# -*- coding: utf-8 -*-
"""
系统配置模块
包含系统配置管理、统计信息、健康检查等功能
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from sqlalchemy import func
from models import db, User,  UserFile, SystemConfig
from utils.auth import login_required, admin_required, sanitize_input, log_user_activity

system_bp = Blueprint('system', __name__)

@system_bp.route('/config', methods=['GET'])
@login_required
def get_system_config(current_user):
    """获取系统配置"""
    try:
        # 获取所有系统配置
        configs = SystemConfig.query.all()
        
        config_dict = {}
        for config in configs:
            # 敏感配置只有管理员可以查看
            if config.is_sensitive and current_user.role != 'admin':
                continue
            
            config_dict[config.key] = {
                'value': config.value,
                'description': config.description,
                'is_sensitive': config.is_sensitive,
                'updated_at': config.updated_at.isoformat() if config.updated_at else None
            }
        
        return jsonify({
            'success': True,
            'data': config_dict
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取系统配置错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '获取系统配置失败'
        }), 500

@system_bp.route('/config', methods=['PUT'])
@admin_required
def update_system_config(current_user):
    """更新系统配置（仅管理员）"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': '请提供配置数据'
            }), 400
        
        updated_configs = []
        
        for key, value in data.items():
            # 查找现有配置
            config = SystemConfig.query.filter_by(key=key).first()
            
            if config:
                # 更新现有配置
                config.value = sanitize_input(str(value))
                config.updated_at = datetime.utcnow()
                config.updated_by = current_user.id
            else:
                # 创建新配置
                config = SystemConfig(
                    key=key,
                    value=sanitize_input(str(value)),
                    description=f"配置项: {key}",
                    is_sensitive=False,
                    created_by=current_user.id,
                    updated_by=current_user.id
                )
                db.session.add(config)
            
            updated_configs.append(key)
        
        db.session.commit()
        
        # 记录用户活动
        log_user_activity(current_user.id, 'update_system_config', {
            'updated_configs': updated_configs
        })
        
        current_app.logger.info(f"管理员 {current_user.username} 更新系统配置: {', '.join(updated_configs)}")
        
        return jsonify({
            'success': True,
            'message': '系统配置更新成功',
            'data': {
                'updated_configs': updated_configs
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新系统配置错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '系统配置更新失败'
        }), 500

@system_bp.route('/stats', methods=['GET'])
@admin_required
def get_system_stats(current_user):
    """获取系统统计信息（仅管理员）"""
    try:
        # 获取统计时间范围
        days = request.args.get('days', 30, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 用户统计
        total_users = User.query.count()
        new_users = User.query.filter(User.created_at >= start_date).count()
        active_users = User.query.filter(User.last_login >= start_date).count()
        

        
        # 文件统计
        total_files = UserFile.query.count()
        new_files = UserFile.query.filter(UserFile.uploaded_at >= start_date).count()
        
        # 按类型统计文件
        file_stats_by_category = db.session.query(
            UserFile.file_category,
            func.count(UserFile.id).label('count')
        ).group_by(UserFile.file_category).all()
        
        file_category_dict = {category: count for category, count in file_stats_by_category}
        
        # 查询统计已移除（知识库在外部服务器）
        total_queries = 0
        new_queries = 0
        daily_queries = []
        
        # 系统资源统计（简化版本）
        import psutil
        
        system_info = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent
        }
        
        stats = {
            'users': {
                'total': total_users,
                'new': new_users,
                'active': active_users
            },

            'files': {
                'total': total_files,
                'new': new_files,
                'by_category': file_category_dict
            },
            'queries': {
                'total': total_queries,
                'new': new_queries,
                'daily': daily_queries
            },
            'system': system_info,
            'period': {
                'days': days,
                'start_date': start_date.isoformat(),
                'end_date': datetime.utcnow().isoformat()
            }
        }
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取系统统计错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '获取系统统计失败'
        }), 500

@system_bp.route('/health', methods=['GET'])
def health_check():
    """系统健康检查"""
    try:
        # 检查数据库连接
        db.session.execute('SELECT 1')
        db_status = 'healthy'
    except Exception as e:
        current_app.logger.error(f"数据库健康检查失败: {str(e)}")
        db_status = 'unhealthy'
    
    # 检查MinIO连接
    try:
        from utils.minio_client import check_minio_health
        minio_status = 'healthy' if check_minio_health() else 'unhealthy'
    except Exception as e:
        current_app.logger.error(f"MinIO健康检查失败: {str(e)}")
        minio_status = 'unhealthy'
    
    # 系统状态
    overall_status = 'healthy' if db_status == 'healthy' and minio_status == 'healthy' else 'unhealthy'
    
    health_info = {
        'status': overall_status,
        'timestamp': datetime.utcnow().isoformat(),
        'services': {
            'database': db_status,
            'minio': minio_status
        },
        'version': current_app.config.get('APP_VERSION', '1.0.0')
    }
    
    status_code = 200 if overall_status == 'healthy' else 503
    
    return jsonify(health_info), status_code

@system_bp.route('/logs', methods=['GET'])
@admin_required
def get_system_logs(current_user):
    """获取系统日志（仅管理员）"""
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        level = request.args.get('level', '').upper()
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # 这里应该从日志文件或日志系统中读取日志
        # 为了演示，返回模拟数据
        logs = [
            {
                'timestamp': datetime.utcnow().isoformat(),
                'level': 'INFO',
                'message': '系统启动成功',
                'module': 'app'
            },
            {
                'timestamp': (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
                'level': 'WARNING',
                'message': 'MinIO连接超时，正在重试',
                'module': 'minio_client'
            },
            {
                'timestamp': (datetime.utcnow() - timedelta(minutes=10)).isoformat(),
                'level': 'ERROR',
                'message': '用户认证失败',
                'module': 'auth'
            }
        ]
        
        # 根据级别过滤
        if level and level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            logs = [log for log in logs if log['level'] == level]
        
        # 分页处理（简化版本）
        total = len(logs)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_logs = logs[start:end]
        
        return jsonify({
            'success': True,
            'data': {
                'logs': paginated_logs,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取系统日志错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '获取系统日志失败'
        }), 500

@system_bp.route('/backup', methods=['POST'])
@admin_required
def create_backup(current_user):
    """创建系统备份（仅管理员）"""
    try:
        # 获取备份类型
        backup_type = request.json.get('type', 'full') if request.json else 'full'
        
        if backup_type not in ['full', 'database', 'files']:
            return jsonify({
                'success': False,
                'message': '无效的备份类型'
            }), 400
        
        # 生成备份文件名
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"backup_{backup_type}_{timestamp}"
        
        # 这里应该实现实际的备份逻辑
        # 为了演示，只是模拟备份过程
        
        # 记录用户活动
        log_user_activity(current_user.id, 'create_backup', {
            'backup_type': backup_type,
            'backup_filename': backup_filename
        })
        
        current_app.logger.info(f"管理员 {current_user.username} 创建系统备份: {backup_filename}")
        
        return jsonify({
            'success': True,
            'message': '备份创建成功',
            'data': {
                'backup_filename': backup_filename,
                'backup_type': backup_type,
                'created_at': datetime.utcnow().isoformat()
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"创建备份错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '备份创建失败'
        }), 500

@system_bp.route('/maintenance', methods=['POST'])
@admin_required
def toggle_maintenance_mode(current_user):
    """切换维护模式（仅管理员）"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False) if data else False
        message = data.get('message', '系统正在维护中，请稍后再试') if data else '系统正在维护中，请稍后再试'
        
        # 更新维护模式配置
        maintenance_config = SystemConfig.query.filter_by(key='maintenance_mode').first()
        
        if maintenance_config:
            maintenance_config.value = str(enabled).lower()
            maintenance_config.updated_at = datetime.utcnow()
            maintenance_config.updated_by = current_user.id
        else:
            maintenance_config = SystemConfig(
                key='maintenance_mode',
                value=str(enabled).lower(),
                description='系统维护模式开关',
                is_sensitive=False,
                created_by=current_user.id,
                updated_by=current_user.id
            )
            db.session.add(maintenance_config)
        
        # 更新维护消息
        message_config = SystemConfig.query.filter_by(key='maintenance_message').first()
        
        if message_config:
            message_config.value = message
            message_config.updated_at = datetime.utcnow()
            message_config.updated_by = current_user.id
        else:
            message_config = SystemConfig(
                key='maintenance_message',
                value=message,
                description='系统维护模式消息',
                is_sensitive=False,
                created_by=current_user.id,
                updated_by=current_user.id
            )
            db.session.add(message_config)
        
        db.session.commit()
        
        # 记录用户活动
        log_user_activity(current_user.id, 'toggle_maintenance_mode', {
            'enabled': enabled,
            'message': message
        })
        
        action = '启用' if enabled else '禁用'
        current_app.logger.info(f"管理员 {current_user.username} {action}维护模式")
        
        return jsonify({
            'success': True,
            'message': f'维护模式已{action}',
            'data': {
                'enabled': enabled,
                'message': message
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"切换维护模式错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '维护模式切换失败'
        }), 500