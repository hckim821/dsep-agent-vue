<template>
  <a-timeline>
    <a-timeline-item
      v-for="job in jobs"
      :key="job.id"
      :color="jobColor(job.status)"
    >
      <div class="flex items-center justify-between gap-2">
        <span class="font-medium text-sm">{{ stageLabel(job.stage) }}</span>
        <StatusBadge :status="job.status" />
      </div>
      <div class="text-xs text-gray-500 mt-1">
        <span>{{ dayjs(job.started_at).format('HH:mm:ss') }}</span>
        <span v-if="job.finished_at"> → {{ dayjs(job.finished_at).format('HH:mm:ss') }}</span>
        <span v-if="duration(job)" class="text-gray-400 ml-1">({{ duration(job) }})</span>
      </div>
      <div v-if="job.tokens_used || job.model_used" class="text-xs text-gray-400 mt-1 flex flex-wrap gap-x-3 gap-y-1">
        <span v-if="job.tokens_used">
          <ThunderboltOutlined /> {{ job.tokens_used.toLocaleString() }} tokens
        </span>
        <span v-if="job.model_used">
          <RobotOutlined /> {{ job.model_used }}
        </span>
      </div>
    </a-timeline-item>
  </a-timeline>
</template>

<script setup lang="ts">
import dayjs from 'dayjs'
import { ThunderboltOutlined, RobotOutlined } from '@ant-design/icons-vue'
import type { IngestJob } from '@/api/types'
import StatusBadge from '@/components/StatusBadge.vue'

defineProps<{ jobs: IngestJob[] }>()

function jobColor(status: string) {
  return ({ running: 'blue', success: 'green', failed: 'red' } as Record<string, string>)[status] ?? 'gray'
}

function stageLabel(stage: string) {
  return ({ ocr: 'OCR (이미지 인식)', ingest: 'LLM Ingest (위키 통합)', lint: 'Lint (검증)' } as Record<string, string>)[stage] ?? stage
}

function duration(job: IngestJob): string | null {
  if (!job.finished_at) return null
  const start = dayjs(job.started_at)
  const end = dayjs(job.finished_at)
  const diff = end.diff(start, 'second', true)
  if (diff < 1) return `${Math.round(diff * 1000)}ms`
  if (diff < 60) return `${diff.toFixed(1)}s`
  return `${Math.floor(diff / 60)}m ${Math.round(diff % 60)}s`
}
</script>
