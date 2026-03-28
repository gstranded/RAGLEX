# RUN_LOCAL

本文档面向“拿到仓库就想先跑起来”的场景。

## 最短路径

### 1. 复制环境文件

```bash
cp .env.local.example .env.local
```

### 2. 启动 Ollama 并拉模型

```bash
ollama serve
./scripts/pull_ollama_model.sh
```

如果机器资源有限，可以改拉更小的模型：

```bash
OLLAMA_MODEL=qwen2.5:3b ./scripts/pull_ollama_model.sh
```

### 3. 一键启动

```bash
./deploy.sh
```

### 4. 打开页面

```text
http://127.0.0.1:13000
```

### 5. 一键回归

```bash
./scripts/smoke_local.sh
```

## 如果系统里没有 venv / pip

可以直接执行：

```bash
./scripts/bootstrap_python.sh
```

它会：

1. 检查 `python3`
2. 如缺少 `pip`，自动通过 `get-pip.py --user` 安装
3. 安装 `virtualenv`
4. 创建仓库本地 `.venv`
5. 安装后端依赖

## 如果你不想用 Ollama

把 `.env.local` 改成你自己的 OpenAI-compatible 端点：

```env
OPENAI_COMPAT_BASE_URL=https://your-endpoint.example.com/v1
OPENAI_COMPAT_API_KEY=your-api-key
OPENAI_CHAT_MODEL=your-model-name
```

然后重新执行：

```bash
./deploy.sh
```

## 运行控制

### 启动

```bash
./scripts/start_local.sh
```

### 停止

```bash
./scripts/stop_local.sh
```

### 状态

```bash
./scripts/status_local.sh
```

### 回归测试

```bash
./scripts/smoke_local.sh
```

如果后端已经启动，`smoke_local.sh` 会复用当前实例；如果没有启动，它会自行拉起并在结束后自动清理。

### 日志

```bash
tail -f .logs/backend.log
tail -f .logs/frontend.log
```

## 常见问题

### 1. `ollama` 不存在

先安装：

<https://ollama.com/download>

### 2. 问答时报网络错误

通常是模型端点不可用。先检查：

```bash
curl http://127.0.0.1:11434/v1/models
```

### 3. 文件上传失败

默认本地模式不依赖 MinIO，会写入：

```text
law_backend_flask/data/local_object_store/
```

请确认当前用户对该目录有写权限。

### 4. 前端能打开但接口报错

检查：

```bash
curl http://127.0.0.1:5000/api/health
```

期望返回：

```json
{
  "status": "healthy"
}
```

如果你改过 `.env.local` 里的端口，请把上面的 `5000` 换成你自己的 `BACKEND_PORT`。
