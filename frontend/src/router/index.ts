// Vue Router 路由配置
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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
      path: '/403',
      name: 'Forbidden',
      component: () => import('@/views/ForbiddenView.vue'),
      meta: {
        public: true,
        title: '无权限',
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
            title: '任务管理',
          },
        },
        {
          path: 'tasks/:id/result',
          name: 'TaskResult',
          component: () => import('@/views/TaskResultView.vue'),
          meta: {
            title: '计算结果',
          },
        },
        {
          path: 'tasks/:id/t3-result',
          name: 'T3TaskResult',
          component: () => import('@/views/T3TaskResultView.vue'),
          meta: {
            title: '疫苗效果评估结果',
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
            title: '机构与节点',
          },
        },
        {
          path: 'data-resources',
          name: 'DataResource',
          component: () => import('@/views/DataResourceView.vue'),
          meta: {
            title: '数据资源',
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
        // 新增页面
        {
          path: 'stat-template',
          name: 'StatTemplate',
          component: () => import('@/views/StatTemplateView.vue'),
          meta: {
            title: '统计模板',
          },
        },
        {
          path: 'results',
          name: 'Results',
          component: () => import('@/views/ResultView.vue'),
          meta: {
            title: '结果展示',
          },
        },
        {
          path: 'audit-query',
          name: 'AuditQuery',
          component: () => import('@/views/AuditQueryView.vue'),
          meta: {
            title: '审计查询',
          },
        },
        {
          path: 'group-manage',
          name: 'GroupManage',
          redirect: '/groups',
          meta: {
            title: '群组管理',
          },
        },
        {
          path: 'groups',
          name: 'GroupList',
          component: () => import('@/views/Group/GroupListView.vue'),
          meta: {
            title: '群组管理',
            permission: 'group:read',
          },
        },
        {
          path: 'groups/:id',
          name: 'GroupDetail',
          component: () => import('@/views/Group/GroupDetailView.vue'),
          meta: {
            title: '群组详情',
            permission: 'group:read',
          },
        },
        {
          path: 'base-resource',
          name: 'BaseResource',
          component: () => import('@/views/BaseResource/BaseResourceView.vue'),
          meta: {
            title: '基础资源管理',
            permission: 'agency:read',
          },
        },
        {
          path: 'user-manage',
          name: 'UserManage',
          redirect: '/base-resource?tab=users',
          meta: {
            title: '用户管理',
          },
        },
        {
          path: 'role-auth',
          name: 'RoleAuth',
          component: () => import('@/views/RoleManageView.vue'),
          meta: {
            title: '角色授权',
          },
        },
        {
          path: 'chain-verify',
          name: 'ChainVerify',
          component: () => import('@/views/ChainVerifyView.vue'),
          meta: {
            title: '链上校验',
          },
        },
        {
          path: 'contract-manage',
          name: 'ContractManage',
          component: () => import('@/views/ContractManageView.vue'),
          meta: {
            title: '合约管理',
          },
        },
      ],
    },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const token = localStorage.getItem('access_token')

  // 公开页面直接放行
  if (to.meta.public) {
    // 已登录访问登录页，跳转 dashboard
    if (to.path === '/login' && token) {
      next('/dashboard')
      return
    }
    next()
    return
  }

  // 未登录跳转登录页
  if (!token) {
    next('/login')
    return
  }

  // 已登录但没有用户信息，尝试恢复
  const authStore = useAuthStore()
  if (authStore.isLogin && !authStore.userInfo) {
    try {
      await authStore.fetchCurrentUser()
    } catch (error) {
      authStore.clearAuth()
      next('/login')
      return
    }
  }

  next()
})

export default router
