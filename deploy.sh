#!/bin/bash

# RAGLEX项目部署脚本
# 用于自动化构建和部署前后端应用

set -e  # 遇到错误时退出

echo "=== RAGLEX项目部署开始 ==="

# 检查Docker和Docker Compose是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 检查Node.js和npm是否安装
if ! command -v node &> /dev/null; then
    echo "错误: Node.js未安装，请先安装Node.js"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "错误: npm未安装，请先安装npm"
    exit 1
fi

echo "1. 构建前端应用..."
cd law_front

# 安装前端依赖
echo "   安装前端依赖..."
npm install

# 构建前端应用
echo "   构建前端应用..."
npm run build

echo "   前端构建完成！"

cd ..

echo "2. 构建和启动后端服务..."
cd law_backend_flask

# 创建必要的目录
mkdir -p nginx/ssl
mkdir -p uploads
mkdir -p logs

# 停止现有服务（如果存在）
echo "   停止现有服务..."
docker-compose down

# 构建并启动服务
echo "   构建并启动服务..."
docker-compose up --build -d

echo "   等待服务启动..."
sleep 10

# 检查服务状态
echo "3. 检查服务状态..."
docker-compose ps

echo ""
echo "=== 部署完成 ==="
echo "前端应用: http://localhost"
echo "后端API: http://localhost/api"
echo "MinIO控制台: http://localhost:9001"
echo "MySQL端口: 3306"
echo "Redis端口: 6379"
echo ""
echo "请确保在生产环境中修改以下配置:"
echo "- 数据库密码 (docker-compose.yml)"
echo "- JWT密钥 (docker-compose.yml)"
echo "- MinIO访问密钥 (docker-compose.yml)"
echo "- SSL证书 (nginx/ssl/)"
echo ""
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"