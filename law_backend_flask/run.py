#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAGLEX 法律案件管理系统 - 应用启动脚本

这个脚本用于启动 Flask 应用，支持不同的运行模式和配置选项。
"""

import os
import sys
import argparse
from app import create_app
from config import DevelopmentConfig, ProductionConfig, TestingConfig

def get_config_class(env):
    """根据环境变量获取配置类"""
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    return config_map.get(env.lower(), DevelopmentConfig)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='RAGLEX 法律案件管理系统')
    parser.add_argument('--host', default='0.0.0.0', help='服务器主机地址 (默认: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='服务器端口 (默认: 5000)')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--env', choices=['development', 'production', 'testing'], 
                       default='development', help='运行环境 (默认: development)')
    parser.add_argument('--init-db', action='store_true', help='初始化数据库后启动')
    
    args = parser.parse_args()
    
    # 设置环境变量
    os.environ['FLASK_ENV'] = args.env
    if args.debug:
        os.environ['FLASK_DEBUG'] = 'True'
    
    # 获取配置类
    config_class = get_config_class(args.env)
    
    try:
        # 创建应用
        app = create_app(args.env)
        
        # 如果需要初始化数据库
        if args.init_db:
            print("正在初始化数据库...")
            from init_db import init_database
            with app.app_context():
                init_database()
            print("数据库初始化完成！")
        
        # 启动信息
        print(f"\n🚀 RAGLEX 法律案件管理系统正在启动...")
        print(f"📍 环境: {args.env}")
        print(f"🌐 地址: http://{args.host}:{args.port}")
        print(f"🔍 健康检查: http://{args.host}:{args.port}/health")
        print(f"📚 API文档: 请查看 README.md")
        
        if args.env == 'development':
            print(f"🐛 调试模式: {'开启' if args.debug else '关闭'}")
            print(f"🔄 自动重载: 开启")
        
        print("\n按 Ctrl+C 停止服务器\n")
        
        # 启动应用
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug and args.env == 'development',
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()