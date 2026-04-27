<template>
  <AppLayout>
    <div class="mb-4">
      <a-input-search
        v-model:value="searchQuery"
        placeholder="위키 검색 (제목, 내용)..."
        enter-button
        @search="doSearch"
        :loading="searching"
        style="max-width: 500px"
      />
      <div v-if="searchResults.length" class="mt-2 bg-white border rounded shadow-lg p-3" style="max-width: 500px">
        <div
          v-for="r in searchResults"
          :key="r.page_id"
          class="p-2 hover:bg-gray-50 cursor-pointer rounded"
          @click="openPage(r.path); searchResults = []"
        >
          <div class="font-medium">{{ r.title }}</div>
          <div class="text-xs text-gray-500">{{ r.path }}</div>
          <div class="text-sm text-gray-600 mt-1">{{ r.snippet }}</div>
        </div>
      </div>
    </div>

    <div class="flex gap-4" style="height: calc(100vh - 220px)">
      <div class="w-64 flex-shrink-0 overflow-y-auto border rounded bg-white p-3">
        <a-spin v-if="treeLoading" />
        <a-tree
          v-else
          :tree-data="treeData"
          :selected-keys="selectedKeys"
          default-expand-all
          @select="onTreeSelect"
        />
      </div>

      <div class="flex-1 overflow-y-auto border rounded bg-white p-6">
        <div v-if="!currentPage" class="text-gray-400 text-center py-20">
          좌측에서 페이지를 선택하세요
        </div>
        <div v-else>
          <div class="flex justify-between items-start mb-4">
            <div>
              <h1 class="text-2xl font-bold">{{ currentPage.title }}</h1>
              <div class="text-xs text-gray-400 mt-1">
                {{ currentPage.path }} · 수정: {{ dayjs(currentPage.updated_at).format('YYYY-MM-DD HH:mm') }}
              </div>
            </div>
            <a-button size="small" @click="suggestCorrection">이 페이지 수정 제안</a-button>
          </div>
          <MarkdownRender :content="processWikiLinks(currentPage.content || '')" />
        </div>
      </div>

      <div class="w-56 flex-shrink-0 overflow-y-auto">
        <div v-if="currentPage">
          <a-card size="small" title="백링크" class="mb-3">
            <div v-if="backlinks.length === 0" class="text-gray-400 text-xs">없음</div>
            <div
              v-for="bl in backlinks"
              :key="bl.id"
              class="text-sm text-blue-600 hover:underline cursor-pointer py-1"
              @click="openPage(bl.path)"
            >{{ bl.title }}</div>
          </a-card>

          <a-card size="small" title="출처" class="mb-3">
            <div v-if="sources.length === 0" class="text-gray-400 text-xs">없음</div>
            <div v-for="src in sources" :key="src.post_id" class="mb-2">
              <a-tag :color="src.relation === 'created' ? 'green' : 'blue'" class="text-xs">
                {{ src.relation === 'created' ? '생성' : '수정' }}
              </a-tag>
              <router-link :to="`/ingest/${src.post_id}`" class="text-xs text-blue-600 hover:underline block mt-1">
                {{ src.title }}
              </router-link>
            </div>
          </a-card>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { wikiApi } from '@/api/wiki'
import type { WikiPageDetail, WikiPage, SearchResult } from '@/api/types'
import AppLayout from '@/components/AppLayout.vue'
import MarkdownRender from '@/components/MarkdownRender.vue'
import { message } from 'ant-design-vue'

const route = useRoute()
const router = useRouter()

const treeData = ref<any[]>([])
const treeLoading = ref(false)
const selectedKeys = ref<string[]>([])
const currentPage = ref<WikiPageDetail | null>(null)
const backlinks = ref<WikiPage[]>([])
const sources = ref<any[]>([])
const searchQuery = ref('')
const searchResults = ref<SearchResult[]>([])
const searching = ref(false)

async function loadTree() {
  treeLoading.value = true
  try {
    const res = await wikiApi.listPages()
    treeData.value = buildTreeData(res.data)
  } finally {
    treeLoading.value = false
  }
}

function buildTreeData(pages: WikiPage[]): any[] {
  const byCategory: Record<string, WikiPage[]> = {}
  for (const p of pages) {
    const cat = p.category || 'misc'
    if (!byCategory[cat]) byCategory[cat] = []
    byCategory[cat].push(p)
  }
  return Object.entries(byCategory).map(([cat, items]) => ({
    key: `cat:${cat}`,
    title: cat,
    selectable: false,
    children: items.map(p => ({
      key: p.path,
      title: p.title,
      isLeaf: true,
    })),
  }))
}

async function openPage(path: string) {
  selectedKeys.value = [path]
  try {
    const res = await wikiApi.getByPath(path)
    currentPage.value = res.data
    const [blRes, srcRes] = await Promise.all([
      wikiApi.getBacklinks(res.data.id),
      wikiApi.getSources(res.data.id),
    ])
    backlinks.value = blRes.data
    sources.value = srcRes.data
  } catch (e) {
    message.error('페이지를 불러올 수 없습니다')
  }
}

function onTreeSelect(keys: string[]) {
  if (keys.length && !keys[0].startsWith('cat:')) {
    openPage(keys[0])
  }
}

async function doSearch() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  try {
    const res = await wikiApi.search(searchQuery.value)
    searchResults.value = res.data
  } finally {
    searching.value = false
  }
}

function processWikiLinks(content: string): string {
  return content.replace(/\[\[([^\]]+)\]\]/g, (_, title) => `**${title}**`)
}

function suggestCorrection() {
  if (!currentPage.value) return
  router.push({
    path: '/ingest/new',
    query: {
      type: 'correction',
      target_wiki_path: currentPage.value.path,
      title: `수정 제안: ${currentPage.value.title}`,
    },
  })
}

watch(() => route.query.path as string, (path) => {
  if (path) openPage(path)
}, { immediate: true })

onMounted(loadTree)
</script>
