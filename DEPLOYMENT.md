# RAGLEX Deployment Guide

本文档描述当前推荐的 RAGLEX 部署方式。默认推荐的是：

- Flask 后端
- Vue 前端
- SQLite
- 本地文件存储兜底
- OpenAI-compatible LLM

这是当前仓库里最稳定、最容易复现、最适合 GitHub 用户直接运行的链路。

## 1. 部署模式

### 模式 A：本地开发 / 单机部署

适合：

- 本地开发
- 单机演示
- 云主机快速试跑

组成：

- 前端：Vite dev server
- 后端：Flask
- 数据库：SQLite
- 文件存储：本地文件系统
- 模型：Ollama 或任意 OpenAI-compatible 服务

入口命令：

```bash
./deploy.sh
```

### 模式 B：单机生产化部署

适合：

- 内网服务器
- 单台 Linux 主机
- 小规模团队内部使用

建议组合：

- 前端：构建后用 Nginx/Caddy 托管
- 后端：Flask + Gunicorn / systemd
- 数据库：SQLite 或 MySQL
- 文件存储：本地文件系统或 MinIO
- 模型：Ollama / vLLM / LM Studio / OneAPI / OpenAI-compatible provider

## 2. 前置要求

### 必需

- Linux / macOS
- `python3` 3.10+
- `node` 18+
- `npm`
- `curl`

### 模型服务

二选一：

1. 本地 Ollama
2. 外部 OpenAI-compatible API

## 3. 环境配置

复制模板：

```bash
cp .env.local.example .env.local
```

默认模板已经包含：

```env
BACKEND_HOST=127.0.0.1
BACKEND_PORT=5000
FRONTEND_HOST=127.0.0.1
FRONTEND_PORT=13000
DEV_DATABASE_URL=sqlite:///law_backend_flask/data/raglex-dev.sqlite3
MINIO_DISABLED=true
OPENAI_COMPAT_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_COMPAT_API_KEY=ollama
OPENAI_CHAT_MODEL=qwen2.5:7b
```

说明：

- `DEV_DATABASE_URL=sqlite:///law_backend_flask/data/raglex-dev.sqlite3` 这类相对 SQLite 路径会由仓库脚本自动转换为绝对路径
- `.env.local` 不应提交到 GitHub

### 关键变量说明

| 变量 | 说明 |
|---|---|
| `BACKEND_HOST` | 后端监听地址 |
| `BACKEND_PORT` | 后端端口 |
| `FRONTEND_HOST` | 前端监听地址 |
| `FRONTEND_PORT` | 前端端口 |
| `DEV_DATABASE_URL` | 开发环境 SQLite 地址 |
| `MINIO_DISABLED` | `true` 时不连接 MinIO，自动改用本地文件存储 |
| `OPENAI_COMPAT_BASE_URL` | OpenAI-compatible 接口地址 |
| `OPENAI_COMPAT_API_KEY` | OpenAI-compatible 接口密钥 |
| `OPENAI_CHAT_MODEL` | 默认使用的生成模型 |
| `VITE_PROXY_TARGET` | 前端 dev server 代理的后端地址 |
| `VITE_API_BASE_URL` | 前端部署到独立域名时可显式指定 API Base |

## 4. 模型部署

### 4.1 使用 Ollama

安装 Ollama：

- 官方下载：<https://ollama.com/download>
- OpenAI-compatible 文档：<https://ollama.com/blog/openai-compatibility>
- Qwen2.5 模型页：<https://ollama.com/library/qwen2.5>

启动服务：

```bash
ollama serve
```

拉取模型：

```bash
./scripts/pull_ollama_model.sh
```

默认拉取：

```text
qwen2.5:7b
```

如果机器资源有限：

```bash
OLLAMA_MODEL=qwen2.5:3b ./scripts/pull_ollama_model.sh
```

然后把 `.env.local` 改为：

```env
OPENAI_CHAT_MODEL=qwen2.5:3b
```

### 4.2 使用外部 OpenAI-compatible 服务

例如：

- vLLM
- LM Studio
- OneAPI
- 官方 OpenAI
- 云厂商兼容网关

只要改 `.env.local`：

```env
OPENAI_COMPAT_BASE_URL=https://your-endpoint.example.com/v1
OPENAI_COMPAT_API_KEY=your-api-key
OPENAI_CHAT_MODEL=your-model-name
```

## 5. 一键启动

```bash
./deploy.sh
```

实际执行逻辑：

1. 创建或复用 `.venv`
2. 安装后端依赖
3. 安装前端依赖（如果缺失）
4. 启动 Flask
5. 启动 Vite
6. 等待前后端 ready

启动后：

- 前端：`http://127.0.0.1:13000`
- 后端：`http://127.0.0.1:5000`
- 健康检查：`http://127.0.0.1:5000/api/health`

## 6. 服务管理

### 启动

```bash
./scripts/start_local.sh
```

### 停止

```bash
./scripts/stop_local.sh
```

### 查看状态

```bash
./scripts/status_local.sh
```

### 查看日志

```bash
tail -f .logs/backend.log
tail -f .logs/frontend.log
```

## 7. 一键回归

```bash
./scripts/smoke_local.sh
```

这个脚本会：

1. 启动前后端
2. 检查 `/api/health`
3. 构建前端生产包
4. 跑完整接口级 e2e smoke

当前 smoke 已覆盖：

- 注册 / 登录
- 会话创建
- 文件上传 / 下载
- 私有知识库上传 / 检索
- 公有知识库上传 / 检索
- 取消公有知识库后立即失效
- 会话历史落库

如果当前端口上已经有健康的 RAGLEX 后端实例，`smoke_local.sh` 会直接复用它，不会在结束时主动停掉现有服务。

如果失败，请先检查：

- `OPENAI_COMPAT_BASE_URL` 是否可访问
- 模型是否已下载
- `OPENAI_CHAT_MODEL` 是否存在

## 8. 远程服务器部署

如果你要把服务暴露给局域网或公网用户：

### 8.1 修改监听地址

在 `.env.local` 中改成：

```env
BACKEND_HOST=0.0.0.0
FRONTEND_HOST=0.0.0.0
```

### 8.2 建议反向代理

推荐：

- Nginx
- Caddy

建议做法：

- 前端静态构建产物由 Nginx 托管
- `/api` 反代到 Flask
- HTTPS 终止在代理层

### 8.3 systemd 托管示例

可以为 `start_local.sh` 做一个 systemd service：

```ini
[Unit]
Description=RAGLEX
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/RAGLEX
ExecStart=/opt/RAGLEX/scripts/start_local.sh
ExecStop=/opt/RAGLEX/scripts/stop_local.sh
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

如果你要更严格地管理两个进程，建议拆成两个 unit：

- `raglex-backend.service`
- `raglex-frontend.service`

## 9. 数据与备份

默认需要备份的目录：

- `law_backend_flask/data/`
- `.env.local`

其中：

- `law_backend_flask/data/raglex-dev.sqlite3`：用户、文件、会话、知识切片
- `law_backend_flask/data/local_object_store/`：上传的原始文件

## 10. MinIO / MySQL 何时需要

默认本地部署不需要。

只有在你明确要这些能力时再开启：

- 用 MySQL 替换 SQLite
- 用 MinIO 替换本地对象存储

本仓库当前实现已经支持：

- MinIO 不可用时自动退回本地存储
- SQLite 即可完成完整链路

## 11. 旧版 `RAGLEX-main` 的定位

`RAGLEX-main/` 是历史上保留下来的独立 FastAPI RAG 实验目录。

当前默认部署：

- 不依赖它
- 不要求启动它
- 不要求下载它的 embedding / reranker 模型

如果你要研究旧版完整向量链路，可以单独进入该目录做二次开发，但这不属于当前推荐部署路径。

## 12. 故障排查

### 12.1 启动后问答失败

优先检查模型端点：

```bash
curl http://127.0.0.1:11434/v1/models
```

如果失败，说明 Ollama 没启动或模型端点未配置好。

### 12.2 上传文件失败

检查：

- `law_backend_flask/data/` 是否可写
- 磁盘空间是否足够

### 12.3 前端打不开

检查：

```bash
./scripts/status_local.sh
tail -f .logs/frontend.log
```

如果 `./scripts/start_local.sh` 直接报端口占用，说明 `BACKEND_PORT` 或 `FRONTEND_PORT` 已被别的进程占用。请先释放端口，或在 `.env.local` 中改用新的端口号。

### 12.4 健康检查不通过

检查：

```bash
curl http://127.0.0.1:5000/api/health
```

如果 `database=healthy` 且 `minio=disabled/local/healthy`，则服务可用。
