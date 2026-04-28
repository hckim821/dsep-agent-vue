<template>
  <AppLayout>
    <div class="flex justify-between items-start mb-6">
      <div>
        <h2 class="text-2xl font-bold tracking-tight">품질 점검</h2>
        <p class="text-gray-500 text-sm mt-1">지식베이스의 빈틈, 어긋난 내용, 오래된 페이지를 찾아드려요</p>
      </div>
      <a-button type="primary" size="large" :loading="running" @click="runLint">
        <ThunderboltOutlined /> 지금 점검 시작
      </a-button>
    </div>

    <a-row :gutter="16" class="mb-6">
      <a-col :xs="12" :sm="8" :lg="5" v-for="stat in stats" :key="stat.type">
        <div
          class="stat-card bg-white rounded-xl p-4 border cursor-pointer"
          :class="filterType === stat.type ? 'ring-2 ring-indigo-300' : ''"
          style="border-color: var(--color-border);"
          @click="toggleFilter(stat.type)"
        >
          <div class="flex items-center justify-between mb-1">
            <span class="text-xs text-gray-500">{{ typeLabel(stat.type) }}</span>
            <component :is="stat.icon" :class="stat.iconCls" />
          </div>
          <div class="text-3xl font-bold" :class="stat.count > 0 ? stat.colorCls : 'text-gray-300'">
            {{ stat.count }}
          </div>
        </div>
      </a-col>
    </a-row>

    <a-card :bordered="false">
      <template #title>
        <span>점검 결과</span>
        <a-tag class="ml-2 !m-0">{{ findings.length }}건</a-tag>
      </template>
      <template #extra>
        <div class="flex gap-2">
          <a-select v-model:value="filterType" placeholder="유형 전체" allow-clear style="width: 170px" @change="load">
            <a-select-option value="contradiction">서로 어긋남</a-select-option>
            <a-select-option value="orphan">연결 안 된 페이지</a-select-option>
            <a-select-option value="stale">오래된 페이지</a-select-option>
            <a-select-option value="missing_entity">없는 페이지</a-select-option>
            <a-select-option value="broken_link">잘못된 연결</a-select-option>
          </a-select>
          <a-select v-model:value="filterSeverity" placeholder="중요도" allow-clear style="width: 110px" @change="load">
            <a-select-option value="high">높음</a-select-option>
            <a-select-option value="medium">보통</a-select-option>
            <a-select-option value="low">낮음</a-select-option>
          </a-select>
          <a-select v-model:value="filterResolvedStr" placeholder="처리 여부" allow-clear style="width: 130px" @change="load">
            <a-select-option value="unresolved">아직</a-select-option>
            <a-select-option value="resolved">처리됨</a-select-option>
          </a-select>
        </div>
      </template>

      <div v-if="loading" class="text-center py-12">
        <a-spin size="large" />
      </div>
      <div v-else-if="findings.length === 0" class="empty-state">
        <CheckCircleOutlined class="empty-state-icon" style="color: #10b981;" />
        <div class="text-base font-medium mb-1 text-gray-700">문제 없어요!</div>
        <div class="text-sm">지식베이스가 건강한 상태입니다 ✨</div>
        <a-button class="mt-4" :loading="running" @click="runLint">
          <SyncOutlined /> 다시 점검하기
        </a-button>
      </div>

      <div v-else class="space-y-2">
        <div
          v-for="item in findings"
          :key="item.id"
          class="border rounded-lg p-4 hover:bg-gray-50 transition"
          style="border-color: var(--color-border);"
        >
          <div class="flex items-start gap-3">
            <div
              class="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center"
              :class="severityBg(item.severity)"
            >
              <component :is="typeIconCmp(item.type)" />
            </div>

            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1 flex-wrap">
                <span class="text-xs font-medium px-2 py-0.5 rounded" :class="severityCls(item.severity)">
                  {{ severityLabel(item.severity) }}
                </span>
                <span class="text-xs text-gray-500 font-medium">{{ typeLabel(item.type) }}</span>
                <a-tag v-if="item.resolved_at" color="green" class="!m-0 !text-[10px]">처리됨</a-tag>
              </div>
              <div class="text-sm text-gray-800">{{ item.description }}</div>
              <div class="text-xs text-gray-400 mt-1">
                <span>발견: {{ dayjs(item.detected_at).format('YYYY-MM-DD HH:mm') }}</span>
                <span v-if="item.resolved_at"> · 해결: {{ dayjs(item.resolved_at).format('YYYY-MM-DD') }}</span>
              </div>
            </div>

            <a-button
              v-if="!item.resolved_at"
              size="small"
              @click="createIngest(item)"
            >
              <PlusOutlined /> 보충 자료 올리기
            </a-button>
          </div>
        </div>
      </div>
    </a-card>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { message } from 'ant-design-vue'
import {
  ThunderboltOutlined, CheckCircleOutlined, PlusOutlined, SyncOutlined,
  WarningOutlined, DisconnectOutlined, ClockCircleOutlined, QuestionCircleOutlined, BranchesOutlined,
} from '@ant-design/icons-vue'
import { lintApi } from '@/api/lint'
import type { LintFinding } from '@/api/types'
import AppLayout from '@/components/AppLayout.vue'

const router = useRouter()
const findings = ref<LintFinding[]>([])
const loading = ref(false)
const running = ref(false)
const filterType = ref<string | undefined>()
const filterSeverity = ref<string | undefined>()
const filterResolvedStr = ref<string | undefined>()

const typeLabels: Record<string, string> = {
  contradiction: '서로 어긋남',
  orphan: '연결되지 않은 페이지',
  stale: '오래된 페이지',
  missing_entity: '아직 만들지 않은 페이지',
  broken_link: '잘못된 연결',
}

const typeIcons: Record<string, any> = {
  contradiction: WarningOutlined,
  orphan: DisconnectOutlined,
  stale: ClockCircleOutlined,
  missing_entity: QuestionCircleOutlined,
  broken_link: BranchesOutlined,
}

const stats = computed(() => {
  const types = ['contradiction', 'orphan', 'stale', 'missing_entity', 'broken_link']
  const colorMap: Record<string, { color: string; iconCls: string }> = {
    contradiction: { color: 'text-red-600', iconCls: 'text-red-300 text-xl' },
    orphan: { color: 'text-orange-600', iconCls: 'text-orange-300 text-xl' },
    stale: { color: 'text-yellow-600', iconCls: 'text-yellow-300 text-xl' },
    missing_entity: { color: 'text-purple-600', iconCls: 'text-purple-300 text-xl' },
    broken_link: { color: 'text-pink-600', iconCls: 'text-pink-300 text-xl' },
  }
  return types.map(t => ({
    type: t,
    count: findings.value.filter(f => f.type === t && !f.resolved_at).length,
    colorCls: colorMap[t].color,
    iconCls: colorMap[t].iconCls,
    icon: typeIcons[t],
  }))
})

function typeLabel(t: string) { return typeLabels[t] || t }
function typeIconCmp(t: string) { return typeIcons[t] || WarningOutlined }

function severityLabel(s: string) {
  return ({ high: '높음', medium: '보통', low: '낮음' } as Record<string, string>)[s] || s
}
function severityBg(s: string) {
  return ({
    high: 'bg-red-100 text-red-600',
    medium: 'bg-orange-100 text-orange-600',
    low: 'bg-gray-100 text-gray-500',
  } as Record<string, string>)[s] || 'bg-gray-100 text-gray-500'
}
function severityCls(s: string) {
  return ({
    high: 'bg-red-50 text-red-600',
    medium: 'bg-orange-50 text-orange-600',
    low: 'bg-gray-100 text-gray-600',
  } as Record<string, string>)[s] || 'bg-gray-100 text-gray-600'
}

function toggleFilter(type: string) {
  filterType.value = filterType.value === type ? undefined : type
  load()
}

async function load() {
  loading.value = true
  try {
    const resolved = filterResolvedStr.value === 'resolved' ? true
      : filterResolvedStr.value === 'unresolved' ? false
      : undefined
    const res = await lintApi.listFindings({
      type: filterType.value,
      severity: filterSeverity.value,
      resolved,
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
    message.success('Lint를 시작했습니다. 잠시 후 결과가 표시됩니다.')
    setTimeout(load, 5000)
  } catch (e: any) {
    message.error(e?.response?.data?.detail || 'Lint 실행 실패')
  } finally {
    running.value = false
  }
}

function createIngest(finding: LintFinding) {
  router.push({
    path: '/upload',
    query: {
      type: 'new',
      title: `보강: ${typeLabel(finding.type)}`,
    },
  })
}

onMounted(load)
</script>
