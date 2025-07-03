// API配置文件
const API_BASE_URL = 'http://localhost:5000'

// API端点配置
export const API_ENDPOINTS = {
  // 认证相关
  AUTH: {
    LOGIN: `${API_BASE_URL}/api/auth/login`,
    REGISTER: `${API_BASE_URL}/api/auth/register`,
    PROFILE: `${API_BASE_URL}/api/auth/profile`
  },
  
  // 查询相关
  QUERY: `${API_BASE_URL}/api/query`,
  
  // 文件相关
  FILE: {
    UPLOAD: `${API_BASE_URL}/api/files/upload`,
    PREVIEW: (fileName) => `${API_BASE_URL}/api/preview/${fileName}`,
    DELETE: (fileName) => `${API_BASE_URL}/api/files/${fileName}`
  },
  
  // 健康检查
  HEALTH: `${API_BASE_URL}/health`
}

// 获取认证headers
export function getAuthHeaders() {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` })
  }
}

// 获取上传headers（不包含Content-Type，让浏览器自动设置）
export function getUploadHeaders() {
  const token = localStorage.getItem('access_token')
  return token ? { 'Authorization': `Bearer ${token}` } : {}
}

// 通用API请求函数
export async function apiRequest(url, options = {}) {
  const defaultOptions = {
    headers: getAuthHeaders(),
    ...options
  }
  
  // 如果有data参数，将其序列化为JSON并设置为请求体
  if (options.data) {
    defaultOptions.body = JSON.stringify(options.data)
  }
  
  try {
    const response = await fetch(url, defaultOptions)
    
    // 如果是401错误，可能是token过期，跳转到登录页
    if (response.status === 401) {
      localStorage.removeItem('user')
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
      return null
    }
    
    // 解析JSON响应
    const data = await response.json()
    return data
  } catch (error) {
    console.error('API请求失败:', error)
    throw error
  }
}

export default {
  API_ENDPOINTS,
  getAuthHeaders,
  getUploadHeaders,
  apiRequest
}