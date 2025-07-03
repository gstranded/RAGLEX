# RAGLEX法律大模型后端服务

## 项目说明
这是RAGLEX法律大模型的后端服务，提供了法律问答、知识库管理和历史记录等功能的API接口。

## 项目结构
```
backend/
  ├── src/
  │   └── index.js      # 服务器入口文件
  ├── .env              # 环境变量配置
  ├── package.json      # 项目依赖配置
  └── README.md         # 项目说明文档
```

## 安装和运行
1. 安装依赖：
```bash
cd backend
npm install
```

2. 配置环境变量：
- 复制`.env.example`文件为`.env`
- 根据实际情况修改配置项

3. 启动服务：
- 开发环境：`npm run dev`
- 生产环境：`npm start`

## API接口说明

### 1. 法律问答
- 接口：POST /api/query
- 功能：处理用户的法律问题，返回AI模型的回答
- 请求参数：
  ```json
  {
    "question": "问题内容",
    "mode": "knowledgeQA",
    "knowledge": ["criminalLaw", "criminalBook"]
  }
  ```
- 响应格式：
  ```json
  {
    "answer": "AI回答内容",
    "references": [
      {
        "content": "参考资料内容",
        "source": "来源"
      }
    ]
  }
  ```

### 2. 知识库管理
- 知识库管理功能已移除（使用外部服务器）

### 3. 历史记录查询
- 接口：GET /api/history
- 功能：获取问答历史记录
- 响应格式：
  ```json
  [
    {
      "id": 1,
      "question": "问题内容",
      "answer": "回答内容",
      "timestamp": "2023-08-20T10:00:00Z"
    }
  ]
  ```

## 注意事项
1. 确保MongoDB服务已启动
2. 确保AI模型服务可访问
3. 开发环境下支持热重载