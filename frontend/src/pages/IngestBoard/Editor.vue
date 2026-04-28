<template>
  <AppLayout>
    <div class="max-w-5xl mx-auto">
      <!-- 헤더 -->
      <div class="flex justify-between items-center mb-4">
        <div>
          <a-button type="text" size="small" @click="$router.back()" class="-ml-2">
            <LeftOutlined /> 목록
          </a-button>
          <h2 class="text-2xl font-bold tracking-tight mt-1">새 Ingest 게시글</h2>
        </div>
        <div class="flex items-center gap-2 text-xs text-gray-400">
          <span class="kbd">Ctrl</span><span>+</span><span class="kbd">Enter</span>
          <span class="ml-1">저장</span>
        </div>
      </div>

      <a-form layout="vertical" :model="form" @finish="handleSubmit" @keydown.ctrl.enter="handleSubmit">
        <a-card :bordered="false" class="mb-4">
          <a-form-item label="제목" name="title" :rules="[{ required: true, message: '제목을 입력하세요' }]">
            <a-input
              v-model:value="form.title"
              size="large"
              placeholder="이 자료가 다루는 핵심 주제..."
              :maxlength="500"
              show-count
            />
          </a-form-item>

          <a-row :gutter="16">
            <a-col :span="8">
              <a-form-item label="타입" name="type">
                <a-select v-model:value="form.type" size="large">
                  <a-select-option value="new">
                    <span class="inline-flex items-center gap-2">
                      <span class="w-2 h-2 rounded-full bg-blue-500"></span> 신규 자료
                    </span>
                  </a-select-option>
                  <a-select-option value="correction">
                    <span class="inline-flex items-center gap-2">
                      <span class="w-2 h-2 rounded-full bg-orange-500"></span> 수정 제안
                    </span>
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="우선순위" name="priority">
                <a-select v-model:value="form.priority" size="large">
                  <a-select-option value="normal">일반</a-select-option>
                  <a-select-option value="urgent">
                    <span class="text-red-600 font-medium">⚡ 긴급 (즉시 처리)</span>
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="카테고리" name="category">
                <a-auto-complete
                  v-model:value="form.category"
                  size="large"
                  placeholder="entities, concepts, ..."
                  :options="categoryOptions"
                />
              </a-form-item>
            </a-col>
          </a-row>
        </a-card>

        <!-- 본문 — 탭 (작성/미리보기) -->
        <a-card :bordered="false" class="mb-4">
          <template #title>
            <span>본문</span>
            <span class="text-xs text-gray-400 ml-2 font-normal">Markdown 지원 · [[페이지명]]으로 위키링크</span>
          </template>
          <template #extra>
            <a-radio-group v-model:value="editMode" size="small" button-style="solid">
              <a-radio-button value="edit"><EditOutlined /> 작성</a-radio-button>
              <a-radio-button value="preview"><EyeOutlined /> 미리보기</a-radio-button>
              <a-radio-button value="split"><LayoutOutlined /> 분할</a-radio-button>
            </a-radio-group>
          </template>

          <div :class="editMode === 'split' ? 'grid grid-cols-2 gap-4' : ''">
            <a-textarea
              v-show="editMode === 'edit' || editMode === 'split'"
              v-model:value="form.body_md"
              :rows="18"
              placeholder="자료의 내용을 Markdown으로 작성하세요...

# 제목

본문에서 `[[다른 페이지]]`로 다른 위키 페이지를 참조할 수 있습니다.

```python
# 코드 블록도 지원
def hello():
    pass
```"
              class="!font-mono !text-sm"
              style="resize: vertical;"
            />
            <div
              v-show="editMode === 'preview' || editMode === 'split'"
              class="border rounded-lg p-4 overflow-auto"
              style="border-color: var(--color-border); max-height: 480px; min-height: 200px;"
            >
              <div v-if="!form.body_md" class="text-gray-300 text-center py-12 text-sm">
                <FileTextOutlined class="text-4xl mb-2 block" />
                미리보기가 여기 표시됩니다
              </div>
              <MarkdownRender v-else :content="form.body_md" />
            </div>
          </div>
        </a-card>

        <!-- 첨부 -->
        <a-card :bordered="false" class="mb-4" title="첨부 파일">
          <template #extra>
            <span class="text-xs text-gray-400">이미지/PDF/텍스트 (파일당 50MB)</span>
          </template>
          <a-upload-dragger
            v-model:file-list="fileList"
            :before-upload="() => false"
            accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.txt,.md"
            multiple
          >
            <p class="text-3xl text-gray-300 mb-2"><InboxOutlined /></p>
            <p class="text-sm font-medium">클릭하거나 파일을 드래그해서 업로드</p>
            <p class="text-xs text-gray-400 mt-1">png, jpg, gif, webp, pdf, txt, md</p>
          </a-upload-dragger>
        </a-card>

        <!-- 출처 정보 -->
        <a-card :bordered="false" class="mb-4">
          <template #title>
            <span>출처 정보</span>
            <span class="text-xs text-gray-400 ml-2 font-normal">선택 — 위키에 자동 인용됩니다</span>
          </template>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="출처 URL">
                <a-input v-model:value="form.source_url" placeholder="https://...">
                  <template #prefix><LinkOutlined class="text-gray-400" /></template>
                </a-input>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="출처 저자">
                <a-input v-model:value="form.source_author" placeholder="저자/매체명">
                  <template #prefix><UserOutlined class="text-gray-400" /></template>
                </a-input>
              </a-form-item>
            </a-col>
          </a-row>
        </a-card>

        <!-- 액션 바 -->
        <div class="sticky bottom-0 bg-white border-t mt-4 px-4 py-3 -mx-6 flex justify-between items-center" style="border-color: var(--color-border); margin-bottom: -24px;">
          <div class="text-xs text-gray-500">
            <span v-if="form.body_md.length > 0">{{ form.body_md.length.toLocaleString() }}자</span>
            <span v-else>—</span>
          </div>
          <div class="flex gap-3">
            <a-button @click="$router.back()" size="large">취소</a-button>
            <a-button type="primary" html-type="submit" :loading="submitting" size="large">
              <SaveOutlined /> 저장
            </a-button>
          </div>
        </div>
      </a-form>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  LeftOutlined, EditOutlined, EyeOutlined, LayoutOutlined,
  InboxOutlined, LinkOutlined, UserOutlined, SaveOutlined, FileTextOutlined,
} from '@ant-design/icons-vue'
import { ingestApi } from '@/api/ingest'
import AppLayout from '@/components/AppLayout.vue'
import MarkdownRender from '@/components/MarkdownRender.vue'

const router = useRouter()
const route = useRoute()
const submitting = ref(false)
const fileList = ref<any[]>([])
const editMode = ref<'edit' | 'preview' | 'split'>('split')

const form = reactive({
  title: '',
  body_md: '',
  type: 'new',
  priority: 'normal',
  category: '',
  source_url: '',
  source_author: '',
})

const categoryOptions = computed(() => [
  { value: 'entities' },
  { value: 'concepts' },
  { value: 'comparisons' },
])

onMounted(() => {
  if (route.query.title) form.title = route.query.title as string
  if (route.query.type) form.type = route.query.type as string
  if (route.query.category) form.category = route.query.category as string
  if (route.query.target_wiki_path) {
    form.body_md = `> 원본 페이지: \`${route.query.target_wiki_path}\`\n\n`
  }
})

async function handleSubmit() {
  if (!form.title.trim()) {
    message.warning('제목을 입력해주세요')
    return
  }
  if (!form.body_md.trim()) {
    message.warning('본문을 입력해주세요')
    return
  }

  submitting.value = true
  try {
    const res = await ingestApi.create({
      title: form.title,
      body_md: form.body_md,
      type: form.type,
      priority: form.priority,
      category: form.category || undefined,
      source_url: form.source_url || undefined,
      source_author: form.source_author || undefined,
    })

    const postId = res.data.id

    for (const f of fileList.value) {
      const fileObj = f.originFileObj || f
      if (fileObj instanceof File) {
        await ingestApi.uploadAttachment(postId, fileObj)
      }
    }

    message.success('게시글이 등록되었습니다')

    // urgent면 자동 실행
    if (form.priority === 'urgent') {
      try { await ingestApi.run(postId) } catch {}
    }

    router.push(`/ingest/${postId}`)
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '저장 실패')
  } finally {
    submitting.value = false
  }
}
</script>
