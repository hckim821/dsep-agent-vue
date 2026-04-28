<template>
  <AppLayout>
    <div v-if="!authStore.isAdmin" class="empty-state bg-white rounded-xl border" style="border-color: var(--color-border);">
      <LockOutlined class="empty-state-icon" />
      <div class="text-base font-medium mb-1 text-gray-700">관리자 권한이 필요합니다</div>
      <div class="text-sm">Schema 편집은 admin 역할만 가능합니다</div>
    </div>
    <div v-else>
      <div class="flex justify-between items-start mb-6">
        <div>
          <h2 class="text-2xl font-bold tracking-tight">Schema 관리</h2>
          <p class="text-gray-500 text-sm mt-1">위키 구조·작성 규칙·LLM 프롬프트를 관리합니다</p>
        </div>
        <div class="flex gap-2">
          <a-button @click="resetUnsaved" :disabled="!isDirty">
            <UndoOutlined /> 변경 취소
          </a-button>
          <a-button type="primary" size="large" :loading="saving" :disabled="!isDirty" @click="save">
            <SaveOutlined /> 저장
          </a-button>
        </div>
      </div>

      <a-row :gutter="16">
        <a-col :span="16">
          <a-card :bordered="false" class="mb-4">
            <template #title>
              현재 Schema
              <span v-if="currentVersion" class="text-xs text-gray-400 font-normal ml-2">
                v{{ currentVersion.id }} · {{ dayjs(currentVersion.updated_at).fromNow() }}
              </span>
              <a-tag v-if="isDirty" color="orange" class="ml-2 !m-0 !text-[10px]">변경됨</a-tag>
            </template>
            <template #extra>
              <a-radio-group v-model:value="editMode" size="small" button-style="solid">
                <a-radio-button value="edit"><EditOutlined /> 편집</a-radio-button>
                <a-radio-button value="preview"><EyeOutlined /> 미리보기</a-radio-button>
              </a-radio-group>
            </template>

            <a-textarea
              v-show="editMode === 'edit'"
              v-model:value="content"
              :rows="20"
              class="!font-mono !text-sm"
              placeholder="Schema 내용을 Markdown으로 작성하세요..."
              style="resize: vertical;"
            />
            <div
              v-show="editMode === 'preview'"
              class="border rounded-lg p-6 overflow-auto"
              style="border-color: var(--color-border); min-height: 480px;"
            >
              <MarkdownRender v-if="content" :content="content" />
              <div v-else class="text-gray-300 text-center py-12">
                <FileTextOutlined class="text-4xl block mb-2" />
                내용을 입력하면 미리보기가 표시됩니다
              </div>
            </div>

            <a-input
              v-model:value="note"
              placeholder="변경 사유를 간단히 적어주세요 (선택)"
              class="mt-3"
              :maxlength="500"
            >
              <template #prefix><EditOutlined class="text-gray-400" /></template>
            </a-input>
          </a-card>
        </a-col>

        <a-col :span="8">
          <a-card :bordered="false">
            <template #title>변경 이력</template>
            <a-spin v-if="histLoading" />
            <div v-else-if="versions.length === 0" class="text-center text-gray-400 text-sm py-6">
              아직 이력이 없습니다
            </div>
            <a-timeline v-else>
              <a-timeline-item
                v-for="v in versions"
                :key="v.id"
                :color="v.id === currentVersion?.id ? 'green' : 'gray'"
              >
                <div class="flex items-center gap-2 mb-1">
                  <span class="font-semibold text-sm">v{{ v.id }}</span>
                  <a-tag v-if="v.id === currentVersion?.id" color="green" class="!m-0 !text-[10px]">현재</a-tag>
                </div>
                <div class="text-xs text-gray-400">{{ dayjs(v.updated_at).format('YYYY-MM-DD HH:mm') }}</div>
                <div v-if="v.note" class="text-xs text-gray-600 mt-1 italic">"{{ v.note }}"</div>
                <a-button
                  v-if="v.id !== currentVersion?.id"
                  size="small"
                  class="!mt-2"
                  @click="loadVersion(v)"
                >불러오기</a-button>
              </a-timeline-item>
            </a-timeline>
          </a-card>
        </a-col>
      </a-row>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/ko'
import { message } from 'ant-design-vue'
import {
  LockOutlined, SaveOutlined, UndoOutlined,
  EditOutlined, EyeOutlined, FileTextOutlined,
} from '@ant-design/icons-vue'
import { schemaApi } from '@/api/schema'
import type { SchemaVersion } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/components/AppLayout.vue'
import MarkdownRender from '@/components/MarkdownRender.vue'

dayjs.extend(relativeTime)
dayjs.locale('ko')

const authStore = useAuthStore()
const content = ref('')
const originalContent = ref('')
const note = ref('')
const saving = ref(false)
const histLoading = ref(false)
const versions = ref<SchemaVersion[]>([])
const currentVersion = ref<SchemaVersion | null>(null)
const editMode = ref<'edit' | 'preview'>('edit')

const isDirty = computed(() => content.value !== originalContent.value)

async function load() {
  try {
    const res = await schemaApi.getCurrent()
    currentVersion.value = res.data
    content.value = res.data.content
    originalContent.value = res.data.content
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
    originalContent.value = content.value
    note.value = ''
    message.success(`v${res.data.id}로 저장되었습니다`)
    await load()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '저장 실패')
  } finally {
    saving.value = false
  }
}

function resetUnsaved() {
  content.value = originalContent.value
  note.value = ''
}

function loadVersion(v: SchemaVersion) {
  content.value = v.content
  message.info(`v${v.id} 버전을 불러왔습니다. 저장하면 새 버전으로 등록됩니다.`)
}

onMounted(load)
</script>
