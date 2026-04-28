<template>
  <AppLayout>
    <div class="flex justify-between items-start mb-6">
      <div>
        <h2 class="text-2xl font-bold tracking-tight">내가 올린 자료</h2>
        <p class="text-gray-500 text-sm mt-1">올린 자료가 어떻게 정리됐는지 확인하세요</p>
      </div>
      <a-button type="primary" size="large" @click="$router.push('/upload')">
        <PlusOutlined /> 자료 올리기
      </a-button>
    </div>

    <a-row :gutter="16" class="mb-6">
      <a-col :xs="12" :sm="6" v-for="s in stats" :key="s.key">
        <div class="stat-card bg-white rounded-xl p-4 border" style="border-color: var(--color-border);">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-xs text-gray-500 mb-1">{{ s.label }}</div>
              <div class="text-2xl font-bold" :class="s.colorCls">{{ s.count }}</div>
            </div>
            <div class="w-10 h-10 rounded-lg flex items-center justify-center text-lg" :class="s.iconBg">
              <component :is="s.icon" />
            </div>
          </div>
        </div>
      </a-col>
    </a-row>

    <a-card :bordered="false" class="mb-4">
      <div class="flex flex-wrap items-center gap-3">
        <a-input
          v-model:value="search"
          placeholder="제목으로 검색..."
          allow-clear
          style="width: 280px"
        >
          <template #prefix><SearchOutlined class="text-gray-400" /></template>
        </a-input>
        <a-select v-model:value="filterStatus" placeholder="상태 전체" allow-clear style="width: 160px" @change="load">
          <a-select-option value="pending">곧 시작</a-select-option>
          <a-select-option value="ingest_running">정리 중</a-select-option>
          <a-select-option value="done">완료</a-select-option>
          <a-select-option value="failed">문제 발생</a-select-option>
        </a-select>
        <a-select v-model:value="filterType" placeholder="종류 전체" allow-clear style="width: 140px" @change="load">
          <a-select-option value="new">새 자료</a-select-option>
          <a-select-option value="correction">수정 제안</a-select-option>
          <a-select-option value="chat_summary">대화 정리</a-select-option>
        </a-select>
        <a-input v-model:value="filterCategory" placeholder="주제" allow-clear style="width: 160px" @change="load" />
        <a-button @click="load" :loading="store.loading">
          <ReloadOutlined /> 새로고침
        </a-button>
      </div>
    </a-card>

    <div v-if="!store.loading && filteredPosts.length === 0">
      <div class="empty-state bg-white rounded-xl border" style="border-color: var(--color-border);">
        <InboxOutlined class="empty-state-icon" />
        <div class="text-base font-medium mb-1 text-gray-700">아직 올린 자료가 없어요</div>
        <div class="text-sm mb-4">첫 자료를 올리면 AI가 지식베이스를 만들기 시작합니다</div>
        <a-button type="primary" @click="$router.push('/upload')">
          <PlusOutlined /> 자료 올리기
        </a-button>
      </div>
    </div>

    <a-table
      v-else
      :data-source="filteredPosts"
      :loading="store.loading"
      :columns="columns"
      row-key="id"
      :custom-row="customRow"
      :row-class-name="() => 'cursor-pointer'"
      :pagination="{ pageSize: 20, showSizeChanger: false }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'title'">
          <div class="flex items-center gap-2">
            <span class="font-medium">{{ record.title }}</span>
            <a-tag v-if="record.unverified" color="warning" class="!text-[10px]">검토 필요</a-tag>
          </div>
        </template>
        <template v-if="column.key === 'type'">
          <a-tag :color="typeColor(record.type)" class="!m-0">{{ typeLabel(record.type) }}</a-tag>
        </template>
        <template v-if="column.key === 'priority'">
          <a-tag v-if="record.priority === 'urgent'" color="red" class="!m-0">긴급</a-tag>
          <span v-else class="text-gray-300">—</span>
        </template>
        <template v-if="column.key === 'category'">
          <span v-if="record.category" class="text-xs text-gray-600 bg-gray-100 px-2 py-0.5 rounded">{{ record.category }}</span>
          <span v-else class="text-gray-300">—</span>
        </template>
        <template v-if="column.key === 'status'">
          <FriendlyStatus :status="record.status" />
        </template>
        <template v-if="column.key === 'created_at'">
          <a-tooltip :title="dayjs(record.created_at).format('YYYY-MM-DD HH:mm:ss')">
            <span class="text-xs text-gray-500">{{ dayjs(record.created_at).fromNow() }}</span>
          </a-tooltip>
        </template>
      </template>
    </a-table>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/ko'
import {
  PlusOutlined, SearchOutlined, ReloadOutlined, InboxOutlined,
  ClockCircleOutlined, SyncOutlined, CheckCircleOutlined, CloseCircleOutlined,
} from '@ant-design/icons-vue'
import { useIngestStore } from '@/stores/ingest'
import AppLayout from '@/components/AppLayout.vue'
import FriendlyStatus from '@/components/FriendlyStatus.vue'
import type { IngestPost } from '@/api/types'

dayjs.extend(relativeTime)
dayjs.locale('ko')

const router = useRouter()
const store = useIngestStore()
const search = ref('')
const filterStatus = ref<string | undefined>()
const filterType = ref<string | undefined>()
const filterCategory = ref('')

const columns = [
  { title: '제목', key: 'title' },
  { title: '종류', key: 'type', width: 110 },
  { title: '우선', key: 'priority', width: 70 },
  { title: '주제', key: 'category', width: 120 },
  { title: '상태', key: 'status', width: 140 },
  { title: '올린 날짜', key: 'created_at', width: 110 },
]

const stats = computed(() => [
  { key: 'pending', label: '곧 시작', count: store.posts.filter(p => p.status === 'pending').length, colorCls: 'text-gray-700', iconBg: 'bg-gray-100 text-gray-500', icon: ClockCircleOutlined },
  { key: 'running', label: '정리 중', count: store.posts.filter(p => ['ocr_running','ingest_running'].includes(p.status)).length, colorCls: 'text-indigo-600', iconBg: 'bg-indigo-100 text-indigo-500', icon: SyncOutlined },
  { key: 'done', label: '완료', count: store.posts.filter(p => p.status === 'done').length, colorCls: 'text-green-600', iconBg: 'bg-green-100 text-green-500', icon: CheckCircleOutlined },
  { key: 'failed', label: '문제 발생', count: store.posts.filter(p => p.status === 'failed').length, colorCls: 'text-red-600', iconBg: 'bg-red-100 text-red-500', icon: CloseCircleOutlined },
])

const filteredPosts = computed(() => {
  let result = store.posts
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    result = result.filter(p => p.title.toLowerCase().includes(q))
  }
  if (filterType.value) result = result.filter(p => p.type === filterType.value)
  return result
})

function typeColor(type: string) {
  return ({ new: 'blue', correction: 'orange', chat_summary: 'purple' } as Record<string, string>)[type] || 'default'
}
function typeLabel(type: string) {
  return ({ new: '새 자료', correction: '수정 제안', chat_summary: '대화 정리' } as Record<string, string>)[type] || type
}

function customRow(record: IngestPost) {
  return { onClick: () => router.push(`/uploads/${record.id}`) }
}

async function load() {
  await store.fetchPosts({
    status: filterStatus.value,
    category: filterCategory.value || undefined,
  })
}

onMounted(load)
</script>
