<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <h2>{{ isLogin ? '登录' : '注册' }}</h2>
      </div>
      
      <el-form 
        :model="form" 
        :rules="rules" 
        ref="loginForm" 
        class="login-form"
        @submit.prevent="handleSubmit"
      >
        <!-- 注册时显示用户名 -->
        <el-form-item prop="username" v-if="!isLogin">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        
        <!-- 登录时显示用户名/邮箱 -->
        <el-form-item prop="usernameOrEmail" v-if="isLogin">
          <el-input
            v-model="form.usernameOrEmail"
            placeholder="请输入用户名或邮箱"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        
        <!-- 注册时显示邮箱 -->
        <el-form-item prop="email" v-if="!isLogin">
          <el-input
            v-model="form.email"
            placeholder="请输入邮箱"
            prefix-icon="Message"
            size="large"
            type="email"
          />
        </el-form-item>
        
        <!-- 注册时显示姓名 -->
        <el-form-item prop="fullName" v-if="!isLogin">
          <el-input
            v-model="form.fullName"
            placeholder="请输入姓名（可选）"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        
        <!-- 注册时显示确认密码 -->
        <el-form-item prop="confirmPassword" v-if="!isLogin">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="请确认密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            size="large" 
            class="login-btn"
            :loading="loading"
            @click="handleSubmit"
          >
            {{ isLogin ? '登录' : '注册' }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="switch-mode">
        <span>{{ isLogin ? '还没有账号？' : '已有账号？' }}</span>
        <el-button type="text" @click="toggleMode">
          {{ isLogin ? '立即注册' : '立即登录' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus'
import { API_ENDPOINTS, apiRequest } from '../utils/api.js'

export default {
  name: 'Login',
  data() {
    // 确认密码验证
    const validateConfirmPassword = (rule, value, callback) => {
      if (value === '') {
        callback(new Error('请再次输入密码'))
      } else if (value !== this.form.password) {
        callback(new Error('两次输入密码不一致'))
      } else {
        callback()
      }
    }
    
    return {
      isLogin: true, // 默认显示登录界面
      loading: false,
      form: {
        username: '',
        usernameOrEmail: '',
        email: '',
        fullName: '',
        password: '',
        confirmPassword: ''
      },
      rules: {
        username: [
          { required: true, message: '请输入用户名', trigger: 'blur' },
          { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
        ],
        usernameOrEmail: [
          { required: true, message: '请输入用户名或邮箱', trigger: 'blur' }
        ],
        email: [
          { required: true, message: '请输入邮箱地址', trigger: 'blur' },
          { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
        ],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur' },
          { min: 6, message: '密码长度不能少于 6 位', trigger: 'blur' }
        ],
        confirmPassword: [
          { required: true, validator: validateConfirmPassword, trigger: 'blur' }
        ]
      }
    }
  },
  methods: {
    toggleMode() {
      this.isLogin = !this.isLogin
      this.resetForm()
    },
    
    resetForm() {
      this.form = {
        username: '',
        usernameOrEmail: '',
        email: '',
        fullName: '',
        password: '',
        confirmPassword: ''
      }
      if (this.$refs.loginForm) {
        this.$refs.loginForm.clearValidate()
      }
    },
    
    async handleSubmit() {
      try {
        await this.$refs.loginForm.validate()
        
        if (this.isLogin) {
          await this.login()
        } else {
          await this.register()
        }
      } catch (error) {
        console.log('表单验证失败:', error)
      }
    },
    
    async login() {
      this.loading = true
      try {
        const data = await apiRequest(API_ENDPOINTS.AUTH.LOGIN, {
          method: 'POST',
          data: {
            username: this.form.usernameOrEmail,
            password: this.form.password
          }
        })
        
        if (data && data.success) {
          // 保存用户信息和token到localStorage
          localStorage.setItem('user', JSON.stringify(data.data.user))
          localStorage.setItem('access_token', data.data.access_token)
          localStorage.setItem('refresh_token', data.data.refresh_token)
          
          ElMessage.success('登录成功！')
          
          // 跳转到首页
          this.$router.push('/')
        } else {
          ElMessage.error(data?.message || '登录失败')
        }
      } catch (error) {
        console.error('登录错误:', error)
        ElMessage.error('网络错误，请稍后重试')
      } finally {
        this.loading = false
      }
    },
    
    async register() {
      this.loading = true
      try {
        const data = await apiRequest(API_ENDPOINTS.AUTH.REGISTER, {
          method: 'POST',
          data: {
            username: this.form.username,
            email: this.form.email,
            password: this.form.password,
            full_name: this.form.fullName
          }
        })
        
        if (data && data.success) {
          ElMessage.success('注册成功！请登录')
          this.isLogin = true
          this.resetForm()
        } else {
          ElMessage.error(data?.message || '注册失败')
        }
      } catch (error) {
        console.error('注册错误:', error)
        ElMessage.error('网络错误，请稍后重试')
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-box {
  background: white;
  border-radius: 10px;
  padding: 40px;
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h2 {
  color: #333;
  font-size: 28px;
  font-weight: 600;
}

.login-form {
  width: 100%;
}

.login-btn {
  width: 100%;
  height: 45px;
  font-size: 16px;
  font-weight: 600;
}

.switch-mode {
  text-align: center;
  margin-top: 20px;
  color: #666;
}

.switch-mode span {
  margin-right: 5px;
}

:deep(.el-form-item) {
  margin-bottom: 20px;
}

:deep(.el-input__wrapper) {
  border-radius: 8px;
}

:deep(.el-button--text) {
  color: #667eea;
  font-weight: 600;
}

:deep(.el-button--text:hover) {
  color: #764ba2;
}
</style>