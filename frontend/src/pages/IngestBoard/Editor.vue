<template>
  <AppLayout>
    <div class="max-w-5xl mx-auto">
      <div class="flex justify-between items-center mb-4">
        <div>
          <a-button type="text" size="small" @click="$router.back()" class="-ml-2">
            <LeftOutlined /> 뒤로
          </a-button>
          <h2 class="text-2xl font-bold tracking-tight mt-1">{{ isEdit ? '자료 수정하기' : '자료 올리기' }}</h2>
          <p class="text-gray-500 text-sm mt-1">
            <span v-if="isEdit && wasDone">이미 정리된 자료를 수정합니다. 다시 정리하면 지식베이스가 갱신됩니다.</span>
            <span v-else-if="isEdit">자료를 수정합니다</span>
            <span v-else>올린 자료를 AI가 분석해 지식베이스에 통합합니다</span>
          </p>
        </div>
        <div class="flex items-center gap-2 text-xs text-gray-400">
          <span class="kbd">Ctrl</span><span>+</span><span class="kbd">Enter</span>
          <span class="ml-1">저장</span>
        </div>
      </div>

      <!-- 안내 배너 -->
      <a-alert
        v-if="!isEdit"
        type="info"
        show-icon
        class="mb-4"
        message="자유롭게 작성하세요"
        description="제목은 비워두면 AI가 본문을 보고 만들어 드려요. 본문은 평소 메모하듯이 적으면, AI가 알아서 정리·분류해 지식베이스의 적절한 페이지에 통합합니다."
      />
      <a-alert
        v-else-if="wasDone"
        type="warning"
        show-icon
        class="mb-4"
        message="이 자료는 이미 지식베이스에 반영되었어요"
        description="수정만 저장하면 원본 자료만 바뀝니다. '다시 정리하기'로 저장하면 AI가 수정된 내용으로 지식베이스를 갱신합니다 (이전 정리 결과를 덮어씁니다)."
      />
      <a-alert
        v-else
        type="info"
        show-icon
        class="mb-4"
        message="아직 정리가 시작되지 않았어요"
        description="자유롭게 수정 후 저장하세요. 다음 정리 작업부터 수정된 내용이 반영됩니다."
      />

      <a-form layout="vertical" :model="form" @finish="handleSubmit" @keydown.ctrl.enter="handleSubmit">
        <a-card :bordered="false" class="mb-4">
          <a-form-item>
            <template #label>
              <span>제목</span>
              <span class="text-xs text-gray-400 font-normal ml-2">선택 — 비워두면 AI가 본문에서 자동으로 만들어요</span>
            </template>
            <a-input
              v-model:value="form.title"
              size="large"
              placeholder="비워두면 본문에서 자동 추출 — 예: 트랜스포머 아키텍처, 김연아 선수 프로필..."
              :maxlength="500"
              show-count
            />
          </a-form-item>

          <a-row :gutter="16">
            <a-col :span="8">
              <a-form-item label="자료 종류" name="type">
                <a-select v-model:value="form.type" size="large">
                  <a-select-option value="new">
                    <span class="inline-flex items-center gap-2">
                      <span class="w-2 h-2 rounded-full bg-blue-500"></span> 새 자료
                    </span>
                  </a-select-option>
                  <a-select-option value="correction">
                    <span class="inline-flex items-center gap-2">
                      <span class="w-2 h-2 rounded-full bg-orange-500"></span> 기존 페이지 수정 제안
                    </span>
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="처리 속도" name="priority">
                <a-select v-model:value="form.priority" size="large">
                  <a-select-option value="normal">
                    <span>일반 — 자동 일괄 처리</span>
                  </a-select-option>
                  <a-select-option value="urgent">
                    <span class="text-red-600 font-medium">⚡ 빨리 — 저장 즉시 시작</span>
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="주제 (선택)" name="category">
                <a-auto-complete
                  v-model:value="form.category"
                  size="large"
                  placeholder="예: 인물, 개념..."
                  :options="categoryOptions"
                />
              </a-form-item>
            </a-col>
          </a-row>
        </a-card>

        <a-card :bordered="false" class="mb-4">
          <template #title>
            <span>본문</span>
            <span class="text-xs text-gray-400 ml-2 font-normal">자유롭게 작성하세요 · 다른 페이지를 가리키려면 [[페이지명]]</span>
          </template>
          <template #extra>
            <a-radio-group v-model:value="editMode" size="small" button-style="solid">
              <a-radio-button value="edit"><EditOutlined /> 작성</a-radio-button>
              <a-radio-button value="preview"><EyeOutlined /> 미리보기</a-radio-button>
              <a-radio-button value="split"><LayoutOutlined /> 나란히</a-radio-button>
            </a-radio-group>
          </template>

          <div :class="editMode === 'split' ? 'grid grid-cols-2 gap-4' : ''">
            <a-textarea
              v-show="editMode === 'edit' || editMode === 'split'"
              v-model:value="form.body_md"
              :rows="18"
              placeholder="여기에 자료를 작성하거나 붙여넣으세요.

예: 회의록, 메모, 기사 본문, 위키 인용 등 무엇이든 OK.

# 큰 제목
## 작은 제목

- 목록 항목
- **굵게** 또는 *기울임*

다른 페이지를 가리키려면 [[페이지명]]"
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
                작성하면 여기에 결과 모양이 보입니다
              </div>
              <MarkdownRender v-else :content="form.body_md" />
            </div>
          </div>
        </a-card>

        <a-card v-if="!isEdit" :bordered="false" class="mb-4" title="이미지/파일 첨부">
          <template #extra>
            <span class="text-xs text-gray-400">스크린샷·PDF·텍스트 (파일당 50MB)</span>
          </template>
          <a-upload-dragger
            v-model:file-list="fileList"
            :before-upload="() => false"
            accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.txt,.md"
            multiple
          >
            <p class="text-3xl text-gray-300 mb-2"><InboxOutlined /></p>
            <p class="text-sm font-medium">클릭하거나 파일을 끌어다 놓으세요</p>
            <p class="text-xs text-gray-400 mt-1">이미지(png/jpg/gif/webp), 문서(pdf/txt/md)</p>
          </a-upload-dragger>
        </a-card>

        <a-card :bordered="false" class="mb-4">
          <template #title>
            <span>출처</span>
            <span class="text-xs text-gray-400 ml-2 font-normal">선택 — 자료의 신뢰성을 높여줍니다</span>
          </template>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="출처 링크">
                <a-input v-model:value="form.source_url" placeholder="https://...">
                  <template #prefix><LinkOutlined class="text-gray-400" /></template>
                </a-input>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="저자/출처명">
                <a-input v-model:value="form.source_author" placeholder="저자, 매체, 사이트명">
                  <template #prefix><UserOutlined class="text-gray-400" /></template>
                </a-input>
              </a-form-item>
            </a-col>
          </a-row>
        </a-card>

        <div class="sticky bottom-0 bg-white border-t mt-4 px-4 py-3 -mx-6 flex justify-between items-center" style="border-color: var(--color-border); margin-bottom: -24px;">
          <div class="text-xs text-gray-500">
            <span v-if="form.body_md.length > 0">{{ form.body_md.length.toLocaleString() }}자 작성됨</span>
            <span v-else>—</span>
          </div>
          <div class="flex gap-3">
            <a-button @click="$router.back()" size="large">취소</a-button>
            <!-- 신규 -->
            <a-button v-if="!isEdit" type="primary" html-type="submit" :loading="submitting" size="large">
              <SaveOutlined /> {{ form.priority === 'urgent' ? '저장하고 바로 시작' : '저장' }}
            </a-button>
            <!-- 편집(아직 미정리) -->
            <a-button v-else-if="!wasDone" type="primary" html-type="submit" :loading="submitting" size="large">
              <SaveOutlined /> 저장
            </a-button>
            <!-- 편집(완료) — 두 버튼 -->
            <template v-else>
              <a-button :loading="submitting && !rerunIntent" size="large" @click="onSaveOnly">
                <SaveOutlined /> 원본만 수정
              </a-button>
              <a-button type="primary" :loading="submitting && rerunIntent" size="large" @click="onSaveAndRerun">
                <SyncOutlined /> 저장하고 다시 정리
              </a-button>
            </template>
          </div>
        </div>
      </a-form>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import {
  LeftOutlined, EditOutlined, EyeOutlined, LayoutOutlined,
  InboxOutlined, LinkOutlined, UserOutlined, SaveOutlined,
  FileTextOutlined, SyncOutlined,
} from '@ant-design/icons-vue'
import { ingestApi } from '@/api/ingest'
import AppLayout from '@/components/AppLayout.vue'
import MarkdownRender from '@/components/MarkdownRender.vue'

const router = useRouter()
const route = useRoute()
const submitting = ref(false)
const rerunIntent = ref(false)
const fileList = ref<any[]>([])
const editMode = ref<'edit' | 'preview' | 'split'>('split')

const isEdit = computed(() => !!route.params.id)
const editingId = computed(() => Number(route.params.id))
const wasDone = ref(false)

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
  { value: 'entities', label: 'entities (인물·조직·제품)' },
  { value: 'concepts', label: 'concepts (개념·이론)' },
  { value: 'comparisons', label: 'comparisons (비교)' },
])

async function loadForEdit() {
  try {
    const res = await ingestApi.get(editingId.value)
    const post = res.data.post
    form.title = post.title || ''
    form.body_md = post.body_md || ''
    form.type = post.type || 'new'
    form.priority = post.priority || 'normal'
    form.category = post.category || ''
    form.source_url = post.source_url || ''
    form.source_author = post.source_author || ''
    wasDone.value = post.status === 'done'

    // 처리 중 잠금
    if (['ocr_running', 'ingest_running'].includes(post.status)) {
      message.warning('처리 중인 자료는 수정할 수 없습니다')
      router.replace(`/uploads/${editingId.value}`)
    }
  } catch {
    message.error('자료를 불러올 수 없습니다')
    router.replace('/uploads')
  }
}

onMounted(() => {
  if (isEdit.value) {
    loadForEdit()
    return
  }
  // 신규 생성 시 쿼리 파라미터로 prefill
  if (route.query.title) form.title = route.query.title as string
  if (route.query.type) form.type = route.query.type as string
  if (route.query.category) form.category = route.query.category as string
  if (route.query.target_wiki_path) {
    form.body_md = `> 원본 페이지: \`${route.query.target_wiki_path}\`\n\n`
  }
})

function onSaveOnly() {
  rerunIntent.value = false
  handleSubmit()
}

async function onSaveAndRerun() {
  rerunIntent.value = true
  const ok = await new Promise<boolean>((resolve) => {
    Modal.confirm({
      title: '다시 정리하시겠어요?',
      content: 'AI가 수정된 내용으로 지식베이스를 다시 작성합니다. 이전 정리 결과는 새 내용으로 덮어씌워집니다.',
      okText: '다시 정리',
      cancelText: '취소',
      onOk: () => resolve(true),
      onCancel: () => resolve(false),
    })
  })
  if (!ok) {
    rerunIntent.value = false
    return
  }
  handleSubmit()
}

async function handleSubmit() {
  if (!form.body_md.trim()) {
    message.warning('본문을 입력해주세요')
    return
  }

  submitting.value = true
  try {
    if (isEdit.value) {
      // 수정
      await ingestApi.update(editingId.value, {
        title: form.title || undefined,  // 빈 문자열이면 백엔드가 자동 추출
        body_md: form.body_md,
        type: form.type,
        priority: form.priority,
        category: form.category || undefined,
        source_url: form.source_url || undefined,
        source_author: form.source_author || undefined,
        rerun: wasDone.value && rerunIntent.value,
      })
      message.success(
        wasDone.value && rerunIntent.value
          ? '저장되었어요. AI가 다시 정리합니다.'
          : '저장되었어요'
      )
      router.push(`/uploads/${editingId.value}`)
      return
    }

    // 신규
    const res = await ingestApi.create({
      title: form.title || undefined,
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

    message.success('자료가 등록되었어요')
    if (form.priority === 'urgent') {
      try { await ingestApi.run(postId) } catch {}
    }
    router.push(`/uploads/${postId}`)
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '저장 실패'
    message.error(msg)
  } finally {
    submitting.value = false
  }
}
</script>
