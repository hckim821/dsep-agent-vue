<template>
  <span class="inline-flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-full" :class="config.cls">
    <span
      v-if="config.dot"
      class="w-1.5 h-1.5 rounded-full"
      :class="[config.dotCls, config.animated ? 'animate-pulse' : '']"
    ></span>
    <CheckCircleFilled v-else-if="config.icon === 'check'" class="text-xs" />
    <CloseCircleFilled v-else-if="config.icon === 'fail'" class="text-xs" />
    <ClockCircleOutlined v-else-if="config.icon === 'clock'" class="text-xs" />
    {{ config.label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CheckCircleFilled, CloseCircleFilled, ClockCircleOutlined } from '@ant-design/icons-vue'

const props = defineProps<{ status: string }>()

const map: Record<string, { label: string; cls: string; dot?: boolean; dotCls?: string; animated?: boolean; icon?: string }> = {
  pending:        { label: '곧 시작',     cls: 'bg-gray-100 text-gray-600',     icon: 'clock' },
  ocr_running:    { label: '이미지 읽는 중', cls: 'bg-blue-50 text-blue-600',  dot: true, dotCls: 'bg-blue-500', animated: true },
  ocr_done:       { label: '이미지 인식됨', cls: 'bg-blue-50 text-blue-600',   dot: true, dotCls: 'bg-blue-500' },
  ingest_running: { label: 'AI가 정리 중', cls: 'bg-indigo-50 text-indigo-600', dot: true, dotCls: 'bg-indigo-500', animated: true },
  ingest_done:    { label: '거의 완료',   cls: 'bg-indigo-50 text-indigo-600', dot: true, dotCls: 'bg-indigo-500' },
  done:           { label: '정리 완료',   cls: 'bg-green-50 text-green-700',    icon: 'check' },
  failed:         { label: '문제 발생',   cls: 'bg-red-50 text-red-600',        icon: 'fail' },
  running:        { label: '진행 중',     cls: 'bg-blue-50 text-blue-600',      dot: true, dotCls: 'bg-blue-500', animated: true },
  success:        { label: '성공',        cls: 'bg-green-50 text-green-700',    icon: 'check' },
}

const config = computed(() => map[props.status] || { label: props.status, cls: 'bg-gray-100 text-gray-600' })
</script>
