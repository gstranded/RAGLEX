# RAGLEX 法律案件管理系统 - Flask 后端

这是一个基于 Flask 的法律案件管理系统后端，集成了 MySQL 数据库、MinIO 对象存储和用户认证系统，为前端界面提供完整的 RESTful API 服务。

## 功能特性

### 核心功能
- **用户认证系统**: JWT 令牌认证、用户注册登录、权限管理
- **案件管理系统**: 完整的案件 CRUD 操作，支持文档上传下载
- **文档存储系统**: 基于 MinIO 的 PDF 文件存储和管理
- **历史记录管理**: 用户查询历史的存储和管理
- **系统配置**: 灵活的配置管理和统计信息
- **知识库接口**: 预留的知识库问答接口（待实现）

### 技术特性
- RESTful API 设计
- JWT 身份认证
- MySQL 数据库存储
- MinIO 对象存储
- CORS 跨域支持
- 错误处理和日志记录
- 分页支持
- 数据验证
- Docker 容器化部署
- 应用工厂模式

## API 接口

### 用户认证
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/profile` - 获取用户资料
- `PUT /api/auth/profile` - 更新用户资料

### 案件管理
- `GET /api/cases` - 获取案件列表（支持搜索、分页、筛选）
- `GET /api/cases/<id>` - 获取单个案件详情
- `POST /api/cases` - 创建案件（需要登录）

### 文档管理
- `POST /api/cases/<case_id>/documents` - 上传案件文档（需要登录）
- `GET /api/cases/<case_id>/documents/<doc_id>/download` - 下载案件文档（需要登录）
- `DELETE /api/cases/<case_id>/documents/<doc_id>` - 删除案件文档（需要登录）

### 历史记录
- `GET /api/history` - 获取查询历史（需要登录）
- `DELETE /api/history/<id>` - 删除单条历史记录（需要登录）
- `DELETE /api/history/clear` - 清空历史记录（需要登录）

### 知识库（预留接口）
- `POST /api/query` - 知识库问答（待实现）


### 系统配置
- `GET /api/config` - 获取系统配置
- `GET /api/statistics` - 获取统计信息（需要登录）
- `GET /health` - 健康检查

## 安装和运行

### 环境要求
- Python 3.8+
- MySQL 8.0+
- MinIO 服务器
- pip

### 快速部署

#### 方式一：使用部署脚本（推荐）

1. 克隆项目
```bash
git clone <repository-url>
cd law_backend_flask
```

2. 给部署脚本执行权限
```bash
chmod +x deploy.sh
```

3. 完整部署
```bash
./deploy.sh --full
```

4. 启动应用
```bash
./deploy.sh --start
```

#### 方式二：使用 Docker（推荐生产环境）

1. 确保安装了 Docker 和 Docker Compose

2. 使用 Docker 部署
```bash
./deploy.sh --docker
```

#### 方式三：手动安装

1. 安装 Python 依赖
```bash
pip install -r requirements.txt
```

2. 配置 MySQL 数据库
```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE raglex_law CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

3. 配置 MinIO
```bash
# 下载并启动 MinIO
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
./minio server ./minio-data --console-address ":9001"
```

4. 初始化数据库
```bash
python init_db.py
```

5. 启动应用
```bash
python run.py
```

### 访问地址

- **Flask 应用**: http://localhost:5000
- **健康检查**: http://localhost:5000/health
- **MinIO 控制台**: http://localhost:9001

### 默认账户

- **管理员账户**: 
  - 用户名: `admin`
  - 密码: `admin123`

- **测试账户**: 
  - 用户名: `testuser`
  - 密码: `test123`

### 测试

运行 API 测试：
```bash
python test_api.py
# 或使用部署脚本
./deploy.sh --test
```

## 项目结构

```
law_backend_flask/
├── app.py                 # 主应用文件
├── config.py              # 配置文件
├── models.py              # 数据库模型
├── init_db.py             # 数据库初始化脚本
├── requirements.txt       # 依赖包列表
├── test_api.py           # API测试脚本
├── run.py                # 应用启动脚本
├── deploy.sh             # 部署脚本
├── Dockerfile            # Docker配置
├── docker-compose.yml    # Docker Compose配置
├── utils/                # 工具模块
│   ├── __init__.py
│   ├── auth.py           # 认证工具
│   └── minio_client.py   # MinIO客户端
├── uploads/              # 文件上传目录
├── logs/                 # 日志目录
├── data/                 # 数据存储目录
├── minio-data/           # MinIO数据目录
└── README.md             # 项目说明
```

## 配置说明

### 环境变量

在 `.env` 文件中配置以下环境变量：

```bash
# Flask 配置
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# 数据库配置
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/raglex_law

# JWT 配置
JWT_SECRET_KEY=your-jwt-secret-key

# MinIO 配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=raglex-documents

# CORS 配置
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

### 配置文件

主要配置在 `config.py` 中：

```python
class Config:
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT 配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
    # MinIO 配置
    MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT')
    MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY')
    MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY')
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
```

## 数据模型

### 用户 (User)
```python
{
    "id": 1,
    "username": "用户名",
    "email": "邮箱地址",
    "password_hash": "密码哈希",
    "full_name": "真实姓名",
    "role": "用户角色",
    "is_active": "是否激活",
    "created_at": "创建时间",
    "last_login": "最后登录时间"
}
```

### 案件 (Case)
```python
{
    "id": 1,
    "title": "案件标题",
    "case_number": "案件编号",
    "court": "审理法院",
    "case_type": "案件类型",
    "status": "案件状态",
    "date": "审理日期",
    "description": "案件描述",
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "documents": ["关联文档列表"]
}
```

### 案件文档 (CaseDocument)
```python
{
    "id": 1,
    "case_id": "关联案件ID",
    "filename": "文件名",
    "original_filename": "原始文件名",
    "file_size": "文件大小",
    "content_type": "文件类型",
    "minio_path": "MinIO存储路径",
    "uploaded_by": "上传用户ID",
    "uploaded_at": "上传时间"
}
```



## 扩展功能

### 1. 数据库集成
可以集成 SQLite、MySQL 或 PostgreSQL 数据库来持久化存储数据：

```bash
pip install Flask-SQLAlchemy
```

### 2. 认证授权
可以添加用户认证和权限管理：

```bash
pip install Flask-JWT-Extended
```

### 3. 日志记录
可以添加详细的日志记录功能：

```bash
pip install Flask-Logging
```

### 4. API 文档
可以使用 Flask-RESTX 生成 API 文档：

```bash
pip install Flask-RESTX
```

## 注意事项

1. 当前使用内存存储数据，重启服务后数据会丢失
2. 生产环境建议使用数据库进行数据持久化
3. 文件上传功能需要确保有足够的磁盘空间
4. 建议在生产环境中使用 Gunicorn 或 uWSGI 部署

## 部署建议

### 使用 Gunicorn 部署

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:3000 app:app
```

### 使用 Docker 部署

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 3000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:3000", "app:app"]
```

## 开发说明

### 开发环境设置

1. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

2. 安装开发依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件配置数据库和MinIO连接
```

### 添加新的API接口

1. 在 `app.py` 的 `register_routes` 函数中添加路由
2. 实现业务逻辑和数据验证
3. 添加认证装饰器（如需要）
4. 添加错误处理和日志记录
5. 更新 `test_api.py` 添加测试用例

### 数据库操作

```python
# 创建新记录
new_case = Case(title='新案件', case_number='2024001')
db.session.add(new_case)
db.session.commit()

# 查询记录
cases = Case.query.filter_by(status='active').all()

# 更新记录
case = Case.query.get(1)
case.status = 'closed'
db.session.commit()
```

### 文件上传处理

```python
from utils.minio_client import upload_file, download_file

# 上传文件到MinIO
file_path = upload_file(file, bucket_name, object_name)

# 下载文件
file_data = download_file(bucket_name, object_name)
```

## 部署说明

### Docker 部署（推荐）

```bash
# 构建并启动所有服务
docker-compose up --build -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app

# 停止服务
docker-compose down
```

### 生产环境部署

1. 使用 Gunicorn 作为 WSGI 服务器
```bash
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app
```

2. 配置 Nginx 反向代理
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_timeout 120s;
    }
}
```

3. 配置 SSL 证书（推荐使用 Let's Encrypt）
```bash
sudo certbot --nginx -d your-domain.com
```

### 监控和日志

- 应用日志：`logs/app.log`
- 错误日志：`logs/error.log`
- 数据库日志：查看 MySQL 日志
- MinIO 日志：查看 MinIO 服务日志

### 备份策略

1. 数据库备份
```bash
mysqldump -u root -p raglex_law > backup_$(date +%Y%m%d).sql
```

2. MinIO 数据备份
```bash
tar -czf minio_backup_$(date +%Y%m%d).tar.gz minio-data/
```

## 联系方式

如有问题或建议，请联系开发团队。