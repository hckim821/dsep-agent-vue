<template>
  <a-badge :status="badgeStatus as any" :text="label" />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string }>()

const config: Record<string, { status: string; label: string }> = {
  pending:        { status: 'default',    label: '대기' },
  ocr_running:    { status: 'processing', label: 'OCR 중' },
  ocr_done:       { status: 'processing', label: 'OCR 완료' },
  ingest_running: { status: 'processing', label: '처리 중' },
  ingest_done:    { status: 'processing', label: 'Ingest 완료' },
  done:           { status: 'success',    label: '완료' },
  failed:         { status: 'error',      label: '실패' },
}

const badgeStatus = computed(() => config[props.status]?.status ?? 'default')
const label = computed(() => config[props.status]?.label ?? props.status)
</script>
