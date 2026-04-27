<template>
  <AppLayout>
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-xl font-bold">Ingest 게시판</h2>
      <a-button type="primary" @click="$router.push('/ingest/new')">새 게시글</a-button>
    </div>

    <div class="flex gap-3 mb-4">
      <a-select v-model:value="filterStatus" placeholder="상태 필터" allow-clear style="width: 150px" @change="load">
        <a-select-option value="pending">대기중</a-select-option>
        <a-select-option value="ingest_running">처리중</a-select-option>
        <a-select-option value="done">완료</a-select-option>
        <a-select-option value="failed">실패</a-select-option>
      </a-select>
      <a-input-search v-model:value="filterCategory" placeholder="카테고리" style="width: 200px" @search="load" />
    </div>

    <a-table
      :data-source="store.posts"
      :loading="store.loading"
      :columns="columns"
      row-key="id"
      :custom-row="customRow"
      :row-class-name="() => 'cursor-pointer'"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <StatusBadge :status="record.status" />
        </template>
        <template v-if="column.key === 'type'">
          <a-tag :color="typeColor(record.type)">{{ record.type }}</a-tag>
        </template>
        <template v-if="column.key === 'priority'">
          <a-tag v-if="record.priority === 'urgent'" color="red">긴급</a-tag>
        </template>
        <template v-if="column.key === 'created_at'">
          {{ dayjs(record.created_at).format('YYYY-MM-DD HH:mm') }}
        </template>
      </template>
    </a-table>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { useIngestStore } from '@/stores/ingest'
import AppLayout from '@/components/AppLayout.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import type { IngestPost } from '@/api/types'

const router = useRouter()
const store = useIngestStore()
const filterStatus = ref<string | undefined>()
const filterCategory = ref('')

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  { title: '제목', dataIndex: 'title', key: 'title' },
  { title: '타입', key: 'type', width: 100 },
  { title: '우선순위', key: 'priority', width: 90 },
  { title: '카테고리', dataIndex: 'category', key: 'category', width: 120 },
  { title: '상태', key: 'status', width: 130 },
  { title: '작성일', key: 'created_at', width: 160 },
]

function typeColor(type: string) {
  return ({ new: 'blue', correction: 'orange', chat_summary: 'purple' } as Record<string, string>)[type] || 'default'
}

function customRow(record: IngestPost) {
  return {
    onClick: () => router.push(`/ingest/${record.id}`),
  }
}

async function load() {
  await store.fetchPosts({
    status: filterStatus.value,
    category: filterCategory.value || undefined,
  })
}

onMounted(load)
</script>
