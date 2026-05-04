// Vue Router 路由配置
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      meta: {
        public: true,
        title: '登录',
      },
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: {
        title: '首页总览',
      },
    },
      {
  path: '/tasks',
  name: 'TaskList',
  component: () => import('@/views/TaskListView.vue'),
  meta: {
    requiresAuth: true,
    title: '联合统计任务',
  },
},
{
  path: '/tasks/:id',
  name: 'TaskDetail',
  component: () => import('@/views/TaskDetailView.vue'),
  meta: {
    requiresAuth: true,
    title: '任务详情',
  },
},
  ],
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('access_token')

  if (to.meta.public) {
    next()
    return
  }

  if (!token) {
    next('/login')
    return
  }

  next()
})

export default router