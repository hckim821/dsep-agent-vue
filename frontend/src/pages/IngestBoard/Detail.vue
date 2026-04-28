<template>
  <AppLayout>
    <div v-if="store.loading && !detail" class="flex items-center justify-center py-20">
      <a-spin size="large" />
    </div>
    <div v-else-if="detail">
      <!-- 헤더 -->
      <div class="mb-4">
        <a-button type="text" size="small" @click="$router.push('/uploads')" class="-ml-2 mb-2">
          <LeftOutlined /> 내가 올린 자료
        </a-button>
        <div class="flex justify-between items-start gap-4">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-gray-400 font-mono text-sm">#{{ detail.post.id }}</span>
              <a-tag :color="typeColor(detail.post.type)" class="!m-0">{{ typeLabel(detail.post.type) }}</a-tag>
              <a-tag v-if="detail.post.priority === 'urgent'" color="red" class="!m-0">⚡ 긴급</a-tag>
              <a-tag v-if="detail.post.unverified" color="warning" class="!m-0">⚠ 미검증</a-tag>
              <StatusBadge :status="detail.post.status" />
              <span v-if="polling" class="inline-flex items-center gap-1 text-xs text-indigo-500">
                <SyncOutlined spin /> 진행 상황 자동 갱신
              </span>
            </div>
            <h2 class="text-2xl font-bold tracking-tight">{{ detail.post.title }}</h2>
            <div class="text-xs text-gray-500 mt-2">
              <span>작성: {{ dayjs(detail.post.created_at).format('YYYY-MM-DD HH:mm') }}</span>
              <span v-if="detail.post.updated_at !== detail.post.created_at"> · 수정: {{ dayjs(detail.post.updated_at).fromNow() }}</span>
              <span v-if="detail.post.category"> · 카테고리: <code>{{ detail.post.category }}</code></span>
            </div>
          </div>
          <div class="flex gap-2 flex-shrink-0">
            <a-button
              v-if="canEdit"
              size="large"
              @click="$router.push(`/uploads/${detail.post.id}/edit`)"
            >
              <EditOutlined /> 수정
            </a-button>
            <a-button
              v-if="detail.post.status === 'pending'"
              type="primary"
              :loading="running"
              @click="handleRun"
              size="large"
            >
              <PlayCircleOutlined /> 지금 정리 시작
            </a-button>
            <a-button
              v-if="detail.post.status === 'failed'"
              type="primary"
              danger
              :loading="running"
              @click="handleRetry"
              size="large"
            >
              <RedoOutlined /> 다시 시도
            </a-button>
          </div>
        </div>
      </div>

      <!-- 단계 진행 -->
      <a-card :bordered="false" class="mb-4">
        <a-steps :current="currentStep" :status="stepStatus" size="small">
          <a-step title="등록 완료" description="자료 접수됨" />
          <a-step title="이미지 인식" :description="ocrSummary" />
          <a-step title="AI 정리" :description="ingestSummary" />
          <a-step title="지식베이스 반영" :description="commitSummary" />
        </a-steps>
      </a-card>

      <a-row :gutter="16">
        <!-- 좌측: 본문 + 로그 -->
        <a-col :xs="24" :lg="14">
          <a-card title="본문" :bordered="false" class="mb-4">
            <MarkdownRender :content="detail.post.body_md" />
          </a-card>

          <a-card v-if="detail.post.source_url || detail.post.source_author" :bordered="false" class="mb-4">
            <template #title>
              <LinkOutlined /> 출처
            </template>
            <div class="space-y-2 text-sm">
              <div v-if="detail.post.source_url" class="flex items-center gap-2">
                <span class="text-gray-500 w-12">URL</span>
                <a :href="detail.post.source_url" target="_blank" class="text-indigo-600 hover:underline truncate">
                  {{ detail.post.source_url }}
                </a>
              </div>
              <div v-if="detail.post.source_author" class="flex items-center gap-2">
                <span class="text-gray-500 w-12">저자</span>
                <span>{{ detail.post.source_author }}</span>
              </div>
              <div v-if="detail.post.source_date" class="flex items-center gap-2">
                <span class="text-gray-500 w-12">발행</span>
                <span>{{ detail.post.source_date }}</span>
              </div>
            </div>
          </a-card>

          <a-card v-if="latestJob?.log_text || latestJob?.error_text" :bordered="false" class="mb-4">
            <template #title>
              <FileSearchOutlined /> AI 처리 기록 <span class="text-xs text-gray-400 font-normal ml-1">(고급)</span>
            </template>
            <div v-if="latestJob.log_text" class="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-auto max-h-96 text-xs font-mono leading-relaxed whitespace-pre-wrap">{{ latestJob.log_text }}</div>
            <div v-if="latestJob.error_text" class="mt-3 bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg overflow-auto max-h-96 text-xs font-mono whitespace-pre-wrap">{{ latestJob.error_text }}</div>
          </a-card>
        </a-col>

        <!-- 우측: 타임라인 + 결과 -->
        <a-col :xs="24" :lg="10">
          <a-card title="진행 기록" :bordered="false" class="mb-4">
            <Timeline v-if="detail.jobs.length" :jobs="detail.jobs" />
            <div v-else class="text-center py-6 text-gray-400 text-sm">
              <ClockCircleOutlined class="text-3xl block mb-2" />
              아직 처리되지 않았습니다
            </div>
          </a-card>

          <a-card v-if="detail.wiki_pages.length" :bordered="false" class="mb-4">
            <template #title>
              <BookOutlined /> 정리된 페이지
              <a-tag class="ml-2 !m-0">{{ detail.wiki_pages.length }}</a-tag>
            </template>
            <div class="space-y-2">
              <router-link
                v-for="wp in detail.wiki_pages"
                :key="wp.id"
                :to="`/library?path=${encodeURIComponent(wp.path)}`"
                class="block p-3 bg-gray-50 hover:bg-indigo-50 rounded-lg transition group"
              >
                <div class="flex items-start gap-2">
                  <a-tag
                    :color="wp.relation === 'created' ? 'green' : 'blue'"
                    class="!m-0 flex-shrink-0"
                  >
                    {{ wp.relation === 'created' ? '생성' : '수정' }}
                  </a-tag>
                  <div class="flex-1 min-w-0">
                    <div class="font-medium text-gray-900 group-hover:text-indigo-600 truncate">{{ wp.title }}</div>
                    <div class="text-xs text-gray-400 truncate font-mono">{{ wp.path }}</div>
                  </div>
                  <ArrowRightOutlined class="text-gray-300 group-hover:text-indigo-500" />
                </div>
              </router-link>
            </div>
          </a-card>

          <a-card v-if="detail.post.status === 'pending'" :bordered="false" class="mb-4">
            <div class="text-center py-2">
              <ClockCircleOutlined class="text-3xl text-gray-300 mb-2 block" />
              <p class="text-sm text-gray-600 mb-3">아직 정리가 시작되지 않았어요</p>
              <p class="text-xs text-gray-400 mb-3">매일 자동으로 처리되지만, 지금 바로 시작할 수도 있어요.</p>
              <a-button type="primary" @click="handleRun" :loading="running" block>
                <PlayCircleOutlined /> 지금 정리 시작
              </a-button>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/ko'
import {
  LeftOutlined, PlayCircleOutlined, RedoOutlined, SyncOutlined, LinkOutlined,
  FileSearchOutlined, BookOutlined, ArrowRightOutlined, ClockCircleOutlined,
  EditOutlined,
} from '@ant-design/icons-vue'
import { useIngestStore } from '@/stores/ingest'
import { ingestApi } from '@/api/ingest'
import AppLayout from '@/components/AppLayout.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import Timeline from '@/components/Timeline.vue'
import MarkdownRender from '@/components/MarkdownRender.vue'

dayjs.extend(relativeTime)
dayjs.locale('ko')

const store = useIngestStore()
const route = useRoute()
const running = ref(false)
const polling = ref(false)
const pollTimer = ref<number | null>(null)

const detail = computed(() => store.currentDetail)
const canEdit = computed(() => {
  const s = detail.value?.post.status
  return s === 'pending' || s === 'done' || s === 'failed'
})
const latestJob = computed(() => {
  const jobs = detail.value?.jobs
  return jobs && jobs.length ? jobs[jobs.length - 1] : undefined
})

function typeColor(t: string) {
  return ({ new: 'blue', correction: 'orange', chat_summary: 'purple' } as Record<string, string>)[t] || 'default'
}
function typeLabel(t: string) {
  return ({ new: '새 자료', correction: '수정 제안', chat_summary: '대화 정리' } as Record<string, string>)[t] || t
}

const currentStep = computed(() => {
  const s = detail.value?.post.status
  if (!s) return 0
  if (s === 'pending') return 0
  if (s === 'ocr_running') return 1
  if (s === 'ocr_done' || s === 'ingest_running') return 2
  if (s === 'ingest_done' || s === 'done') return 3
  if (s === 'failed') return Math.max(0, currentStepBeforeFail.value)
  return 0
})
const currentStepBeforeFail = computed(() => {
  const failedAt = detail.value?.jobs.find(j => j.status === 'failed')?.stage
  if (failedAt === 'ocr') return 1
  if (failedAt === 'ingest') return 2
  return 0
})
const stepStatus = computed<'wait' | 'process' | 'finish' | 'error'>(() => {
  const s = detail.value?.post.status
  if (s === 'failed') return 'error'
  if (s === 'done') return 'finish'
  if (['ocr_running','ingest_running'].includes(s || '')) return 'process'
  return 'wait'
})

const ocrSummary = computed(() => {
  const ocrJob = detail.value?.jobs.find(j => j.stage === 'ocr')
  if (!ocrJob) return '대기 중'
  if (ocrJob.status === 'success') return '완료'
  if (ocrJob.status === 'failed') return '문제 발생'
  return '진행 중'
})
const ingestSummary = computed(() => {
  const j = detail.value?.jobs.find(jj => jj.stage === 'ingest')
  if (!j) return '대기 중'
  if (j.status === 'success') return '정리 완료'
  if (j.status === 'failed') return '문제 발생'
  return 'AI 분석 중'
})
const commitSummary = computed(() => {
  if (detail.value?.wiki_pages.length) {
    return `${detail.value.wiki_pages.length}개 페이지 반영됨`
  }
  return ''
})

async function load() {
  await store.fetchDetail(Number(route.params.id))
}

async function handleRun() {
  running.value = true
  try {
    await ingestApi.run(Number(route.params.id))
    message.success('처리를 시작했습니다')
    startPolling()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '실행 실패')
  } finally {
    running.value = false
  }
}

async function handleRetry() {
  running.value = true
  try {
    await ingestApi.retry(Number(route.params.id))
    message.success('재시도를 시작했습니다')
    startPolling()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '재시도 실패')
  } finally {
    running.value = false
  }
}

function startPolling() {
  if (pollTimer.value) return
  polling.value = true
  pollTimer.value = window.setInterval(async () => {
    await load()
    const status = detail.value?.post.status
    if (status === 'done' || status === 'failed') {
      stopPolling()
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
  polling.value = false
}

onMounted(async () => {
  await load()
  // 진행 중이면 자동 폴링
  const s = detail.value?.post.status
  if (s && ['ocr_running','ingest_running','ocr_done','ingest_done'].includes(s)) {
    startPolling()
  }
})
onUnmounted(stopPolling)
</script>
