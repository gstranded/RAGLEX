# RAGLEX - 法律领域检索增强生成问答系统

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.9%2B-blueviolet)
![Flask](https://img.shields.io/badge/Flask-2.x-orange)
![Vue.js](https://img.shields.io/badge/Vue.js-3.x-green)

RAGLEX 是一个专为法律领域设计的问答系统。它结合了**检索增强生成 (Retrieval-Augmented Generation, RAG)** 技术，能够基于本地知识库中的法律文档，为用户提供精准、有据可依的回答。

## ✨ 项目特色

* **领域专注**: 深度聚焦于法律领域，提供更专业的问答体验。
* **本地知识库**: 完全基于你提供的本地法律文档进行回答，保证了信息的私密性和可靠性。
* **精准溯源**: 每个回答都能追溯到原文出处，方便用户核实信息来源。
* **前后端分离**: 采用现代化的前后端分离架构，易于维护和扩展。
* **Web 界面**: 提供简洁直观的 Web 交互界面，用户体验友好。

## 🔧 技术栈

* **后端**:
    * **框架**: Flask
    * **核心引擎**: LangChain
    * **模型**: Sentence-Transformers (用于文本嵌入), 以及任何兼容的 LLM (如 ChatGLM, Llama 等)
* **前端**:
    * **框架**: Vue 3
    * **UI 库**: Element Plus
* **部署**: Shell 脚本 (`deploy.sh`)

## 🚀 快速开始

请按照以下步骤在本地环境中安装和运行本项目。

### 1. 克隆项目

```bash
git clone [https://github.com/gstranded/RAGLEX.git](https://github.com/gstranded/RAGLEX.git)
cd RAGLEX
```

### 2. 准备知识库

将你的法律文档（如 `.txt`, `.md`, `.pdf` 文件）放入 `data` 文件夹下。系统将基于这些文件创建向量知识库。

```bash
# 示例：
cp /path/to/your/legal_docs/* data/
```

### 3. 配置并运行后端

```bash
# 进入后端目录
cd law_backend_flask

# 创建并激活 Python 虚拟环境 

# 启动后端 Flask 服务
python run.py --env development --debug --host 0.0.0.0 --port 5000
```
默认情况下，后端服务会运行在 `http://127.0.0.1:5000`。


minio：使用wget下载minio之后：
./minio server /data --console-address ":9001"

### 4. 配置并运行前端

```bash
# (在项目根目录) 进入前端目录
cd law_front

# 安装依赖
npm install

# 启动前端开发服务器
npm run serve
```
前端服务启动后，你可以在浏览器中打开提示的地址 (通常是 `http://localhost:8080`) 来访问问答系统。

## 📂 项目结构

```
RAGLEX/
│
├── data/                    # 存放本地知识库源文件
├── law_backend_flask/       # 后端 Flask 应用
│   ├── app.py               # Flask 主程序
│   └── requirements.txt     # Python 依赖
│
├── law_front/               # 前端 Vue 应用
│   ├── src/                 # 前端源码
│   ├── package.json         # Node.js 依赖
│   └── vue.config.js        # Vue 配置文件
│
├── deploy.sh                # 自动化部署脚本
├── DEPLOYMENT.md            # 详细的部署指南
├── LICENSE                  # 项目许可证
└── README.md                # 你正在阅读的文件
```

## 📜 部署

本项目提供了一键部署脚本 `deploy.sh`。有关详细的生产环境部署步骤，请参考 [DEPLOYMENT.md](DEPLOYMENT.md)。

## 🤝 贡献

欢迎对本项目进行贡献！你可以通过以下方式参与：

1.  Fork 本仓库
2.  创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3.  提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4.  将你的分支推送到远程 (`git push origin feature/AmazingFeature`)
5.  创建一个 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。详情请见 [LICENSE](LICENSE) 文件。
