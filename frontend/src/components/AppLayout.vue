<template>
  <a-layout style="min-height: 100vh">
    <a-layout-sider
      v-model:collapsed="collapsed"
      collapsible
      :width="240"
      class="app-sider"
      :trigger="null"
    >
      <div class="flex items-center gap-2 px-4 py-4 text-white border-b border-gray-700">
        <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-base font-bold flex-shrink-0">
          知
        </div>
        <div v-if="!collapsed" class="flex flex-col leading-tight">
          <span class="font-bold text-base tracking-tight">지식 허브</span>
          <span class="text-[10px] text-gray-400">Knowledge Hub</span>
        </div>
      </div>

      <!-- 새 자료 등록 CTA -->
      <div v-if="!collapsed" class="px-3 py-3 border-b border-gray-700">
        <router-link to="/upload">
          <a-button type="primary" block size="large">
            <PlusOutlined /> 자료 올리기
          </a-button>
        </router-link>
      </div>
      <div v-else class="px-2 py-3 border-b border-gray-700 flex justify-center">
        <a-tooltip title="자료 올리기" placement="right">
          <router-link to="/upload">
            <a-button type="primary" shape="circle" size="large">
              <PlusOutlined />
            </a-button>
          </router-link>
        </a-tooltip>
      </div>

      <a-menu theme="dark" mode="inline" :selected-keys="selectedKeys">
        <a-menu-item key="/home">
          <template #icon><HomeOutlined /></template>
          <router-link to="/home">홈</router-link>
        </a-menu-item>
        <a-menu-item key="/library">
          <template #icon><BookOutlined /></template>
          <router-link to="/library">지식 둘러보기</router-link>
        </a-menu-item>
        <a-menu-item key="/ask">
          <template #icon><MessageOutlined /></template>
          <router-link to="/ask">AI에게 묻기</router-link>
        </a-menu-item>
        <a-menu-item key="/uploads">
          <template #icon><InboxOutlined /></template>
          <router-link to="/uploads">내가 올린 자료</router-link>
        </a-menu-item>

        <a-menu-divider style="background: rgba(255,255,255,0.1); margin: 12px 8px;" />

        <a-menu-item key="/quality">
          <template #icon><SafetyCertificateOutlined /></template>
          <router-link to="/quality">품질 점검</router-link>
        </a-menu-item>
        <a-menu-item key="/rules" v-if="authStore.isAdmin">
          <template #icon><FileProtectOutlined /></template>
          <router-link to="/rules">작성 규칙</router-link>
        </a-menu-item>
      </a-menu>
    </a-layout-sider>

    <a-layout>
      <a-layout-header
        class="bg-white px-4 flex items-center justify-between"
        style="height: 56px; line-height: 56px; border-bottom: 1px solid var(--color-border);"
      >
        <div class="flex items-center gap-3 flex-1 min-w-0">
          <a-button type="text" @click="collapsed = !collapsed" class="!w-8 !h-8 flex items-center justify-center flex-shrink-0">
            <MenuFoldOutlined v-if="!collapsed" />
            <MenuUnfoldOutlined v-else />
          </a-button>
          <span class="text-base font-semibold text-gray-800">{{ pageTitle }}</span>
          <span v-if="pageDescription" class="text-xs text-gray-400 truncate">— {{ pageDescription }}</span>
        </div>

        <!-- 글로벌 검색 -->
        <div class="hidden md:block flex-shrink-0 mx-4">
          <a-input
            v-model:value="globalSearch"
            placeholder="지식베이스 전체 검색..."
            allow-clear
            style="width: 320px"
            @press-enter="doGlobalSearch"
          >
            <template #prefix><SearchOutlined class="text-gray-400" /></template>
          </a-input>
        </div>

        <div class="flex items-center gap-2 flex-shrink-0">
          <a-tooltip title="도움말">
            <a-button type="text" shape="circle" @click="showHelp = true">
              <QuestionCircleOutlined />
            </a-button>
          </a-tooltip>
          <a-dropdown>
            <div class="flex items-center gap-2 cursor-pointer hover:bg-gray-50 px-2 py-1 rounded-lg" style="line-height: 1.4;">
              <a-avatar
                :size="32"
                style="background: linear-gradient(135deg, #4f46e5, #7c3aed);"
              >{{ avatarLetter }}</a-avatar>
              <div class="hidden lg:flex flex-col text-left">
                <span class="text-sm font-medium text-gray-900 leading-tight">{{ authStore.user?.display_name }}</span>
                <span class="text-xs text-gray-400 leading-tight">{{ roleLabel }}</span>
              </div>
              <DownOutlined class="text-xs text-gray-400" />
            </div>
            <template #overlay>
              <a-menu>
                <a-menu-item disabled>
                  <div class="text-xs text-gray-400">{{ authStore.user?.email }}</div>
                </a-menu-item>
                <a-menu-divider />
                <a-menu-item @click="authStore.logout()">
                  <LogoutOutlined /> 로그아웃
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </a-layout-header>

      <a-layout-content style="padding: 24px; overflow-y: auto;">
        <slot />
      </a-layout-content>
    </a-layout>

    <!-- 도움말 모달 -->
    <a-modal v-model:open="showHelp" title="처음 사용하시나요?" :footer="null" width="600px">
      <div class="space-y-4 text-sm">
        <div class="flex gap-3 items-start">
          <div class="w-9 h-9 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center flex-shrink-0">1</div>
          <div>
            <div class="font-semibold mb-1">자료를 올리세요</div>
            <div class="text-gray-600">왼쪽 위 <b>"자료 올리기"</b> 버튼으로 텍스트·이미지·PDF를 등록합니다.</div>
          </div>
        </div>
        <div class="flex gap-3 items-start">
          <div class="w-9 h-9 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center flex-shrink-0">2</div>
          <div>
            <div class="font-semibold mb-1">AI가 정리합니다</div>
            <div class="text-gray-600">올린 자료를 AI가 분석해 <b>지식베이스</b>의 페이지로 자동 통합합니다. 이미 있는 페이지는 보강되고, 없으면 새로 만들어집니다.</div>
          </div>
        </div>
        <div class="flex gap-3 items-start">
          <div class="w-9 h-9 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center flex-shrink-0">3</div>
          <div>
            <div class="font-semibold mb-1">물어보거나 둘러보세요</div>
            <div class="text-gray-600"><b>AI에게 묻기</b>로 자연어 질문을 하거나, <b>지식 둘러보기</b>에서 카테고리·연결 그래프로 탐색합니다.</div>
          </div>
        </div>
        <div class="flex gap-3 items-start">
          <div class="w-9 h-9 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center flex-shrink-0">4</div>
          <div>
            <div class="font-semibold mb-1">함께 가꿉니다</div>
            <div class="text-gray-600">지식이 잘못됐거나 빠졌으면 페이지에서 <b>"이 부분 수정 제안"</b>을 눌러 보강 자료를 등록할 수 있어요.</div>
          </div>
        </div>
      </div>
    </a-modal>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  HomeOutlined, BookOutlined, MessageOutlined, InboxOutlined,
  SafetyCertificateOutlined, FileProtectOutlined, PlusOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined, SearchOutlined,
  QuestionCircleOutlined, DownOutlined, LogoutOutlined,
} from '@ant-design/icons-vue'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const collapsed = ref(false)
const globalSearch = ref('')
const showHelp = ref(false)

const pageMeta: Record<string, { title: string; desc?: string }> = {
  '/home': { title: '홈', desc: '오늘의 활동과 빠른 액션' },
  '/library': { title: '지식 둘러보기', desc: 'AI가 정리한 지식베이스' },
  '/ask': { title: 'AI에게 묻기', desc: '자료 기반으로 답변합니다' },
  '/uploads': { title: '내가 올린 자료', desc: '등록한 자료 목록' },
  '/upload': { title: '자료 올리기', desc: '새 자료를 등록해 지식을 보강합니다' },
  '/quality': { title: '품질 점검', desc: '지식베이스의 빈틈과 모순' },
  '/rules': { title: '작성 규칙', desc: 'AI가 따라야 할 규칙' },
}

const selectedKeys = computed(() => {
  const segs = route.path.split('/').filter(Boolean)
  return segs.length ? ['/' + segs[0]] : ['/home']
})

const pageTitle = computed(() => pageMeta[selectedKeys.value[0]]?.title || '지식 허브')
const pageDescription = computed(() => pageMeta[selectedKeys.value[0]]?.desc)

const avatarLetter = computed(() =>
  (authStore.user?.display_name || authStore.user?.email || '?').charAt(0).toUpperCase()
)
const roleLabel = computed(() => {
  const r = authStore.user?.role
  return ({ admin: '관리자', editor: '편집자', viewer: '뷰어' } as Record<string, string>)[r ?? ''] || r || ''
})

function doGlobalSearch() {
  if (!globalSearch.value.trim()) return
  router.push({ path: '/library', query: { q: globalSearch.value.trim() } })
}
</script>
