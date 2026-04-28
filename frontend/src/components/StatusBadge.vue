<template>
  <FriendlyStatus :status="status" />
</template>

<script setup lang="ts">
import FriendlyStatus from '@/components/FriendlyStatus.vue'
defineProps<{ status: string }>()
</script>
