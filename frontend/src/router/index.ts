// Vue Router 路由配置
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
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
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      redirect: '/dashboard',
      meta: {
        requiresAuth: true,
      },
      children: [
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/views/DashboardView.vue'),
          meta: {
            title: '首页总览',
          },
        },
        {
          path: 'tasks',
          name: 'TaskList',
          component: () => import('@/views/TaskListView.vue'),
          meta: {
            title: '联合任务',
          },
        },
        {
          path: 'tasks/:id',
          name: 'TaskDetail',
          component: () => import('@/views/TaskDetailView.vue'),
          meta: {
            title: '任务详情',
          },
        },
        {
          path: 'nodes',
          name: 'NodeResource',
          component: () => import('@/views/NodeResourceView.vue'),
          meta: {
            title: '节点资源',
          },
        },
        {
          path: 'blockchain',
          name: 'BlockchainGovernance',
          component: () => import('@/views/BlockchainGovernanceView.vue'),
          meta: {
            title: '区块链治理',
          },
        },
      ],
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