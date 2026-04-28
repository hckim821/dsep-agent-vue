import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'Login', component: () => import('@/pages/Login.vue'), meta: { public: true } },
    { path: '/', redirect: '/home' },

    // 새 사용자 친화 경로
    { path: '/home', name: 'Home', component: () => import('@/pages/Home/Index.vue') },
    { path: '/library', name: 'Library', component: () => import('@/pages/WikiBrowse/Index.vue') },
    { path: '/ask', name: 'Ask', component: () => import('@/pages/Chat/Session.vue') },
    { path: '/uploads', name: 'Uploads', component: () => import('@/pages/IngestBoard/List.vue') },
    { path: '/upload', name: 'UploadNew', component: () => import('@/pages/IngestBoard/Editor.vue') },
    { path: '/uploads/:id', name: 'UploadDetail', component: () => import('@/pages/IngestBoard/Detail.vue') },
    { path: '/quality', name: 'Quality', component: () => import('@/pages/LintDashboard/Index.vue') },
    { path: '/rules', name: 'Rules', component: () => import('@/pages/SchemaAdmin/Index.vue') },

    // 구 경로 호환 (북마크 깨짐 방지) — 모두 새 경로로 redirect
    { path: '/ingest', redirect: '/uploads' },
    { path: '/ingest/new', redirect: '/upload' },
    { path: '/ingest/:id', redirect: (to: any) => `/uploads/${to.params.id}` },
    { path: '/wiki', redirect: (to: any) => ({ path: '/library', query: to.query }) },
    { path: '/chat', redirect: '/ask' },
    { path: '/lint', redirect: '/quality' },
    { path: '/schema', redirect: '/rules' },
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
