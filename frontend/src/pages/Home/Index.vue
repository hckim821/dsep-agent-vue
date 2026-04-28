<template>
  <AppLayout>
    <!-- 환영 배너 -->
    <div class="rounded-2xl p-6 mb-6 text-white relative overflow-hidden" style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 60%, #db2777 100%);">
      <div class="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -mt-20 -mr-20"></div>
      <div class="relative z-10">
        <h2 class="text-2xl font-bold tracking-tight mb-2">
          안녕하세요, {{ authStore.user?.display_name }}님 👋
        </h2>
        <p class="text-white/90 text-sm mb-5 max-w-2xl">
          여기는 AI가 함께 가꾸는 우리 팀의 지식 허브입니다. 자료를 올리면 AI가 정리해서 지식베이스에 통합하고,
          질문하면 그 지식을 바탕으로 답변합니다.
        </p>
        <div class="flex flex-wrap gap-3">
          <router-link to="/upload">
            <a-button type="primary" size="large" class="!bg-white !text-indigo-700 !border-white hover:!bg-gray-50">
              <PlusOutlined /> 자료 올리기
            </a-button>
          </router-link>
          <router-link to="/ask">
            <a-button size="large" ghost>
              <MessageOutlined /> AI에게 질문하기
            </a-button>
          </router-link>
          <router-link to="/library">
            <a-button size="large" ghost>
              <BookOutlined /> 지식 둘러보기
            </a-button>
          </router-link>
        </div>
      </div>
    </div>

    <!-- 통계 4개 -->
    <a-row :gutter="16" class="mb-6">
      <a-col :xs="12" :md="6">
        <div class="stat-card bg-white rounded-xl p-5 border" style="border-color: var(--color-border);">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs text-gray-500">지식 페이지</span>
            <BookOutlined class="text-indigo-300 text-xl" />
          </div>
          <div class="text-3xl font-bold text-indigo-600">{{ stats.pages }}</div>
          <div class="text-xs text-gray-400 mt-1">정리된 페이지 수</div>
        </div>
      </a-col>
      <a-col :xs="12" :md="6">
        <div class="stat-card bg-white rounded-xl p-5 border" style="border-color: var(--color-border);">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs text-gray-500">올린 자료</span>
            <InboxOutlined class="text-purple-300 text-xl" />
          </div>
          <div class="text-3xl font-bold text-purple-600">{{ stats.uploads }}</div>
          <div class="text-xs text-gray-400 mt-1">전체 등록 자료</div>
        </div>
      </a-col>
      <a-col :xs="12" :md="6">
        <div class="stat-card bg-white rounded-xl p-5 border" style="border-color: var(--color-border);">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs text-gray-500">정리 중</span>
            <SyncOutlined class="text-blue-300 text-xl" :spin="stats.processing > 0" />
          </div>
          <div class="text-3xl font-bold" :class="stats.processing > 0 ? 'text-blue-600' : 'text-gray-300'">{{ stats.processing }}</div>
          <div class="text-xs text-gray-400 mt-1">AI 처리 진행 중</div>
        </div>
      </a-col>
      <a-col :xs="12" :md="6">
        <div class="stat-card bg-white rounded-xl p-5 border cursor-pointer" style="border-color: var(--color-border);" @click="$router.push('/quality')">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs text-gray-500">점검 필요</span>
            <SafetyCertificateOutlined class="text-orange-300 text-xl" />
          </div>
          <div class="text-3xl font-bold" :class="stats.issues > 0 ? 'text-orange-600' : 'text-green-600'">{{ stats.issues }}</div>
          <div class="text-xs text-gray-400 mt-1">{{ stats.issues > 0 ? '확인이 필요한 이슈' : '문제 없음' }}</div>
        </div>
      </a-col>
    </a-row>

    <a-row :gutter="16">
      <!-- 최근 활동 -->
      <a-col :xs="24" :lg="14">
        <a-card :bordered="false" class="mb-4">
          <template #title>
            <FieldTimeOutlined /> 최근 활동
          </template>
          <template #extra>
            <router-link to="/uploads" class="text-xs text-indigo-600 hover:underline">전체 보기 →</router-link>
          </template>

          <div v-if="loading" class="text-center py-8"><a-spin /></div>
          <div v-else-if="recentPosts.length === 0" class="empty-state !py-12">
            <InboxOutlined class="empty-state-icon" />
            <div class="text-sm font-medium mb-1 text-gray-700">아직 등록된 자료가 없어요</div>
            <div class="text-xs mb-4">첫 자료를 올려서 지식베이스를 시작해보세요</div>
            <router-link to="/upload">
              <a-button type="primary"><PlusOutlined /> 자료 올리기</a-button>
            </router-link>
          </div>
          <div v-else class="space-y-2">
            <router-link
              v-for="p in recentPosts"
              :key="p.id"
              :to="`/uploads/${p.id}`"
              class="block p-3 hover:bg-gray-50 rounded-lg transition border"
              style="border-color: transparent;"
            >
              <div class="flex items-center justify-between gap-2">
                <div class="flex-1 min-w-0">
                  <div class="font-medium text-gray-900 truncate">{{ p.title }}</div>
                  <div class="text-xs text-gray-400 mt-0.5">
                    {{ dayjs(p.created_at).fromNow() }}
                    <span v-if="p.category"> · {{ p.category }}</span>
                  </div>
                </div>
                <FriendlyStatus :status="p.status" />
              </div>
            </router-link>
          </div>
        </a-card>
      </a-col>

      <!-- 빠른 액션 + 최근 페이지 -->
      <a-col :xs="24" :lg="10">
        <a-card :bordered="false" class="mb-4">
          <template #title>
            <BulbOutlined /> 이렇게 시작해보세요
          </template>
          <div class="space-y-2">
            <button
              v-for="(tip, i) in tips"
              :key="i"
              class="w-full text-left p-3 hover:bg-indigo-50 rounded-lg transition flex items-start gap-3 border"
              style="border-color: var(--color-border);"
              @click="tip.action"
            >
              <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" :class="tip.bg">
                <component :is="tip.icon" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-gray-900">{{ tip.title }}</div>
                <div class="text-xs text-gray-500 mt-0.5">{{ tip.desc }}</div>
              </div>
              <ArrowRightOutlined class="text-gray-300" />
            </button>
          </div>
        </a-card>

        <a-card :bordered="false" v-if="recentPages.length > 0">
          <template #title>
            <BookOutlined /> 최근 정리된 페이지
          </template>
          <template #extra>
            <router-link to="/library" class="text-xs text-indigo-600 hover:underline">전체 보기 →</router-link>
          </template>
          <div class="space-y-1">
            <router-link
              v-for="pg in recentPages"
              :key="pg.id"
              :to="`/library?path=${encodeURIComponent(pg.path)}`"
              class="block p-2 hover:bg-gray-50 rounded text-sm flex items-center gap-2 group"
            >
              <FileOutlined class="text-gray-400 flex-shrink-0 group-hover:text-indigo-500" />
              <span class="flex-1 truncate">{{ pg.title }}</span>
              <span class="text-[10px] text-gray-400 flex-shrink-0">{{ dayjs(pg.updated_at).fromNow() }}</span>
            </router-link>
          </div>
        </a-card>
      </a-col>
    </a-row>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/ko'
import {
  PlusOutlined, MessageOutlined, BookOutlined, InboxOutlined,
  SyncOutlined, SafetyCertificateOutlined, FieldTimeOutlined,
  BulbOutlined, ArrowRightOutlined, FileOutlined, EditOutlined,
} from '@ant-design/icons-vue'
import { ingestApi } from '@/api/ingest'
import { wikiApi } from '@/api/wiki'
import { lintApi } from '@/api/lint'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/components/AppLayout.vue'
import FriendlyStatus from '@/components/FriendlyStatus.vue'

dayjs.extend(relativeTime)
dayjs.locale('ko')

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(true)
const recentPosts = ref<any[]>([])
const recentPages = ref<any[]>([])
const stats = ref({ pages: 0, uploads: 0, processing: 0, issues: 0 })

const tips = computed(() => [
  {
    title: '회의록·메모 올려보기',
    desc: '복사해 붙여넣기만 해도 AI가 정리합니다',
    icon: EditOutlined,
    bg: 'bg-indigo-100 text-indigo-600',
    action: () => router.push('/upload'),
  },
  {
    title: '"이번 분기 핵심 결정은?" 같은 질문',
    desc: '쌓인 자료에서 답을 찾아드립니다',
    icon: MessageOutlined,
    bg: 'bg-purple-100 text-purple-600',
    action: () => router.push('/ask'),
  },
  {
    title: '지식 연결 그래프 보기',
    desc: '페이지 간 관계를 시각적으로',
    icon: BookOutlined,
    bg: 'bg-pink-100 text-pink-600',
    action: () => router.push('/library?view=graph'),
  },
])

async function load() {
  loading.value = true
  try {
    const [postsRes, pagesRes, qualityRes] = await Promise.all([
      ingestApi.list({ limit: 6 }),
      wikiApi.listPages(),
      lintApi.listFindings({ resolved: false, limit: 100 }).catch(() => ({ data: [] })),
    ])
    recentPosts.value = postsRes.data
    recentPages.value = (pagesRes.data || [])
      .slice()
      .sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''))
      .slice(0, 6)
    stats.value = {
      pages: pagesRes.data.length,
      uploads: postsRes.data.length === 6 ? postsRes.data.length : postsRes.data.length,
      processing: postsRes.data.filter((p: any) => ['ocr_running', 'ingest_running', 'pending'].includes(p.status)).length,
      issues: (qualityRes.data || []).length,
    }
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
