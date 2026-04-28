<template>
  <AppLayout>
    <!-- 뷰 모드 토글 -->
    <div class="mb-4 flex items-center justify-between">
      <a-radio-group v-model:value="viewMode" button-style="solid">
        <a-radio-button value="doc"><FileTextOutlined /> 문서 뷰</a-radio-button>
        <a-radio-button value="graph"><ApartmentOutlined /> 그래프 뷰</a-radio-button>
      </a-radio-group>
      <div class="text-xs text-gray-400" v-if="viewMode === 'graph'">
        노드 더블클릭으로 페이지 이동 · 드래그로 위치 조정 · 휠로 확대/축소
      </div>
    </div>

    <!-- 그래프 뷰 -->
    <div v-show="viewMode === 'graph'" style="height: calc(100vh - 160px);">
      <WikiGraph @open-page="openPage" />
    </div>

    <!-- 문서 뷰 -->
    <div v-show="viewMode === 'doc'" class="flex gap-4" style="height: calc(100vh - 160px);">
      <!-- 좌측: 트리 + 검색 -->
      <div class="w-72 flex-shrink-0 flex flex-col bg-white rounded-xl border" style="border-color: var(--color-border);">
        <div class="p-3 border-b" style="border-color: var(--color-border);">
          <a-input
            v-model:value="searchQuery"
            placeholder="페이지 검색..."
            allow-clear
            @input="onSearchInput"
          >
            <template #prefix><SearchOutlined class="text-gray-400" /></template>
          </a-input>
        </div>
        <div class="flex-1 overflow-y-auto p-3">
          <a-spin v-if="treeLoading" />
          <div v-else-if="!allPages.length" class="empty-state">
            <BookOutlined class="empty-state-icon" />
            <div class="text-sm font-medium mb-1 text-gray-700">아직 정리된 페이지가 없어요</div>
            <div class="text-xs mb-3">자료를 올리면 AI가 페이지를 만들어요</div>
            <router-link to="/upload">
              <a-button type="primary" size="small">자료 올리기</a-button>
            </router-link>
          </div>
          <div v-else>
            <div v-for="(items, cat) in groupedPages" :key="cat" class="mb-3">
              <div class="flex items-center gap-1.5 text-xs font-semibold text-gray-500 tracking-wider px-2 py-1.5">
                <component :is="catIcon(cat)" class="text-gray-400" />
                <span>{{ catLabel(cat) }}</span>
                <span class="ml-auto text-gray-300 normal-case font-normal">{{ items.length }}</span>
              </div>
              <button
                v-for="p in items"
                :key="p.id"
                class="w-full text-left px-2 py-1.5 rounded text-sm hover:bg-gray-50 transition flex items-center gap-2"
                :class="currentPage?.id === p.id ? 'bg-indigo-50 text-indigo-700 font-medium' : 'text-gray-700'"
                @click="openPage(p.path)"
              >
                <FileOutlined class="text-xs flex-shrink-0" :class="currentPage?.id === p.id ? 'text-indigo-500' : 'text-gray-400'" />
                <span class="truncate">{{ p.title }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 중앙 본문 -->
      <div class="flex-1 flex flex-col min-w-0 bg-white rounded-xl border overflow-hidden" style="border-color: var(--color-border);">
        <!-- 빈 상태 -->
        <div v-if="!currentPage" class="flex-1 flex items-center justify-center">
          <div class="text-center max-w-md px-6">
            <BookOutlined class="text-5xl text-gray-300 mb-4" />
            <h3 class="text-xl font-bold mb-2 text-gray-700">읽고 싶은 페이지를 골라보세요</h3>
            <p class="text-gray-500 text-sm">왼쪽 목록에서 클릭하거나, 검색창에서 찾아보세요.</p>
          </div>
        </div>

        <template v-else>
          <!-- 페이지 헤더 -->
          <div class="px-6 py-4 border-b flex items-center justify-between gap-4" style="border-color: var(--color-border);">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2 text-xs text-gray-400 mb-1 font-mono">
                <span>{{ currentPage.path }}</span>
                <span v-if="currentPage.current_commit_sha" class="bg-gray-100 px-1.5 py-0.5 rounded text-gray-500">{{ currentPage.current_commit_sha.slice(0, 7) }}</span>
              </div>
              <h1 class="text-2xl font-bold tracking-tight truncate">{{ currentPage.title }}</h1>
              <div class="text-xs text-gray-500 mt-1">
                {{ dayjs(currentPage.updated_at).format('YYYY-MM-DD HH:mm') }} 수정 ·
                {{ dayjs(currentPage.updated_at).fromNow() }}
              </div>
            </div>
            <div class="flex gap-2 flex-shrink-0">
              <a-button @click="copyPath">
                <LinkOutlined /> 링크 복사
              </a-button>
              <a-button type="primary" @click="suggestCorrection">
                <EditOutlined /> 이 페이지 보강하기
              </a-button>
            </div>
          </div>

          <!-- 본문 -->
          <div class="flex-1 overflow-y-auto px-6 py-6">
            <MarkdownRender :content="currentPage.content || ''" :known-titles="knownTitles" />
          </div>
        </template>
      </div>

      <!-- 우측 패널 -->
      <div v-if="currentPage" class="w-72 flex-shrink-0 overflow-y-auto space-y-3">
        <a-card :bordered="false" :body-style="{ padding: '12px 16px' }">
          <template #title>
            <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">한눈에</span>
          </template>
          <div class="text-xs space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-gray-500">이 페이지를 참조하는 곳</span>
              <span class="font-medium">{{ backlinks.length }}개</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-gray-500">출처가 된 자료</span>
              <span class="font-medium">{{ sources.length }}개</span>
            </div>
            <div v-if="currentPage.category" class="flex items-center justify-between">
              <span class="text-gray-500">주제</span>
              <code class="text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">{{ currentPage.category }}</code>
            </div>
          </div>
        </a-card>

        <a-card :bordered="false" :body-style="{ padding: '12px 16px' }">
          <template #title>
            <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">참조하는 페이지</span>
          </template>
          <div v-if="backlinks.length === 0" class="text-gray-400 text-xs py-2">이 페이지를 가리키는 페이지가 아직 없어요</div>
          <button
            v-for="bl in backlinks"
            :key="bl.id"
            class="w-full text-left text-sm py-1.5 px-2 hover:bg-indigo-50 hover:text-indigo-600 rounded transition flex items-center gap-2"
            @click="openPage(bl.path)"
          >
            <ArrowLeftOutlined class="text-xs text-gray-400" />
            <span class="truncate">{{ bl.title }}</span>
          </button>
        </a-card>

        <a-card :bordered="false" :body-style="{ padding: '12px 16px' }">
          <template #title>
            <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">이 페이지의 출처 자료</span>
          </template>
          <div v-if="sources.length === 0" class="text-gray-400 text-xs py-2">출처 정보가 없어요</div>
          <div v-for="src in sources" :key="src.post_id" class="mb-2 last:mb-0">
            <router-link :to="`/uploads/${src.post_id}`" class="block p-2 hover:bg-gray-50 rounded transition">
              <div class="flex items-center gap-2 mb-1">
                <a-tag :color="src.relation === 'created' ? 'green' : 'blue'" class="!m-0 !text-[10px]">
                  {{ src.relation === 'created' ? '생성' : '수정' }}
                </a-tag>
                <span class="text-[10px] text-gray-400">{{ dayjs(src.created_at).fromNow() }}</span>
              </div>
              <div class="text-xs text-indigo-600 truncate">{{ src.title }}</div>
            </router-link>
          </div>
        </a-card>
      </div>
    </div>

    <!-- 검색 결과 모달 -->
    <a-modal
      v-model:open="searchModalOpen"
      title="검색 결과"
      :footer="null"
      width="640px"
    >
      <div v-if="searching" class="text-center py-8"><a-spin /></div>
      <div v-else-if="searchResults.length === 0" class="text-center py-8 text-gray-400">
        <SearchOutlined class="text-3xl mb-2" />
        <div class="text-sm">"{{ searchQuery }}"에 대한 결과가 없습니다</div>
      </div>
      <div v-else class="space-y-1">
        <div class="text-xs text-gray-400 mb-2">{{ searchResults.length }}개 결과</div>
        <button
          v-for="r in searchResults"
          :key="r.page_id"
          class="block w-full text-left p-3 hover:bg-indigo-50 rounded-lg transition border"
          style="border-color: transparent;"
          @click="onSearchSelect(r.path)"
        >
          <div class="font-medium text-gray-900 mb-1">{{ r.title }}</div>
          <div class="text-xs text-gray-400 font-mono mb-1">{{ r.path }}</div>
          <div v-if="r.snippet" class="text-sm text-gray-600 line-clamp-2">{{ r.snippet }}</div>
        </button>
      </div>
    </a-modal>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/ko'
import { message } from 'ant-design-vue'
import {
  SearchOutlined, BookOutlined, FileOutlined, LinkOutlined, EditOutlined,
  ArrowLeftOutlined, ApartmentOutlined, BlockOutlined, SwapOutlined, FolderOutlined,
  FileTextOutlined,
} from '@ant-design/icons-vue'
import { wikiApi } from '@/api/wiki'
import type { WikiPageDetail, WikiPage, SearchResult } from '@/api/types'
import AppLayout from '@/components/AppLayout.vue'
import MarkdownRender from '@/components/MarkdownRender.vue'
import WikiGraph from '@/components/WikiGraph.vue'

dayjs.extend(relativeTime)
dayjs.locale('ko')

const route = useRoute()
const router = useRouter()

const viewMode = ref<'doc' | 'graph'>('doc')
const allPages = ref<WikiPage[]>([])
const treeLoading = ref(false)
const currentPage = ref<WikiPageDetail | null>(null)
const backlinks = ref<WikiPage[]>([])
const sources = ref<any[]>([])
const searchQuery = ref('')
const searchResults = ref<SearchResult[]>([])
const searching = ref(false)
const searchModalOpen = ref(false)
let searchDebounce: number | null = null

const knownTitles = computed(() => new Set(allPages.value.map(p => p.title)))

const groupedPages = computed(() => {
  const groups: Record<string, WikiPage[]> = {}
  for (const p of allPages.value) {
    const cat = p.category || 'misc'
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(p)
  }
  // sort
  for (const key in groups) {
    groups[key].sort((a, b) => a.title.localeCompare(b.title))
  }
  return groups
})

function catIcon(cat: string) {
  return ({ entities: ApartmentOutlined, concepts: BlockOutlined, comparisons: SwapOutlined } as any)[cat] || FolderOutlined
}
function catLabel(cat: string) {
  return ({
    entities: '인물·조직·제품',
    concepts: '개념·이론',
    comparisons: '비교',
    misc: '기타',
  } as Record<string, string>)[cat] || cat
}

async function loadTree() {
  treeLoading.value = true
  try {
    const res = await wikiApi.listPages()
    allPages.value = res.data
  } finally {
    treeLoading.value = false
  }
}

async function openPage(path: string) {
  try {
    const res = await wikiApi.getByPath(path)
    currentPage.value = res.data
    const [blRes, srcRes] = await Promise.all([
      wikiApi.getBacklinks(res.data.id),
      wikiApi.getSources(res.data.id),
    ])
    backlinks.value = blRes.data
    sources.value = srcRes.data
  } catch {
    message.error('페이지를 불러올 수 없습니다')
  }
}

async function openByTitle(title: string) {
  // 트리에서 title로 매칭
  const found = allPages.value.find(p => p.title === title)
  if (found) {
    await openPage(found.path)
  } else {
    message.warning(`"${title}" 페이지를 찾을 수 없습니다`)
  }
}

function onSearchInput() {
  if (searchDebounce) clearTimeout(searchDebounce)
  if (!searchQuery.value.trim()) {
    searchModalOpen.value = false
    searchResults.value = []
    return
  }
  searchDebounce = window.setTimeout(async () => {
    searching.value = true
    searchModalOpen.value = true
    try {
      const res = await wikiApi.search(searchQuery.value)
      searchResults.value = res.data
    } finally {
      searching.value = false
    }
  }, 300)
}

function onSearchSelect(path: string) {
  searchModalOpen.value = false
  searchQuery.value = ''
  openPage(path)
}

function suggestCorrection() {
  if (!currentPage.value) return
  router.push({
    path: '/upload',
    query: {
      type: 'correction',
      target_wiki_path: currentPage.value.path,
      title: `보강: ${currentPage.value.title}`,
    },
  })
}

function copyPath() {
  if (!currentPage.value) return
  navigator.clipboard.writeText(currentPage.value.path)
  message.success('경로를 복사했습니다')
}

watch(() => route.query.path as string, (path) => {
  if (path) openPage(path)
})
watch(() => route.query.title as string, (title) => {
  if (title) openByTitle(title)
})

onMounted(async () => {
  await loadTree()
  if (route.query.view === 'graph') {
    viewMode.value = 'graph'
  }
  if (route.query.path) {
    await openPage(route.query.path as string)
  } else if (route.query.title) {
    await openByTitle(route.query.title as string)
  } else if (route.query.q) {
    searchQuery.value = route.query.q as string
    onSearchInput()
  }
})
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
