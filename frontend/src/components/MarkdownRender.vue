<template>
  <div class="prose max-w-none" v-html="rendered" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

const props = defineProps<{ content: string }>()

marked.use({
  renderer: {
    code(this: any, token: any) {
      const codeStr = typeof token === 'string' ? token : token?.text ?? ''
      const language = typeof token === 'object' ? token?.lang : undefined
      try {
        if (language && hljs.getLanguage(language)) {
          const out = hljs.highlight(codeStr, { language }).value
          return `<pre><code class="hljs language-${language}">${out}</code></pre>`
        }
        const out = hljs.highlightAuto(codeStr).value
        return `<pre><code class="hljs">${out}</code></pre>`
      } catch {
        return `<pre><code>${codeStr}</code></pre>`
      }
    },
  },
} as any)

const rendered = computed(() => {
  const text = props.content || ''
  return marked.parse(text, { async: false }) as string
})
</script>
