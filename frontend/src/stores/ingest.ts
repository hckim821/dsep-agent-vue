import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ingestApi } from '@/api/ingest'
import type { IngestPost, IngestDetail } from '@/api/types'

export const useIngestStore = defineStore('ingest', () => {
  const posts = ref<IngestPost[]>([])
  const currentDetail = ref<IngestDetail | null>(null)
  const loading = ref(false)

  async function fetchPosts(params?: { status?: string; category?: string; skip?: number; limit?: number }) {
    loading.value = true
    try {
      const res = await ingestApi.list(params)
      posts.value = res.data
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id: number) {
    loading.value = true
    try {
      const res = await ingestApi.get(id)
      currentDetail.value = res.data
    } finally {
      loading.value = false
    }
  }

  return { posts, currentDetail, loading, fetchPosts, fetchDetail }
})
