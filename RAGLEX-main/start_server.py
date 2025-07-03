#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法律智能助手服务启动脚本

使用方法:
    python start_server.py
    
或者指定端口:
    python start_server.py --port 8080
"""

import argparse
import uvicorn
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import config

def main():
    parser = argparse.ArgumentParser(description='启动法律智能助手服务')
    parser.add_argument('--host', default=config.WEB_HOST, help='服务器地址')
    parser.add_argument('--port', type=int, default=config.WEB_PORT, help='服务器端口')
    parser.add_argument('--reload', action='store_true', help='开启热重载（开发模式）')
    parser.add_argument('--workers', type=int, default=1, help='工作进程数')
    
    args = parser.parse_args()
    
    print("🚀 正在启动法律智能助手服务...")
    print(f"📍 服务地址: http://{args.host}:{args.port}")
    print(f"📖 API文档: http://{args.host}:{args.port}/docs")
    print(f"🔧 交互式API: http://{args.host}:{args.port}/redoc")
    print("="*50)
    
    # 检查必要的环境变量
    if not os.getenv('OPENAI_API_KEY') and not os.getenv('DEEPSEEK_API_KEY'):
        print("⚠️  警告: 未检测到 OPENAI_API_KEY 或 DEEPSEEK_API_KEY 环境变量")
        print("   请确保在 .env 文件中配置了相应的API密钥")
    
    try:
        uvicorn.run(
            "app:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers if not args.reload else 1,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 启动服务时发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()