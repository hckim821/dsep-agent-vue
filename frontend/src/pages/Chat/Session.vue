<template>
  <AppLayout>
    <div class="flex h-[calc(100vh-120px)] gap-4">
      <div class="w-64 flex-shrink-0">
        <div class="flex justify-between items-center mb-3">
          <span class="font-bold">채팅 목록</span>
          <a-button size="small" type="primary" @click="newSession">새 채팅</a-button>
        </div>
        <div
          v-for="s in sessions"
          :key="s.id"
          class="p-3 rounded cursor-pointer hover:bg-gray-100 mb-1"
          :class="{ 'bg-blue-50 border border-blue-200': currentSessionId === s.id }"
          @click="selectSession(s.id)"
        >
          <div class="text-sm font-medium truncate">{{ s.title || `채팅 #${s.id}` }}</div>
          <div class="text-xs text-gray-400">{{ dayjs(s.updated_at).fromNow() }}</div>
        </div>
      </div>

      <div class="flex-1 flex flex-col">
        <div class="flex-1 overflow-y-auto p-4 bg-gray-50 rounded" ref="messagesContainer">
          <div v-for="msg in messages" :key="msg.id" class="mb-4">
            <div
              class="max-w-3xl"
              :class="msg.role === 'user' ? 'ml-auto' : ''"
            >
              <div class="text-xs text-gray-400 mb-1">
                {{ msg.role === 'user' ? '나' : 'AI' }}
              </div>
              <div
                class="rounded-lg p-3"
                :class="msg.role === 'user' ? 'bg-blue-500 text-white' : 'bg-white shadow'"
              >
                <MarkdownRender v-if="msg.role === 'assistant'" :content="msg.content" />
                <span v-else>{{ msg.content }}</span>
              </div>
            </div>
          </div>

          <div v-if="streaming" class="mb-4">
            <div class="text-xs text-gray-400 mb-1">AI</div>
            <div class="bg-white shadow rounded-lg p-3 max-w-3xl">
              <MarkdownRender :content="streamingContent" />
              <a-spin size="small" class="ml-2" />
            </div>
          </div>
        </div>

        <div class="mt-3 flex gap-2">
          <a-textarea
            v-model:value="input"
            :rows="2"
            placeholder="메시지를 입력하세요..."
            @press-enter.prevent="sendMessage"
            :disabled="streaming || !currentSessionId"
          />
          <div class="flex flex-col gap-1">
            <a-button
              type="primary"
              :loading="streaming"
              :disabled="!currentSessionId || !input.trim()"
              @click="sendMessage"
            >전송</a-button>
            <a-button
              size="small"
              :disabled="!currentSessionId || messages.length === 0"
              @click="toIngest"
            >정리하기</a-button>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/ko'
import { chatApi } from '@/api/chat'
import type { ChatSession, ChatMessage } from '@/api/types'
import AppLayout from '@/components/AppLayout.vue'
import MarkdownRender from '@/components/MarkdownRender.vue'

dayjs.extend(relativeTime)
dayjs.locale('ko')

const router = useRouter()
const sessions = ref<ChatSession[]>([])
const messages = ref<ChatMessage[]>([])
const currentSessionId = ref<number | null>(null)
const input = ref('')
const streaming = ref(false)
const streamingContent = ref('')
const messagesContainer = ref<HTMLElement>()

async function loadSessions() {
  const res = await chatApi.listSessions()
  sessions.value = res.data
}

async function selectSession(id: number) {
  currentSessionId.value = id
  const res = await chatApi.getMessages(id)
  messages.value = res.data
  await scrollBottom()
}

async function newSession() {
  const res = await chatApi.createSession()
  sessions.value.unshift(res.data)
  await selectSession(res.data.id)
}

async function sendMessage() {
  if (!input.value.trim() || !currentSessionId.value || streaming.value) return

  const content = input.value.trim()
  input.value = ''

  messages.value.push({
    id: Date.now(),
    role: 'user',
    content,
    citations_json: null,
    created_at: new Date().toISOString(),
  })
  await scrollBottom()

  streaming.value = true
  streamingContent.value = ''

  try {
    const response = await fetch(`/api/chat/sessions/${currentSessionId.value}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
      },
      body: JSON.stringify({ content }),
    })

    if (!response.body) throw new Error('스트림을 사용할 수 없습니다')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.delta) {
            streamingContent.value += data.delta
            await scrollBottom()
          }
          if (data.done) {
            messages.value.push({
              id: Date.now() + 1,
              role: 'assistant',
              content: streamingContent.value,
              citations_json: data.citations ?? null,
              created_at: new Date().toISOString(),
            })
            streamingContent.value = ''
          }
        } catch {
          // ignore malformed SSE chunks
        }
      }
    }
  } catch (e: any) {
    message.error('전송 실패: ' + e.message)
  } finally {
    streaming.value = false
    await loadSessions()
  }
}

async function toIngest() {
  if (!currentSessionId.value) return
  try {
    const res = await chatApi.toIngest(currentSessionId.value)
    message.success('Ingest 게시글이 생성되었습니다')
    router.push(`/ingest/${res.data.post_id}`)
  } catch {
    message.error('변환 실패')
  }
}

async function scrollBottom() {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

onMounted(async () => {
  await loadSessions()
  if (sessions.value.length > 0) {
    await selectSession(sessions.value[0].id)
  }
})
</script>
