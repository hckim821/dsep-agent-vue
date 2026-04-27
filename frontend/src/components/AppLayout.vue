<template>
  <a-layout style="min-height: 100vh">
    <a-layout-sider v-model:collapsed="collapsed" collapsible>
      <div class="logo px-4 py-3 text-white font-bold text-lg">
        {{ collapsed ? 'W' : 'LLM Wiki' }}
      </div>
      <a-menu theme="dark" mode="inline" v-model:selectedKeys="selectedKeys">
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
      <a-layout-header class="bg-white px-6 flex items-center justify-between shadow">
        <span class="text-lg font-semibold">{{ pageTitle }}</span>
        <div class="flex items-center gap-3">
          <span class="text-gray-600">{{ authStore.user?.display_name }}</span>
          <a-button size="small" @click="authStore.logout">로그아웃</a-button>
        </div>
      </a-layout-header>
      <a-layout-content class="p-6">
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
  FileTextOutlined, BookOutlined, MessageOutlined,
  BugOutlined, SettingOutlined,
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
</script>
