import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
// 案件文档管理页面
import CaseManagement from '../views/CaseManagement.vue'
import Login from '../views/Login.vue'

// 路由守卫函数
function requireAuth(to, from, next) {
  const token = localStorage.getItem('access_token')
  if (token) {
    next()
  } else {
    next('/login')
  }
}

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/',
    name: 'Home',
    component: Home,
    beforeEnter: requireAuth
  },
  {
    path: '/case-management',
    name: 'CaseManagement',
    // 案件文档管理页面
    component: CaseManagement,
    beforeEnter: requireAuth
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
