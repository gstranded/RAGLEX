<template>
  <div id="app">
    <div class="header" v-if="!isLoginPage">
      <h1 class="clickable-title" @click="goToHome">RAGLEX</h1>
      <div class="user-info" v-if="user">
        <el-dropdown @command="handleCommand">
          <span class="user-name">
            {{ user.full_name || user.username }}
            <el-icon class="el-icon--right"><arrow-down /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人资料</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
    <router-view />
  </div>
</template>

<script>
import { ElMessage } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'

export default {
  name: 'App',
  components: {
    ArrowDown
  },
  data() {
    return {
      user: null
    }
  },
  computed: {
    isLoginPage() {
      return this.$route.path === '/login'
    }
  },
  mounted() {
    this.loadUserInfo()
    // 监听路由变化
    this.$watch('$route', () => {
      this.loadUserInfo()
    })
  },
  methods: {
    loadUserInfo() {
      const userStr = localStorage.getItem('user')
      if (userStr) {
        try {
          this.user = JSON.parse(userStr)
        } catch (error) {
          console.error('解析用户信息失败:', error)
          this.user = null
        }
      } else {
        this.user = null
      }
    },
    
    handleCommand(command) {
      switch (command) {
        case 'profile':
          ElMessage.info('个人资料功能开发中...')
          break
        case 'logout':
          this.logout()
          break
      }
    },
    
    logout() {
      // 清除本地存储的用户信息
      localStorage.removeItem('user')
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      
      this.user = null
      ElMessage.success('已退出登录')
      
      // 跳转到登录页
      this.$router.push('/login')
    },
    
    // 保留方法，以防其他地方调用
    importHistoricalCases() {
      this.$message.success('开始导入历史案件');
    },
    
    goToHome() {
      // 如果当前不在首页，则跳转到首页
      if (this.$route.path !== '/') {
        this.$router.push('/')
      } else {
        // 如果已经在首页，可以刷新页面或重置状态
        // 这里可以触发首页的重置方法
        this.$nextTick(() => {
          // 通过事件总线或其他方式通知首页组件重置状态
          window.location.reload()
        })
      }
    }
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  margin: 0;
  padding: 0;
  height: 100vh;
}

.header {
  background-color: #f5f7fa;
  padding: 15px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e4e7ed;
}

.header h1 {
  font-size: 20px;
  margin: 0;
}

.clickable-title {
  cursor: pointer;
  transition: color 0.3s ease;
}

.clickable-title:hover {
  color: #409eff;
}

.user-info {
  display: flex;
  align-items: center;
}

.user-name {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 4px;
  transition: background-color 0.3s;
  color: #333;
  font-weight: 500;
}

.user-name:hover {
  background-color: #e4e7ed;
}

.actions {
  display: flex;
  gap: 10px;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: Arial, sans-serif;
}
</style>
