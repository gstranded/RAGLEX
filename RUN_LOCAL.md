# RUN_LOCAL (clean-clone)

目标：在**无 sudo**、系统 `python3` 缺 `pip/venv` 的主机上，也能跑通 RAGLEX 最小本地闭环：

- 后端：SQLite + `MINIO_DISABLED=true` 启动，并能访问 `/api/health`
- 前端：`law_front` 可 `npm install` + `npm run build`（或 `npm run serve`）

> 本文档面向「clean clone」。如果你在旧目录里遇到 `npm install EACCES`，优先重新 `git clone` 到当前用户拥有的目录。

---

## 0) 前置条件

- Linux
- `python3` (>= 3.10)
- `curl`
- `node` + `npm`

> 备注：当前 host 的已知限制：`python3 -m pip` 不存在、`python3 -m venv` 失败（缺 `python3-venv/ensurepip`），且无 sudo。

---

## 1) 后端（SQLite + MINIO disabled）

### 1.1 Python bootstrap（无 sudo）

在仓库根目录执行：

```bash
./scripts/bootstrap_python.sh
```

它会：

1. 用 `get-pip.py --user` 安装 pip 到用户目录（不依赖系统 `python3-venv`）
2. 安装 `virtualenv`
3. 创建 repo-local venv：`./.venv`
4. 安装后端依赖：`law_backend_flask/requirements.txt`

### 1.2 启动后端

```bash
./scripts/run_backend_sqlite.sh
```

默认：

- `DEV_DATABASE_URL=sqlite:///law_backend_flask/data/raglex-dev.sqlite3`
- `MINIO_DISABLED=true`
- listen: `127.0.0.1:5000`

### 1.3 健康检查

```bash
curl -fsS http://127.0.0.1:5000/api/health | jq .
```

期望：HTTP 200，且 `status=healthy`。

---

## 2) 前端（law_front）

```bash
cd law_front

# 不复用旧 node_modules（避免“污染”与权限问题）
rm -rf node_modules

npm install
npm run build

# 开发模式
npm run serve
# -> http://127.0.0.1:13000 （vite.config.js 里配置）
```

默认 proxy：`/api -> http://localhost:5000`

---

## 3) 一键 smoke（可选）

```bash
./scripts/smoke_local.sh
```

它会：

- bootstrap python + 启动后端 + curl `/api/health`
- 清理前端 `node_modules` 后执行 `npm install` + `npm run build`

---

## 常见问题

### Q1: `npm install` 报 EACCES

这通常是目录 ownership 错了（例如目录由其他 uid 拥有）。建议：

- 不要在“别人拥有”的目录里硬修
- 重新 `git clone` 到你自己拥有的目录

### Q2: 后端启动慢 / 卡住

若本机没有 MinIO，确保：

```bash
export MINIO_DISABLED=true
```

（`run_backend_sqlite.sh` 默认已设置。）
