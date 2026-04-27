<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <a-card title="LLM Wiki 로그인" style="width: 400px">
      <a-form layout="vertical" @finish="handleLogin">
        <a-form-item label="이메일" name="email" :rules="[{ required: true }]">
          <a-input v-model:value="form.email" placeholder="admin@llmwiki.local" />
        </a-form-item>
        <a-form-item label="비밀번호" name="password" :rules="[{ required: true }]">
          <a-input-password v-model:value="form.password" />
        </a-form-item>
        <a-button type="primary" html-type="submit" block :loading="loading">
          로그인
        </a-button>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const loading = ref(false)
const form = reactive({ email: '', password: '' })

async function handleLogin() {
  loading.value = true
  try {
    await authStore.login(form.email, form.password)
    router.push('/ingest')
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '로그인 실패')
  } finally {
    loading.value = false
  }
}
</script>
