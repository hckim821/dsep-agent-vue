<template>
  <AppLayout>
    <div v-if="store.loading && !detail" class="text-center py-10"><a-spin /></div>
    <div v-else-if="detail">
      <div class="flex justify-between items-start mb-6">
        <div>
          <h2 class="text-2xl font-bold">{{ detail.post.title }}</h2>
          <div class="flex gap-2 mt-2">
            <StatusBadge :status="detail.post.status" />
            <a-tag :color="typeColor(detail.post.type)">{{ detail.post.type }}</a-tag>
            <a-tag v-if="detail.post.priority === 'urgent'" color="red">긴급</a-tag>
            <a-tag v-if="detail.post.unverified" color="warning">미검증 포함</a-tag>
          </div>
        </div>
        <div class="flex gap-2">
          <a-button
            v-if="detail.post.status === 'pending' || detail.post.status === 'failed'"
            type="primary"
            :loading="running"
            @click="handleRun"
          >즉시 처리</a-button>
          <a-button
            v-if="detail.post.status === 'failed'"
            :loading="running"
            @click="handleRetry"
          >재시도</a-button>
        </div>
      </div>

      <a-row :gutter="16">
        <a-col :span="14">
          <a-card title="본문" class="mb-4">
            <MarkdownRender :content="detail.post.body_md" />
          </a-card>

          <a-card title="LLM 작업 로그" v-if="latestJob?.log_text" class="mb-4">
            <pre class="text-sm bg-gray-50 p-3 rounded overflow-auto max-h-96">{{ latestJob.log_text }}</pre>
          </a-card>

          <a-card title="에러" v-if="latestJob?.error_text" class="mb-4">
            <pre class="text-sm bg-red-50 text-red-700 p-3 rounded overflow-auto">{{ latestJob.error_text }}</pre>
          </a-card>
        </a-col>

        <a-col :span="10">
          <a-card title="처리 타임라인" class="mb-4">
            <Timeline :jobs="detail.jobs" />
          </a-card>

          <a-card title="연관 위키 페이지" class="mb-4" v-if="detail.wiki_pages.length">
            <div v-for="wp in detail.wiki_pages" :key="wp.id" class="mb-2">
              <a-tag :color="wp.relation === 'created' ? 'green' : 'blue'">
                {{ wp.relation === 'created' ? '생성' : '수정' }}
              </a-tag>
              <router-link :to="`/wiki?path=${wp.path}`" class="ml-2 text-blue-600 hover:underline">
                {{ wp.title }}
              </router-link>
            </div>
          </a-card>

          <a-card title="출처 정보" v-if="detail.post.source_url || detail.post.source_author">
            <div v-if="detail.post.source_url">
              URL: <a :href="detail.post.source_url" target="_blank" class="text-blue-600">{{ detail.post.source_url }}</a>
            </div>
            <div v-if="detail.post.source_author">저자: {{ detail.post.source_author }}</div>
            <div v-if="detail.post.source_date">발행일: {{ detail.post.source_date }}</div>
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
import { useIngestStore } from '@/stores/ingest'
import { ingestApi } from '@/api/ingest'
import AppLayout from '@/components/AppLayout.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import Timeline from '@/components/Timeline.vue'
import MarkdownRender from '@/components/MarkdownRender.vue'

const store = useIngestStore()
const route = useRoute()
const running = ref(false)
const pollTimer = ref<number | null>(null)

const detail = computed(() => store.currentDetail)
const latestJob = computed(() => {
  const jobs = detail.value?.jobs
  return jobs && jobs.length ? jobs[jobs.length - 1] : undefined
})

function typeColor(type: string) {
  return ({ new: 'blue', correction: 'orange', chat_summary: 'purple' } as Record<string, string>)[type] || 'default'
}

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
  pollTimer.value = window.setInterval(async () => {
    await load()
    const status = detail.value?.post.status
    if (status === 'done' || status === 'failed') {
      stopPolling()
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

onMounted(load)
onUnmounted(stopPolling)
</script>
