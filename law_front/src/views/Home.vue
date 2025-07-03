<template>
  <div class="container">
    <div class="title">RAGLEX-中文法律大模型</div>
    <div class="main-content">
      <!-- 左侧历史记录面板 -->
      <div class="left-panel">
        <div class="history-header">
          <div class="new-chat" @click="startNewChat">
            <span class="plus-icon">+</span> 新的对话
          </div>
        </div>
        <div class="history-list">
          <div 
            class="history-item" 
            v-for="conversation in conversationHistory" 
            :key="conversation.id"
            :class="{ active: currentConversationId === conversation.id }"
            @click="loadConversation(conversation.id)"
          >
            <span class="history-icon">💬</span>
            <div class="conversation-info" v-if="editingConversationId !== conversation.id">
              <span class="history-title">{{ conversation.title || '历史对话' }}</span>
              <span class="conversation-time">{{ formatTime(conversation.updated_at) }}</span>
            </div>
            <input 
              v-else
              v-model="editingTitle"
              @blur="saveConversationTitle(conversation.id)"
              @keyup.enter="saveConversationTitle(conversation.id)"
              @click.stop
              class="title-input"
              ref="titleInput"
            />
            <div class="conversation-actions">
              <div class="dropdown" @click.stop>
                <button class="dropdown-btn" @click="toggleDropdown(conversation.id)">⋯</button>
                <div class="dropdown-menu" v-show="activeDropdown === conversation.id">
                  <div class="dropdown-item" @click="startEditTitle(conversation.id, conversation.title)">重命名</div>
                  <div class="dropdown-item delete" @click="deleteConversation(conversation.id)">删除</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 中间内容区 -->
      <div class="center-panel">
        <!-- 聊天对话区域 -->
        <div class="chat-container">
          <div class="chat-header">
            <span>对话</span>
            <span v-if="currentConversationTitle" class="conversation-title">- {{ currentConversationTitle }}</span>
          </div>
          <div class="chat-content">
            <div class="chat-messages" ref="chatMessages">
              <!-- 当前对话的消息 -->
              <template v-for="(message, index) in currentMessages" :key="index">
                <!-- 用户消息 -->
                <div v-if="message.role === 'user'" class="message-wrapper user-message-wrapper">
                  <div class="message user-message">
                    <div class="message-content">{{ message.content }}</div>
                  </div>
                  <div class="avatar user-avatar">👤</div>
                </div>
                <!-- AI回答 -->
                <div v-else class="message-wrapper ai-message-wrapper">
                  <div class="avatar ai-avatar">🤖</div>
                  <div class="message ai-message">
                    <div class="message-content" :class="{ 'typing-animation': message.isTyping }" v-html="renderMarkdown(message.content)"></div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </div>

        <!-- 问题输入区域 -->
        <div class="question-area">
          <div class="question-input">
            <input
              type="text"
              v-model="question"
              placeholder="请输入问题"
              class="input-box"
              @keyup.enter="sendQuestion"
              :disabled="isLoading"
            />
            <div class="button-group">
              <div class="send-button" @click="sendQuestion" :class="{ disabled: isLoading }">
                <span class="send-icon">📨</span> {{ isLoading ? '发送中...' : '发送' }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧配置面板 -->
      <div class="right-panel">
        <div class="config-section">
          <h3>模型配置</h3>
          <div class="config-item">
            <label>嵌入模型:</label>
            <select v-model="embeddingModel">
              <option value="text2vec-base">text2vec-base</option>
            </select>
          </div>
          <div class="config-item">
            <label>大语言模型:</label>
            <select v-model="largeLanguageModel">
              <option value="ChatGLM-6B">ChatGLM-6B</option>
            </select>
          </div>
          <div class="config-item">
            <label>Top K:</label>
            <input type="number" v-model="topK" min="1" max="10" />
          </div>
          <div class="config-item">
            <label>网络搜索:</label>
            <select v-model="webSearch">
              <option value="notUse">不使用</option>
              <option value="use">使用</option>
            </select>
          </div>
          <div class="config-item">
            <label>模式:</label>
            <select v-model="mode">
              <option value="shared_knowledge">使用公有知识库</option>
              <option value="private_knowledge">使用私有知识库</option>
              <option value="entire_knowledge">使用整个知识库</option>
              <option value="none_knowledge">不使用知识库</option>
            </select>
          </div>
        </div>
        
        <div class="action-section">
          <button class="action-button" @click="importHistoricalCases">
            📁 导入历史案例
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { 
  getConversations, 
  createConversation, 
  getMessages, 
  deleteConversation as deleteConversationAPI,
  updateConversation,
  sendQuestionWithConversation 
} from '../api/conversations'
import { marked } from 'marked'

export default {
  name: 'HomePage',
  data() {
    return {
      question: '',
      embeddingModel: 'text2vec-base',
      largeLanguageModel: 'ChatGLM-6B',
      topK: 3,
      webSearch: 'notUse',
      mode: 'none_knowledge',
      knowledge: [],
      
      // 对话相关数据
      conversationHistory: [], // 所有对话历史
      currentMessages: [], // 当前对话的消息
      currentConversationId: null, // 当前对话ID
      currentConversationTitle: '', // 当前对话标题
      isLoading: false, // 发送状态
      
      // 编辑相关状态
      editingConversationId: null, // 正在编辑的对话ID
      editingTitle: '', // 编辑中的标题
      activeDropdown: null // 当前激活的下拉菜单
    }
  },
  
  async mounted() {
    // 检查用户登录状态
    const token = localStorage.getItem('access_token')
    if (!token) {
      // 如果没有token，跳转到登录页
      this.$router.push('/login')
      return
    }
    
    // 页面加载时获取对话历史
    await this.loadConversationHistory()
    
    // 显示欢迎消息
    this.showWelcomeMessage()
    
    // 添加点击外部关闭下拉菜单的事件监听
    document.addEventListener('click', this.closeDropdown)
  },
  
  beforeDestroy() {
    // 清理事件监听器
    document.removeEventListener('click', this.closeDropdown)
  },
  
  methods: {
    /**
     * 关闭下拉菜单
     */
    closeDropdown() {
      this.activeDropdown = null
    },
    
    /**
     * 渲染Markdown内容
     */
    renderMarkdown(content) {
      if (!content) return ''
      
      // 配置marked选项
      marked.setOptions({
        breaks: true, // 支持换行
        gfm: true, // 支持GitHub风格的Markdown
        sanitize: false // 允许HTML（注意：在生产环境中可能需要更严格的安全设置）
      })
      
      return marked(content)
    },
    
    /**
     * 加载对话历史列表
     */
    async loadConversationHistory() {
      try {
        const response = await getConversations()
        if (response.success) {
          // 按更新时间排序，最新的在前面
          this.conversationHistory = response.data.sort((a, b) => {
            return new Date(b.updated_at) - new Date(a.updated_at)
          })
        }
      } catch (error) {
        console.error('加载对话历史失败:', error)
      }
    },
    
    /**
     * 显示欢迎消息
     */
    showWelcomeMessage() {
      if (this.currentMessages.length === 0) {
        this.currentMessages = [{
          role: 'assistant',
          content: '您好，今天有什么可以帮到您的？',
          isTyping: false
        }]
      }
    },
    
    /**
     * 开始新对话
     */
    async startNewChat() {
      try {
        // 清空当前对话
        this.currentMessages = []
        this.currentConversationId = null
        this.currentConversationTitle = ''
        this.question = ''
        
        // 显示欢迎消息
        this.showWelcomeMessage()
        
        console.log('新对话创建完成')
      } catch (error) {
        console.error('开始新对话失败:', error)
      }
    },
    
    /**
     * 保存当前对话到历史
     */
    async saveCurrentConversation() {
      console.log('开始保存对话，消息数量:', this.currentMessages.length)
      if (this.currentMessages.length === 0) return
      
      try {
        // 生成对话标题（使用第一个用户消息的前20个字符）
        const firstUserMessage = this.currentMessages.find(msg => msg.role === 'user')
        const title = firstUserMessage ? 
          firstUserMessage.content.substring(0, 20) + (firstUserMessage.content.length > 20 ? '...' : '') :
          '新对话'
        
        console.log('生成的对话标题:', title)
        
        // 创建新对话
        console.log('调用createConversation API')
        const response = await createConversation(title)
        console.log('createConversation响应:', response)
        
        if (response.success) {
          this.currentConversationId = response.data.id
          this.currentConversationTitle = response.data.title
          
          console.log('对话创建成功，ID:', this.currentConversationId)
          
          // 重新加载对话历史
          console.log('重新加载对话历史')
          await this.loadConversationHistory()
        } else {
          console.error('创建对话失败:', response)
        }
      } catch (error) {
        console.error('保存对话失败:', error)
      }
    },
    
    /**
     * 加载指定对话
     */
    async loadConversation(conversationId) {
      try {
        const response = await getMessages(conversationId)
        
        if (response.success) {
          this.currentConversationId = conversationId
          this.currentConversationTitle = response.data.conversation.title
          
          this.currentMessages = response.data.messages.map(msg => ({
            role: msg.role,
            content: msg.content,
            isTyping: false
          }))
          
          // 滚动到底部
          this.$nextTick(() => {
            this.scrollToBottom()
          })
        }
      } catch (error) {
        console.error('加载对话失败:', error)
      }
    },
    
    /**
     * 删除对话
     */
    async deleteConversation(conversationId) {
      if (!confirm('确定要删除这个对话吗？')) return
      
      // 关闭下拉菜单
      this.activeDropdown = null
      
      try {
        const response = await deleteConversationAPI(conversationId)
        if (response.success) {
          // 如果删除的是当前对话，清空当前对话
          if (this.currentConversationId === conversationId) {
            this.currentMessages = []
            this.currentConversationId = null
            this.currentConversationTitle = ''
          }
          
          // 重新加载对话历史
          await this.loadConversationHistory()
        }
      } catch (error) {
        console.error('删除对话失败:', error)
      }
    },
    
    /**
     * 切换下拉菜单
     */
    toggleDropdown(conversationId) {
      this.activeDropdown = this.activeDropdown === conversationId ? null : conversationId
    },
    
    /**
     * 开始编辑标题
     */
    startEditTitle(conversationId, currentTitle) {
      this.editingConversationId = conversationId
      this.editingTitle = currentTitle || '历史对话'
      this.activeDropdown = null
      
      // 下一帧聚焦输入框
      this.$nextTick(() => {
        const input = this.$refs.titleInput
        if (input) {
          input.focus()
          input.select()
        }
      })
    },
    
    /**
     * 保存对话标题
     */
    async saveConversationTitle(conversationId) {
      if (!this.editingTitle.trim()) {
        this.editingTitle = '历史对话'
      }
      
      try {
        // 调用API更新对话标题
        const response = await updateConversation(conversationId, this.editingTitle)
        if (response.success) {
          // 更新本地数据
          const conversation = this.conversationHistory.find(c => c.id === conversationId)
          if (conversation) {
            conversation.title = this.editingTitle
          }
          
          // 如果是当前对话，也更新当前对话标题
          if (this.currentConversationId === conversationId) {
            this.currentConversationTitle = this.editingTitle
          }
          
          console.log('标题已更新为:', this.editingTitle)
        } else {
          console.error('更新标题失败:', response.message)
        }
      } catch (error) {
        console.error('保存标题失败:', error)
      } finally {
        this.editingConversationId = null
        this.editingTitle = ''
      }
    },
    
    /**
     * 发送问题
     */
    async sendQuestion() {
      if (!this.question.trim() || this.isLoading) return
      
      const userQuestion = this.question.trim()
      this.question = ''
      this.isLoading = true
      
      try {
        // 添加用户消息到当前对话
        this.currentMessages.push({
          role: 'user',
          content: userQuestion,
          isTyping: false
        })
        
        // 添加AI回复占位符
        this.currentMessages.push({
          role: 'assistant',
          content: '正在思考中...',
          isTyping: true
        })
        
        // 滚动到底部
        this.$nextTick(() => {
          this.scrollToBottom()
        })
        
        // 如果没有当前对话ID，先创建对话
        if (!this.currentConversationId) {
          const title = userQuestion.substring(0, 20) + (userQuestion.length > 20 ? '...' : '')
          const createResponse = await createConversation(title)
          if (createResponse.success) {
            this.currentConversationId = createResponse.data.id
            this.currentConversationTitle = createResponse.data.title
            await this.loadConversationHistory()
          }
        }
        
        // 准备配置参数
        const config = {
          embeddingModel: this.embeddingModel,
          largeLanguageModel: this.largeLanguageModel,
          topK: this.topK,
          webSearch: this.webSearch,
          mode: this.mode
        }
        
        // 发送问题到后端
        const response = await sendQuestionWithConversation(userQuestion, this.currentConversationId, config)
        
        if (response.success && response.data && response.data.answer) {
          // 更新AI回复
          const lastMessage = this.currentMessages[this.currentMessages.length - 1]
          lastMessage.content = response.data.answer
          lastMessage.isTyping = false
        } else {
          // 处理错误
          const lastMessage = this.currentMessages[this.currentMessages.length - 1]
          lastMessage.content = '抱歉，发生了错误，请稍后重试。'
          lastMessage.isTyping = false
        }
        
      } catch (error) {
        console.error('发送问题失败:', error)
        // 更新错误信息
        const lastMessage = this.currentMessages[this.currentMessages.length - 1]
        lastMessage.content = '抱歉，发生了错误，请稍后重试。'
        lastMessage.isTyping = false
      } finally {
        this.isLoading = false
        // 滚动到底部
        this.$nextTick(() => {
          this.scrollToBottom()
        })
      }
    },
    
    /**
     * 滚动到聊天底部
     */
    scrollToBottom() {
      const chatMessages = this.$refs.chatMessages
      if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight
      }
    },
    
    /**
     * 格式化时间显示
     */
    formatTime(timeString) {
      if (!timeString) return ''
      
      const now = new Date()
      const time = new Date(timeString)
      const diffMs = now - time
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
      
      if (diffDays === 0) {
        // 今天，显示时间
        return time.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      } else if (diffDays === 1) {
        // 昨天
        return '昨天'
      } else if (diffDays < 7) {
        // 一周内，显示星期几
        const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
        return weekdays[time.getDay()]
      } else if (diffDays < 365) {
        // 一年内，显示月日
        return time.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
      } else {
        // 超过一年，显示年月日
        return time.toLocaleDateString('zh-CN', { year: 'numeric', month: 'short', day: 'numeric' })
      }
    },
    
    /**
     * 导入历史案例
     */
    importHistoricalCases() {
      this.$router.push('/case-management')
    }
  }
}
</script>

<style scoped>
.container {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #f5f7fa;
}

.title {
  text-align: center;
  padding: 20px;
  font-size: 24px;
  font-weight: bold;
  color: #333;
}

.main-content {
  flex: 1;
  display: flex;
  gap: 20px;
  padding: 0 20px 20px;
}

.left-panel {
  width: 250px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
}

.history-header {
  padding: 15px;
  border-bottom: 1px solid #eee;
}

.new-chat {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 15px;
  background-color: #007bff;
  color: white;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.new-chat:hover {
  background-color: #0056b3;
}

.plus-icon {
  font-size: 16px;
  font-weight: bold;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  margin-bottom: 5px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
  position: relative;
}

.history-item:hover {
  background-color: #f8f9fa;
}

.history-item.active {
  background-color: #e3f2fd;
  border-left: 3px solid #007bff;
}

.history-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.conversation-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-right: 30px; /* 为三个小点按钮留出空间 */
  min-width: 0; /* 允许flex子元素收缩 */
}

.history-title {
  font-size: 14px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.2;
  max-width: 100%; /* 确保不超出父容器 */
}

.conversation-time {
  font-size: 11px;
  color: #888;
  line-height: 1;
}

.conversation-actions {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  display: none;
  z-index: 10;
}

.history-item:hover .conversation-actions {
  display: block;
}

.dropdown {
  position: relative;
}

.dropdown-btn {
  width: 20px;
  height: 20px;
  border: none;
  background-color: #6c757d;
  color: white;
  border-radius: 50%;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.dropdown-btn:hover {
  background-color: #5a6268;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  background-color: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 1001; /* 确保下拉菜单在最上层 */
  min-width: 80px;
  margin-top: 2px;
}

.dropdown-item {
  padding: 8px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: background-color 0.2s;
  white-space: nowrap;
}

.dropdown-item:hover {
  background-color: #f8f9fa;
}

.dropdown-item.delete {
  color: #dc3545;
}

.dropdown-item.delete:hover {
  background-color: #f8d7da;
}

.title-input {
  flex: 1;
  border: 1px solid #007bff;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 14px;
  outline: none;
  background-color: white;
}

.center-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-header {
  padding: 15px 20px;
  border-bottom: 1px solid #eee;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.conversation-title {
  color: #666;
  font-weight: normal;
  font-size: 14px;
}

.chat-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0; /* 确保flex子元素可以收缩 */
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  max-height: calc(100vh - 300px); /* 限制最大高度，为标题、输入框等预留空间 */
  min-height: 400px; /* 设置最小高度 */
}

.message-wrapper {
  display: flex;
  margin-bottom: 20px;
  align-items: flex-start;
}

.user-message-wrapper {
  justify-content: flex-end;
}

.ai-message-wrapper {
  justify-content: flex-start;
}

.message {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  word-wrap: break-word;
}

.user-message {
  background-color: #007bff;
  color: white;
  margin-left: 10px;
}

.ai-message {
  background-color: #f8f9fa;
  color: #333;
  margin-right: 10px;
  border: 1px solid #e9ecef;
}

.message-content {
  line-height: 1.5;
}

/* Markdown样式 */
.message-content h1,
.message-content h2,
.message-content h3,
.message-content h4,
.message-content h5,
.message-content h6 {
  margin: 0.5em 0;
  font-weight: bold;
}

.message-content h1 { font-size: 1.5em; }
.message-content h2 { font-size: 1.3em; }
.message-content h3 { font-size: 1.1em; }

.message-content p {
  margin: 0.5em 0;
}

.message-content ul,
.message-content ol {
  margin: 0.5em 0;
  padding-left: 1.5em;
}

.message-content li {
  margin: 0.2em 0;
}

.message-content strong {
  font-weight: bold;
}

.message-content em {
  font-style: italic;
}

.message-content code {
  background-color: #f1f3f4;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}

.message-content pre {
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  padding: 10px;
  overflow-x: auto;
  margin: 0.5em 0;
}

.message-content pre code {
  background-color: transparent;
  padding: 0;
  border-radius: 0;
}

.message-content blockquote {
  border-left: 4px solid #007bff;
  margin: 0.5em 0;
  padding-left: 1em;
  color: #666;
}

.message-content table {
  border-collapse: collapse;
  width: 100%;
  margin: 0.5em 0;
}

.message-content th,
.message-content td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

.message-content th {
  background-color: #f2f2f2;
  font-weight: bold;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.user-avatar {
  background-color: #007bff;
  color: white;
}

.ai-avatar {
  background-color: #28a745;
  color: white;
}

.typing-animation {
  position: relative;
}

.typing-animation::after {
  content: '|';
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.question-area {
  padding: 20px;
  border-top: 1px solid #eee;
}

.question-input {
  display: flex;
  gap: 10px;
  align-items: center;
}

.input-box {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.input-box:focus {
  border-color: #007bff;
}

.input-box:disabled {
  background-color: #f8f9fa;
  cursor: not-allowed;
}

.button-group {
  display: flex;
  gap: 10px;
}

.send-button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 20px;
  background-color: #007bff;
  color: white;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
  font-size: 14px;
}

.send-button:hover:not(.disabled) {
  background-color: #0056b3;
}

.send-button.disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.send-icon {
  font-size: 14px;
}

.right-panel {
  width: 300px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.config-section h3 {
  margin: 0 0 15px 0;
  color: #333;
  font-size: 16px;
}

.config-item {
  margin-bottom: 15px;
}

.config-item label {
  display: block;
  margin-bottom: 5px;
  font-size: 14px;
  color: #555;
}

.config-item select,
.config-item input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.action-section {
  margin-top: auto;
}

.action-button {
  width: 100%;
  padding: 12px;
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s;
}

.action-button:hover {
  background-color: #218838;
}
</style>
  