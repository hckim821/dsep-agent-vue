<template>
  <AppLayout>
    <div class="flex h-[calc(100vh-104px)] gap-4 -m-6 p-6">
      <!-- 좌측 세션 목록 -->
      <div class="w-64 flex-shrink-0 flex flex-col bg-white rounded-xl border" style="border-color: var(--color-border);">
        <div class="p-3 border-b" style="border-color: var(--color-border);">
          <a-button type="primary" block @click="newSession">
            <PlusOutlined /> 새 채팅
          </a-button>
        </div>
        <div class="flex-1 overflow-y-auto p-2">
          <div v-if="sessions.length === 0" class="text-center text-gray-400 text-xs py-8">
            아직 채팅이 없습니다
          </div>
          <div
            v-for="s in sessions"
            :key="s.id"
            class="p-3 rounded-lg cursor-pointer mb-1 group transition"
            :class="currentSessionId === s.id ? 'bg-indigo-50 border border-indigo-200' : 'hover:bg-gray-50 border border-transparent'"
            @click="selectSession(s.id)"
          >
            <div class="flex items-start gap-2">
              <MessageOutlined class="mt-1 text-gray-400" :class="currentSessionId === s.id ? '!text-indigo-500' : ''" />
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium truncate" :class="currentSessionId === s.id ? 'text-indigo-700' : 'text-gray-900'">
                  {{ s.title || `채팅 #${s.id}` }}
                </div>
                <div class="text-xs text-gray-400 mt-0.5">{{ dayjs(s.updated_at).fromNow() }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 채팅 메인 -->
      <div class="flex-1 flex flex-col bg-white rounded-xl border overflow-hidden" style="border-color: var(--color-border);">
        <div v-if="!currentSessionId" class="flex-1 flex items-center justify-center">
          <div class="text-center max-w-md px-6">
            <div class="inline-flex w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-500 items-center justify-center mb-4 shadow-lg">
              <MessageOutlined class="text-2xl text-white" />
            </div>
            <h3 class="text-xl font-bold mb-2">무엇이 궁금하세요?</h3>
            <p class="text-gray-500 text-sm mb-6">
              지식베이스에 쌓인 내용을 바탕으로 답변해 드려요.<br />
              유익한 답변은 자료로 저장해서 지식을 키울 수 있어요.
            </p>
            <a-button type="primary" size="large" @click="newSession">
              <PlusOutlined /> 새 대화 시작
            </a-button>
          </div>
        </div>

        <template v-else>
          <!-- 세션 헤더 -->
          <div class="px-5 py-3 border-b flex items-center justify-between" style="border-color: var(--color-border);">
            <div>
              <div class="font-semibold">{{ currentSession?.title || `채팅 #${currentSessionId}` }}</div>
              <div class="text-xs text-gray-400">{{ messages.length }}개 메시지</div>
            </div>
            <div class="flex items-center gap-2">
              <a-tooltip title="이 대화의 유익한 내용을 새 자료로 저장">
                <a-button @click="toIngest" :disabled="messages.length === 0">
                  <FileTextOutlined /> 자료로 저장
                </a-button>
              </a-tooltip>
            </div>
          </div>

          <!-- 메시지 영역 -->
          <div class="flex-1 overflow-y-auto px-5 py-4" ref="messagesContainer" style="background: #fafbfc;">
            <!-- 빈 메시지 (세션은 있지만 메시지 없음) -->
            <div v-if="messages.length === 0 && !streaming" class="flex flex-col items-center justify-center h-full">
              <div class="text-center max-w-lg">
                <RobotOutlined class="text-4xl text-gray-300 mb-3" />
                <h4 class="text-base font-semibold text-gray-700 mb-2">무엇이든 자연어로 물어보세요</h4>
                <p class="text-sm text-gray-400 mb-6">지식베이스의 내용을 인용해서 답변해 드려요</p>
                <div class="grid grid-cols-1 gap-2">
                  <button
                    v-for="(s, i) in suggestions"
                    :key="i"
                    class="text-left px-4 py-3 bg-white border rounded-lg hover:border-indigo-400 hover:bg-indigo-50 transition text-sm"
                    style="border-color: var(--color-border);"
                    @click="useSuggestion(s)"
                  >
                    <span class="text-indigo-500 mr-2">▸</span>{{ s }}
                  </button>
                </div>
              </div>
            </div>

            <!-- 메시지 리스트 -->
            <div
              v-for="(msg, idx) in messages"
              :key="msg.id"
              class="mb-4 chat-bubble"
            >
              <!-- 같은 발신자 연속 메시지 묶기 -->
              <div :class="msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'">
                <div :class="msg.role === 'user' ? 'max-w-[75%]' : 'max-w-[85%]'">
                  <div v-if="!isContinuation(idx)" class="flex items-center gap-2 mb-1" :class="msg.role === 'user' ? 'justify-end' : ''">
                    <a-avatar
                      v-if="msg.role !== 'user'"
                      :size="22"
                      style="background: linear-gradient(135deg, #4f46e5, #7c3aed);"
                    ><RobotOutlined class="text-xs" /></a-avatar>
                    <span class="text-xs font-medium text-gray-700">
                      {{ msg.role === 'user' ? authStore.user?.display_name : 'AI 어시스턴트' }}
                    </span>
                    <span class="text-[10px] text-gray-400">{{ dayjs(msg.created_at).format('HH:mm') }}</span>
                  </div>
                  <div
                    class="rounded-2xl px-4 py-2.5"
                    :class="msg.role === 'user'
                      ? 'bg-indigo-500 text-white shadow-sm'
                      : 'bg-white border shadow-sm'"
                    :style="msg.role !== 'user' ? 'border-color: var(--color-border);' : ''"
                  >
                    <MarkdownRender v-if="msg.role === 'assistant'" :content="msg.content" />
                    <div v-else class="whitespace-pre-wrap text-[14.5px] leading-relaxed">{{ msg.content }}</div>
                  </div>
                  <div v-if="msg.citations_json && Array.isArray(msg.citations_json) && msg.citations_json.length" class="mt-1.5 flex flex-wrap gap-1">
                    <router-link
                      v-for="(c, ci) in msg.citations_json"
                      :key="ci"
                      :to="`/wiki?path=${encodeURIComponent(c.path || '')}`"
                      class="inline-flex items-center gap-1 text-xs text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded hover:bg-indigo-100"
                    >
                      <BookOutlined />[{{ ci + 1 }}] {{ c.title || c.path }}
                    </router-link>
                  </div>
                </div>
              </div>
            </div>

            <!-- 스트리밍 중 -->
            <div v-if="streaming" class="mb-4 chat-bubble">
              <div class="flex justify-start">
                <div class="max-w-[85%]">
                  <div class="flex items-center gap-2 mb-1">
                    <a-avatar :size="22" style="background: linear-gradient(135deg, #4f46e5, #7c3aed);"><RobotOutlined class="text-xs" /></a-avatar>
                    <span class="text-xs font-medium text-gray-700">AI 어시스턴트</span>
                    <span class="inline-flex gap-0.5 ml-1">
                      <span class="typing-dot w-1 h-1 bg-indigo-400 rounded-full"></span>
                      <span class="typing-dot w-1 h-1 bg-indigo-400 rounded-full"></span>
                      <span class="typing-dot w-1 h-1 bg-indigo-400 rounded-full"></span>
                    </span>
                  </div>
                  <div class="bg-white border shadow-sm rounded-2xl px-4 py-2.5" style="border-color: var(--color-border);">
                    <div v-if="!streamingContent" class="text-gray-400 text-sm italic">생각 중...</div>
                    <MarkdownRender v-else :content="streamingContent" />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 입력창 -->
          <div class="border-t p-4" style="border-color: var(--color-border);">
            <div class="relative">
              <a-textarea
                v-model:value="input"
                :rows="2"
                :auto-size="{ minRows: 2, maxRows: 8 }"
                placeholder="메시지를 입력하세요... (Enter: 전송, Shift+Enter: 줄바꿈)"
                @keydown="handleKeydown"
                :disabled="streaming"
                class="!pr-24"
              />
              <a-button
                type="primary"
                shape="round"
                :loading="streaming"
                :disabled="!input.trim()"
                @click="sendMessage"
                class="!absolute !bottom-2 !right-2"
              >
                <SendOutlined />
                전송
              </a-button>
            </div>
            <div class="text-[10px] text-gray-400 mt-2 flex items-center gap-3">
              <span><span class="kbd">Enter</span> 전송</span>
              <span><span class="kbd">Shift</span>+<span class="kbd">Enter</span> 줄바꿈</span>
            </div>
          </div>
        </template>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/ko'
import {
  PlusOutlined, MessageOutlined, FileTextOutlined,
  RobotOutlined, SendOutlined, BookOutlined,
} from '@ant-design/icons-vue'
import { chatApi } from '@/api/chat'
import type { ChatSession, ChatMessage } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/components/AppLayout.vue'
import MarkdownRender from '@/components/MarkdownRender.vue'

dayjs.extend(relativeTime)
dayjs.locale('ko')

const router = useRouter()
const authStore = useAuthStore()
const sessions = ref<ChatSession[]>([])
const messages = ref<ChatMessage[]>([])
const currentSessionId = ref<number | null>(null)
const input = ref('')
const streaming = ref(false)
const streamingContent = ref('')
const messagesContainer = ref<HTMLElement>()

const suggestions = [
  '지금까지 등록된 주요 주제는 어떤 것들이 있어?',
  '최근에 추가된 내용을 요약해줘',
  '서로 어긋나는 내용은 없는지 확인해줘',
]

const currentSession = computed(() => sessions.value.find(s => s.id === currentSessionId.value))

function isContinuation(idx: number): boolean {
  if (idx === 0) return false
  return messages.value[idx].role === messages.value[idx - 1].role
}

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

function useSuggestion(s: string) {
  input.value = s
  sendMessage()
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (!streaming.value) sendMessage()
  }
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
    let citations: any = null

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
          if (data.citations) citations = data.citations
          if (data.error) {
            message.error('AI 응답 오류: ' + data.error)
          }
          if (data.done) {
            messages.value.push({
              id: Date.now() + 1,
              role: 'assistant',
              content: streamingContent.value,
              citations_json: citations,
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
    message.success('대화 내용을 새 자료로 저장했어요. 검토 후 처리됩니다.')
    router.push(`/uploads/${res.data.post_id}`)
  } catch {
    message.error('저장 실패')
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
