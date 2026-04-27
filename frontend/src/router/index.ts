import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'Login', component: () => import('@/pages/Login.vue'), meta: { public: true } },
    { path: '/', redirect: '/ingest' },
    { path: '/ingest', name: 'IngestList', component: () => import('@/pages/IngestBoard/List.vue') },
    { path: '/ingest/new', name: 'IngestNew', component: () => import('@/pages/IngestBoard/Editor.vue') },
    { path: '/ingest/:id', name: 'IngestDetail', component: () => import('@/pages/IngestBoard/Detail.vue') },
    { path: '/wiki', name: 'WikiBrowse', component: () => import('@/pages/WikiBrowse/Index.vue') },
    { path: '/chat', name: 'Chat', component: () => import('@/pages/Chat/Session.vue') },
    { path: '/lint', name: 'LintDashboard', component: () => import('@/pages/LintDashboard/Index.vue') },
    { path: '/schema', name: 'SchemaAdmin', component: () => import('@/pages/SchemaAdmin/Index.vue') },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta.public) return true
  const auth = useAuthStore()
  if (!auth.isLoggedIn) return '/login'
  if (!auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      return '/login'
    }
  }
  return true
})

export default router
