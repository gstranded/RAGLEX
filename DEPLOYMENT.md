# RAGLEX 部署指南

本文档详细说明了如何部署RAGLEX法律知识问答系统。

## 系统要求

### 硬件要求
- CPU: 2核心以上
- 内存: 4GB以上
- 存储: 20GB以上可用空间

### 软件要求
- Docker 20.10+
- Docker Compose 2.0+
- Node.js 16+
- npm 8+

## 快速部署

### 1. 克隆项目
```bash
git clone <repository-url>
cd RAGLEX
```

### 2. 一键部署
```bash
./deploy.sh
```

### 3. 访问应用
- 前端应用: http://localhost
- 后端API: http://localhost/api
- MinIO控制台: http://localhost:9001

## 手动部署

### 1. 构建前端
```bash
cd law_front
npm install
npm run build
cd ..
```

### 2. 配置环境变量
```bash
cd law_backend_flask
cp .env.production .env
# 编辑 .env 文件，修改密码和密钥
```

### 3. 启动服务
```bash
docker-compose up --build -d
```

## 服务架构

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Nginx     │    │   Flask     │    │   MySQL     │
│  (端口80)   │───▶│  (端口5000) │───▶│  (端口3306) │
└─────────────┘    └─────────────┘    └─────────────┘
                           │
                           ▼
                   ┌─────────────┐    ┌─────────────┐
                   │   MinIO     │    │   Redis     │
                   │  (端口9000) │    │  (端口6379) │
                   └─────────────┘    └─────────────┘
```

## 服务说明

### Nginx (反向代理)
- 端口: 80, 443
- 功能: 静态文件服务、API代理
- 配置文件: `law_backend_flask/nginx/nginx.conf`

### Flask (后端应用)
- 端口: 5000 (内部)
- 功能: API服务、业务逻辑
- WSGI服务器: Gunicorn + Gevent

### MySQL (数据库)
- 端口: 3306
- 功能: 用户数据、文件元数据存储
- 数据卷: `mysql_data`

### MinIO (对象存储)
- 端口: 9000 (API), 9001 (控制台)
- 功能: 文件存储
- 数据卷: `minio_data`

### Redis (缓存)
- 端口: 6379
- 功能: 会话缓存、临时数据
- 数据卷: `redis_data`

## 生产环境配置

### 1. 安全配置

#### 修改默认密码
编辑 `law_backend_flask/.env` 文件:
```env
# 数据库密码
MYSQL_ROOT_PASSWORD=your-strong-root-password
MYSQL_PASSWORD=your-strong-user-password

# MinIO密钥
MINIO_ACCESS_KEY=your-minio-access-key
MINIO_SECRET_KEY=your-strong-minio-secret-key

# 应用密钥
SECRET_KEY=your-32-char-secret-key
JWT_SECRET_KEY=your-32-char-jwt-secret-key
```

#### SSL证书配置
1. 将SSL证书文件放置在 `law_backend_flask/nginx/ssl/` 目录
2. 修改 `nginx.conf` 添加HTTPS配置:
```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    # ... 其他配置
}
```

### 2. 性能优化

#### Gunicorn配置
编辑 `law_backend_flask/gunicorn.conf.py`:
```python
# 根据CPU核心数调整工作进程
workers = multiprocessing.cpu_count() * 2 + 1

# 生产环境建议使用gevent
worker_class = 'gevent'
worker_connections = 1000
```

#### 数据库优化
编辑 `docker-compose.yml` 中MySQL配置:
```yaml
command: >
  --default-authentication-plugin=mysql_native_password
  --innodb-buffer-pool-size=1G
  --max-connections=200
```

### 3. 监控和日志

#### 查看服务状态
```bash
docker-compose ps
docker-compose logs -f
```

#### 查看特定服务日志
```bash
docker-compose logs -f flask_app
docker-compose logs -f nginx
docker-compose logs -f mysql
```

#### 健康检查
```bash
curl http://localhost/health
```

## 维护操作

### 备份数据
```bash
# 备份MySQL数据
docker-compose exec mysql mysqldump -u root -p raglex_law > backup.sql

# 备份MinIO数据
docker-compose exec minio mc mirror /data /backup
```

### 更新应用
```bash
# 拉取最新代码
git pull

# 重新构建前端
cd law_front
npm run build
cd ..

# 重新构建并启动服务
cd law_backend_flask
docker-compose up --build -d
```

### 扩容
```bash
# 增加Flask应用实例
docker-compose up --scale flask_app=3 -d
```

## 故障排除

### 常见问题

1. **服务启动失败**
   - 检查端口是否被占用
   - 检查Docker和Docker Compose版本
   - 查看服务日志: `docker-compose logs`

2. **数据库连接失败**
   - 检查数据库密码配置
   - 确认MySQL服务已启动
   - 检查网络连接: `docker-compose exec flask_app ping mysql`

3. **文件上传失败**
   - 检查MinIO服务状态
   - 验证MinIO访问密钥
   - 检查存储空间

4. **前端页面无法访问**
   - 检查Nginx配置
   - 确认前端构建成功
   - 检查静态文件路径

### 调试模式
```bash
# 启用调试模式
export FLASK_ENV=development
docker-compose up
```

## 性能基准

### 推荐配置
- 生产环境: 4核8GB内存
- 并发用户: 100+
- 响应时间: <200ms
- 文件上传: 支持100MB以下文件

### 监控指标
- CPU使用率 < 70%
- 内存使用率 < 80%
- 磁盘使用率 < 85%
- 数据库连接数 < 150

## 联系支持

如遇到部署问题，请提供以下信息:
1. 操作系统版本
2. Docker版本
3. 错误日志
4. 服务状态: `docker-compose ps`