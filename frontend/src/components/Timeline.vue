<template>
  <a-timeline>
    <a-timeline-item
      v-for="job in jobs"
      :key="job.id"
      :color="jobColor(job.status)"
    >
      <div class="font-medium">{{ stageLabel(job.stage) }}</div>
      <div class="text-xs text-gray-500">
        시작: {{ fmt(job.started_at) }}
        <span v-if="job.finished_at"> → 완료: {{ fmt(job.finished_at) }}</span>
      </div>
      <div class="text-xs text-gray-500" v-if="job.tokens_used">
        토큰: {{ job.tokens_used.toLocaleString() }}
        <span v-if="job.model_used"> | 모델: {{ job.model_used }}</span>
      </div>
    </a-timeline-item>
  </a-timeline>
</template>

<script setup lang="ts">
import dayjs from 'dayjs'
import type { IngestJob } from '@/api/types'

defineProps<{ jobs: IngestJob[] }>()

function jobColor(status: string) {
  return ({ running: 'blue', success: 'green', failed: 'red' } as Record<string, string>)[status] ?? 'gray'
}

function stageLabel(stage: string) {
  return ({ ocr: 'OCR', ingest: 'Ingest', lint: 'Lint' } as Record<string, string>)[stage] ?? stage
}

function fmt(ts: string) {
  return dayjs(ts).format('HH:mm:ss')
}
</script>
