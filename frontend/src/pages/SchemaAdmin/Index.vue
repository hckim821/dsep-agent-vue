<template>
  <AppLayout>
    <div v-if="!authStore.isAdmin" class="text-center py-20 text-gray-500">
      관리자 권한이 필요합니다.
    </div>
    <div v-else>
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-bold">Schema 관리</h2>
        <a-button type="primary" :loading="saving" @click="save">저장</a-button>
      </div>

      <a-row :gutter="16">
        <a-col :span="16">
          <a-card title="현재 Schema" class="mb-4">
            <a-textarea
              v-model:value="content"
              :rows="24"
              class="font-mono text-sm"
              placeholder="Schema 내용 (Markdown)"
            />
            <a-input
              v-model:value="note"
              placeholder="변경 사유 (선택)"
              class="mt-2"
            />
          </a-card>
        </a-col>

        <a-col :span="8">
          <a-card title="변경 이력">
            <a-spin v-if="histLoading" />
            <a-timeline v-else>
              <a-timeline-item
                v-for="v in versions"
                :key="v.id"
                :color="v.id === currentVersion?.id ? 'green' : 'gray'"
              >
                <div class="text-sm font-medium">v{{ v.id }}</div>
                <div class="text-xs text-gray-400">{{ dayjs(v.updated_at).format('YYYY-MM-DD HH:mm') }}</div>
                <div v-if="v.note" class="text-xs text-gray-500">{{ v.note }}</div>
                <a-button
                  v-if="v.id !== currentVersion?.id"
                  size="small"
                  class="mt-1"
                  @click="loadVersion(v)"
                >이 버전 불러오기</a-button>
              </a-timeline-item>
            </a-timeline>
          </a-card>
        </a-col>
      </a-row>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import dayjs from 'dayjs'
import { message } from 'ant-design-vue'
import { schemaApi } from '@/api/schema'
import type { SchemaVersion } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/components/AppLayout.vue'

const authStore = useAuthStore()
const content = ref('')
const note = ref('')
const saving = ref(false)
const histLoading = ref(false)
const versions = ref<SchemaVersion[]>([])
const currentVersion = ref<SchemaVersion | null>(null)

async function load() {
  try {
    const res = await schemaApi.getCurrent()
    currentVersion.value = res.data
    content.value = res.data.content
  } catch {
    // No schema yet
  }

  histLoading.value = true
  try {
    const res = await schemaApi.listVersions()
    versions.value = res.data
  } finally {
    histLoading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const res = await schemaApi.update(content.value, note.value || undefined)
    currentVersion.value = res.data
    note.value = ''
    message.success('Schema가 저장되었습니다')
    await load()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '저장 실패')
  } finally {
    saving.value = false
  }
}

function loadVersion(v: SchemaVersion) {
  content.value = v.content
  message.info(`v${v.id} 버전을 불러왔습니다. 저장하면 새 버전으로 등록됩니다.`)
}

onMounted(load)
</script>
