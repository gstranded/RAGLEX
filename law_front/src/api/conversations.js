// 对话相关的API调用
import { apiRequest } from '../utils/api.js'

// API端点
const CONVERSATION_ENDPOINTS = {
  LIST: 'http://localhost:5000/api/conversations/',
  CREATE: 'http://localhost:5000/api/conversations/',
  MESSAGES: (id) => `http://localhost:5000/api/conversations/${id}/messages`,
  DELETE: (id) => `http://localhost:5000/api/conversations/${id}`,
  UPDATE: (id) => `http://localhost:5000/api/conversations/${id}`
}

/**
 * 获取用户的所有对话历史
 * @param {number} userId - 用户ID
 * @returns {Promise} API响应
 */
export const getConversations = (userId = 1) => {
  return apiRequest(CONVERSATION_ENDPOINTS.LIST, {
    method: 'GET',
    params: { user_id: userId }
  })
}

/**
 * 创建新对话
 * @param {string} title - 对话标题
 * @param {number} userId - 用户ID
 * @returns {Promise} API响应
 */
export const createConversation = (title, userId = 1) => {
  return apiRequest(CONVERSATION_ENDPOINTS.CREATE, {
    method: 'POST',
    data: {
      title,
      user_id: userId
    }
  })
}

/**
 * 获取指定对话的所有消息
 * @param {number} conversationId - 对话ID
 * @returns {Promise} API响应
 */
export const getMessages = (conversationId) => {
  return apiRequest(CONVERSATION_ENDPOINTS.MESSAGES(conversationId), {
    method: 'GET'
  })
}

/**
 * 向指定对话添加消息
 * @param {number} conversationId - 对话ID
 * @param {string} role - 消息角色 (user/assistant)
 * @param {string} content - 消息内容
 * @returns {Promise} API响应
 */
export const addMessage = (conversationId, role, content) => {
  return apiRequest(CONVERSATION_ENDPOINTS.MESSAGES(conversationId), {
    method: 'POST',
    data: {
      role,
      content
    }
  })
}

/**
 * 删除指定对话
 * @param {number} conversationId - 对话ID
 * @returns {Promise} API响应
 */
export const deleteConversation = (conversationId) => {
  return apiRequest(CONVERSATION_ENDPOINTS.DELETE(conversationId), {
    method: 'DELETE'
  })
}

/**
 * 更新对话标题
 * @param {number} conversationId - 对话ID
 * @param {string} title - 新标题
 * @returns {Promise} API响应
 */
export const updateConversation = (conversationId, title) => {
  return apiRequest(CONVERSATION_ENDPOINTS.UPDATE(conversationId), {
    method: 'PUT',
    data: {
      title
    }
  })
}

/**
 * 发送问题到知识库查询（带对话ID）
 * @param {string} question - 问题内容
 * @param {number} conversationId - 对话ID（可选）
 * @param {Object} config - 模型配置参数（可选）
 * @returns {Promise} API响应
 */
export const sendQuestionWithConversation = (question, conversationId = null, config = {}) => {
  const data = { question }
  if (conversationId) {
    data.conversation_id = conversationId
  }
  
  // 添加配置参数
  if (config.embeddingModel) {
    data.embedding_model = config.embeddingModel
  }
  if (config.largeLanguageModel) {
    data.large_language_model = config.largeLanguageModel
  }
  if (config.topK) {
    data.top_k = config.topK
  }
  if (config.webSearch) {
    data.web_search = config.webSearch
  }
  if (config.mode) {
    data.mode = config.mode
  }
  
  return apiRequest('http://localhost:5000/api/query', {
    method: 'POST',
    data
  })
}