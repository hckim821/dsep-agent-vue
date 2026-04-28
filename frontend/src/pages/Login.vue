<template>
  <div class="min-h-screen flex items-center justify-center relative overflow-hidden" style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #db2777 100%);">
    <!-- 배경 장식 -->
    <div class="absolute top-10 left-10 w-72 h-72 bg-white/10 rounded-full blur-3xl"></div>
    <div class="absolute bottom-10 right-10 w-96 h-96 bg-pink-300/20 rounded-full blur-3xl"></div>

    <div class="relative z-10 w-full max-w-md mx-4">
      <div class="text-center mb-8">
        <div class="inline-flex w-14 h-14 rounded-2xl bg-white/20 backdrop-blur items-center justify-center mb-4 shadow-lg">
          <span class="text-2xl font-bold text-white">W</span>
        </div>
        <h1 class="text-3xl font-bold text-white tracking-tight">LLM Wiki</h1>
        <p class="text-white/80 mt-2 text-sm">자료를 올리면 LLM이 위키를 빌드합니다</p>
      </div>

      <div class="bg-white rounded-2xl shadow-2xl p-8">
        <h2 class="text-lg font-semibold mb-6 text-gray-900">로그인</h2>
        <a-form layout="vertical" :model="form" @finish="handleLogin">
          <a-form-item label="이메일" name="email" :rules="[{ required: true, message: '이메일을 입력하세요' }]">
            <a-input
              v-model:value="form.email"
              size="large"
              placeholder="admin@llmwiki.local"
              autocomplete="email"
            >
              <template #prefix><MailOutlined class="text-gray-400" /></template>
            </a-input>
          </a-form-item>
          <a-form-item label="비밀번호" name="password" :rules="[{ required: true, message: '비밀번호를 입력하세요' }]">
            <a-input-password
              v-model:value="form.password"
              size="large"
              autocomplete="current-password"
            >
              <template #prefix><LockOutlined class="text-gray-400" /></template>
            </a-input-password>
          </a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            block
            size="large"
            :loading="loading"
            class="!h-11 !font-semibold"
          >로그인</a-button>
        </a-form>

        <a-divider style="margin: 20px 0; font-size: 12px; color: #9ca3af;">
          <span>또는</span>
        </a-divider>

        <a-button
          block
          size="large"
          @click="fillDemo"
          class="!h-11"
        >
          <ThunderboltOutlined /> 데모 계정으로 빠르게 입장
        </a-button>

        <div class="mt-4 text-xs text-gray-400 text-center">
          데모: admin@llmwiki.local · admin1234
        </div>
      </div>

      <div class="text-center mt-6 text-white/70 text-xs">
        Karpathy의 llm-wiki 패턴 · Vue 3 + FastAPI + vLLM
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'
import { MailOutlined, LockOutlined, ThunderboltOutlined } from '@ant-design/icons-vue'

const authStore = useAuthStore()
const router = useRouter()
const loading = ref(false)
const form = reactive({ email: '', password: '' })

async function handleLogin() {
  loading.value = true
  try {
    await authStore.login(form.email, form.password)
    message.success(`환영합니다, ${authStore.user?.display_name}님`)
    router.push('/ingest')
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '로그인 실패: 이메일/비밀번호를 확인하세요')
  } finally {
    loading.value = false
  }
}

function fillDemo() {
  form.email = 'admin@llmwiki.local'
  form.password = 'admin1234'
  handleLogin()
}
</script>
