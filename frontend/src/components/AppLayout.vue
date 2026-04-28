<template>
  <a-layout style="min-height: 100vh">
    <a-layout-sider
      v-model:collapsed="collapsed"
      collapsible
      :width="220"
      class="app-sider"
      :trigger="null"
    >
      <div class="flex items-center gap-2 px-4 py-4 text-white border-b border-gray-700">
        <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center font-bold flex-shrink-0">
          W
        </div>
        <span v-if="!collapsed" class="font-bold text-base tracking-tight">LLM Wiki</span>
      </div>
      <a-menu theme="dark" mode="inline" :selected-keys="selectedKeys">
        <a-menu-item key="/ingest">
          <template #icon><FileTextOutlined /></template>
          <router-link to="/ingest">Ingest 게시판</router-link>
        </a-menu-item>
        <a-menu-item key="/wiki">
          <template #icon><BookOutlined /></template>
          <router-link to="/wiki">위키 탐색</router-link>
        </a-menu-item>
        <a-menu-item key="/chat">
          <template #icon><MessageOutlined /></template>
          <router-link to="/chat">채팅</router-link>
        </a-menu-item>
        <a-menu-item key="/lint">
          <template #icon><BugOutlined /></template>
          <router-link to="/lint">Lint 결과</router-link>
        </a-menu-item>
        <a-menu-item key="/schema" v-if="authStore.isAdmin">
          <template #icon><SettingOutlined /></template>
          <router-link to="/schema">Schema 관리</router-link>
        </a-menu-item>
      </a-menu>
    </a-layout-sider>

    <a-layout>
      <a-layout-header
        class="bg-white px-6 flex items-center justify-between"
        style="height: 56px; line-height: 56px; border-bottom: 1px solid var(--color-border); padding-left: 16px;"
      >
        <div class="flex items-center gap-3">
          <a-button type="text" @click="collapsed = !collapsed" class="!w-8 !h-8 flex items-center justify-center">
            <MenuFoldOutlined v-if="!collapsed" />
            <MenuUnfoldOutlined v-else />
          </a-button>
          <a-breadcrumb>
            <a-breadcrumb-item>
              <HomeOutlined />
            </a-breadcrumb-item>
            <a-breadcrumb-item>{{ pageTitle }}</a-breadcrumb-item>
          </a-breadcrumb>
        </div>
        <div class="flex items-center gap-3">
          <a-tooltip title="API 문서">
            <a-button type="text" shape="circle" @click="openDocs">
              <ApiOutlined />
            </a-button>
          </a-tooltip>
          <a-dropdown>
            <div class="flex items-center gap-2 cursor-pointer hover:bg-gray-50 px-3 py-1 rounded-lg" style="line-height: 1.4;">
              <a-avatar
                :size="32"
                style="background: linear-gradient(135deg, #4f46e5, #7c3aed);"
              >{{ avatarLetter }}</a-avatar>
              <div class="flex flex-col text-left">
                <span class="text-sm font-medium text-gray-900 leading-tight">{{ authStore.user?.display_name }}</span>
                <span class="text-xs text-gray-400 leading-tight">{{ authStore.user?.role }}</span>
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
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  FileTextOutlined, BookOutlined, MessageOutlined, BugOutlined,
  SettingOutlined, MenuFoldOutlined, MenuUnfoldOutlined,
  HomeOutlined, ApiOutlined, DownOutlined, LogoutOutlined,
} from '@ant-design/icons-vue'

const authStore = useAuthStore()
const route = useRoute()
const collapsed = ref(false)

const selectedKeys = computed(() => {
  const segs = route.path.split('/').filter(Boolean)
  return segs.length ? ['/' + segs[0]] : ['/ingest']
})

const pageTitle = computed(() => {
  const map: Record<string, string> = {
    '/ingest': 'Ingest 게시판',
    '/wiki': '위키 탐색',
    '/chat': '채팅',
    '/lint': 'Lint 결과',
    '/schema': 'Schema 관리',
  }
  return map[selectedKeys.value[0]] || 'LLM Wiki'
})

const avatarLetter = computed(() =>
  (authStore.user?.display_name || authStore.user?.email || '?').charAt(0).toUpperCase()
)

function openDocs() {
  window.open('http://localhost:8000/api/docs', '_blank')
}
</script>
