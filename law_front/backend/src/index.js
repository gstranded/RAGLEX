require('dotenv').config();
const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();

// 中间件配置
app.use(cors());
app.use(bodyParser.json());

// 路由配置
app.post('/api/query', async (req, res) => {
  try {
    const { question, mode, knowledge } = req.body;
    // TODO: 实现与AI模型的交互逻辑
    const mockResponse = {
      answer: '这是一个模拟的回答。实际实现时，这里将连接到AI模型进行问答。',
      references: [
        { content: '参考资料1', source: '法律条文' },
        { content: '参考资料2', source: '历史案例' }
      ]
    };
    res.json(mockResponse);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 知识库管理接口已移除（使用外部服务器）

// 历史记录接口
app.get('/api/history', async (req, res) => {
  try {
    // TODO: 实现历史记录查询逻辑
    const mockHistory = [
      { id: 1, question: '示例问题1', answer: '示例回答1', timestamp: new Date() },
      { id: 2, question: '示例问题2', answer: '示例回答2', timestamp: new Date() }
    ];
    res.json(mockHistory);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`服务器运行在端口 ${PORT}`);
});