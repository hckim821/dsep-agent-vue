<template>
  <AppLayout>
    <div class="max-w-4xl mx-auto">
      <h2 class="text-xl font-bold mb-6">새 Ingest 게시글</h2>
      <a-form layout="vertical" @finish="handleSubmit">
        <a-form-item label="제목" :rules="[{ required: true }]" name="title">
          <a-input v-model:value="form.title" placeholder="제목을 입력하세요" />
        </a-form-item>

        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="타입" name="type">
              <a-select v-model:value="form.type">
                <a-select-option value="new">신규</a-select-option>
                <a-select-option value="correction">수정 제안</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="우선순위" name="priority">
              <a-select v-model:value="form.priority">
                <a-select-option value="normal">일반</a-select-option>
                <a-select-option value="urgent">긴급</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="카테고리" name="category">
              <a-input v-model:value="form.category" placeholder="concepts, entities..." />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="본문 (Markdown)">
          <a-textarea
            v-model:value="form.body_md"
            :rows="12"
            placeholder="내용을 입력하세요..."
            class="font-mono text-sm"
          />
        </a-form-item>

        <a-form-item label="이미지/파일 첨부">
          <a-upload
            v-model:file-list="fileList"
            :before-upload="() => false"
            accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.txt,.md"
            multiple
          >
            <a-button><UploadOutlined /> 파일 선택</a-button>
          </a-upload>
        </a-form-item>

        <a-collapse ghost class="mb-4">
          <a-collapse-panel key="1" header="출처 정보 (선택)">
            <a-row :gutter="16">
              <a-col :span="12">
                <a-form-item label="출처 URL">
                  <a-input v-model:value="form.source_url" placeholder="https://..." />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="출처 저자">
                  <a-input v-model:value="form.source_author" />
                </a-form-item>
              </a-col>
            </a-row>
          </a-collapse-panel>
        </a-collapse>

        <div class="flex gap-3">
          <a-button type="primary" html-type="submit" :loading="submitting">저장</a-button>
          <a-button @click="$router.back()">취소</a-button>
        </div>
      </a-form>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { UploadOutlined } from '@ant-design/icons-vue'
import { ingestApi } from '@/api/ingest'
import AppLayout from '@/components/AppLayout.vue'

const router = useRouter()
const route = useRoute()
const submitting = ref(false)
const fileList = ref<any[]>([])

const form = reactive({
  title: '',
  body_md: '',
  type: 'new',
  priority: 'normal',
  category: '',
  source_url: '',
  source_author: '',
})

onMounted(() => {
  if (route.query.title) form.title = route.query.title as string
  if (route.query.type) form.type = route.query.type as string
  if (route.query.category) form.category = route.query.category as string
  if (route.query.target_wiki_path) {
    form.body_md = `> 원본 페이지: \`${route.query.target_wiki_path}\`\n\n`
  }
})

async function handleSubmit() {
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
    router.push(`/ingest/${postId}`)
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '저장 실패')
  } finally {
    submitting.value = false
  }
}
</script>
