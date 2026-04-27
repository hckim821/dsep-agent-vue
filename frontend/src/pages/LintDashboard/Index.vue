<template>
  <AppLayout>
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-xl font-bold">Lint 결과 대시보드</h2>
      <a-button type="primary" :loading="running" @click="runLint">Lint 실행</a-button>
    </div>

    <div class="flex gap-3 mb-4">
      <a-select v-model:value="filterType" placeholder="타입 필터" allow-clear style="width: 160px" @change="load">
        <a-select-option value="contradiction">모순</a-select-option>
        <a-select-option value="orphan">고아 페이지</a-select-option>
        <a-select-option value="stale">오래된 페이지</a-select-option>
        <a-select-option value="missing_entity">누락 개념</a-select-option>
        <a-select-option value="broken_link">깨진 링크</a-select-option>
      </a-select>
      <a-select v-model:value="filterSeverity" placeholder="심각도" allow-clear style="width: 120px" @change="load">
        <a-select-option value="high">높음</a-select-option>
        <a-select-option value="medium">보통</a-select-option>
        <a-select-option value="low">낮음</a-select-option>
      </a-select>
      <a-select v-model:value="filterResolved" placeholder="해결 여부" allow-clear style="width: 130px" @change="load">
        <a-select-option :value="false">미해결</a-select-option>
        <a-select-option :value="true">해결됨</a-select-option>
      </a-select>
    </div>

    <a-row :gutter="16" class="mb-6">
      <a-col :span="5" v-for="stat in stats" :key="stat.type">
        <a-card size="small" :bordered="false" class="bg-gray-50">
          <div class="text-xs text-gray-500">{{ typeLabel(stat.type) }}</div>
          <div class="text-2xl font-bold" :class="stat.count > 0 ? 'text-red-500' : 'text-green-500'">
            {{ stat.count }}
          </div>
        </a-card>
      </a-col>
    </a-row>

    <a-list
      :data-source="findings"
      :loading="loading"
      item-layout="horizontal"
    >
      <template #renderItem="{ item }">
        <a-list-item>
          <a-list-item-meta>
            <template #title>
              <div class="flex items-center gap-2">
                <a-tag :color="severityColor(item.severity)">{{ severityLabel(item.severity) }}</a-tag>
                <a-tag>{{ typeLabel(item.type) }}</a-tag>
                <span>{{ item.description }}</span>
              </div>
            </template>
            <template #description>
              <span class="text-xs text-gray-400">
                발견: {{ dayjs(item.detected_at).format('YYYY-MM-DD HH:mm') }}
                <span v-if="item.resolved_at"> · 해결: {{ dayjs(item.resolved_at).format('YYYY-MM-DD') }}</span>
              </span>
            </template>
          </a-list-item-meta>
          <template #actions>
            <a-button
              v-if="!item.resolved_at"
              size="small"
              @click="createIngest(item)"
            >Ingest 보충</a-button>
          </template>
        </a-list-item>
      </template>
    </a-list>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { message } from 'ant-design-vue'
import { lintApi } from '@/api/lint'
import type { LintFinding } from '@/api/types'
import AppLayout from '@/components/AppLayout.vue'

const router = useRouter()
const findings = ref<LintFinding[]>([])
const loading = ref(false)
const running = ref(false)
const filterType = ref<string | undefined>()
const filterSeverity = ref<string | undefined>()
const filterResolved = ref<boolean | undefined>()

const typeLabels: Record<string, string> = {
  contradiction: '모순',
  orphan: '고아 페이지',
  stale: '오래된 페이지',
  missing_entity: '누락 개념',
  broken_link: '깨진 링크',
}

const stats = computed(() => {
  const types = ['contradiction', 'orphan', 'stale', 'missing_entity', 'broken_link']
  return types.map(t => ({
    type: t,
    count: findings.value.filter(f => f.type === t && !f.resolved_at).length,
  }))
})

function typeLabel(type: string) { return typeLabels[type] || type }
function severityLabel(s: string) {
  const map: Record<string, string> = { high: '높음', medium: '보통', low: '낮음' }
  return map[s] || s
}
function severityColor(s: string) {
  const map: Record<string, string> = { high: 'red', medium: 'orange', low: 'default' }
  return map[s] || 'default'
}

async function load() {
  loading.value = true
  try {
    const res = await lintApi.listFindings({
      type: filterType.value,
      severity: filterSeverity.value,
      resolved: filterResolved.value,
    })
    findings.value = res.data
  } finally {
    loading.value = false
  }
}

async function runLint() {
  running.value = true
  try {
    await lintApi.runLint()
    message.success('Lint를 시작했습니다. 잠시 후 결과를 확인하세요.')
    setTimeout(load, 5000)
  } catch (e: any) {
    message.error(e?.response?.data?.detail || 'Lint 실행 실패')
  } finally {
    running.value = false
  }
}

function createIngest(finding: LintFinding) {
  router.push({
    path: '/ingest/new',
    query: {
      type: 'new',
      category: finding.type,
      title: `Lint 보충: ${typeLabel(finding.type)} — ${finding.description?.slice(0, 60)}`,
    },
  })
}

onMounted(load)
</script>
