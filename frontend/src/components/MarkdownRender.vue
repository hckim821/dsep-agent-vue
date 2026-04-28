<template>
  <div class="prose max-w-none" v-html="rendered" @click="handleClick" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

const props = defineProps<{
  content: string
  knownTitles?: Set<string>
}>()

const router = useRouter()

marked.use({
  gfm: true,
  breaks: true,
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

function transformWikiLinks(text: string): string {
  return text.replace(/\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g, (_, target, alias) => {
    const display = (alias || target).trim()
    const cleanTarget = target.trim()
    const known = props.knownTitles
    const broken = known ? !known.has(cleanTarget) : false
    const cls = broken ? 'wiki-link broken' : 'wiki-link'
    const titleAttr = broken ? 'title="아직 위키에 없는 페이지"' : ''
    return `<a class="${cls}" data-wiki="${encodeURIComponent(cleanTarget)}" ${titleAttr}>${display}</a>`
  })
}

const rendered = computed(() => {
  const text = transformWikiLinks(props.content || '')
  return marked.parse(text, { async: false }) as string
})

function handleClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  const link = target.closest('a.wiki-link') as HTMLAnchorElement | null
  if (link) {
    e.preventDefault()
    const wikiTitle = decodeURIComponent(link.getAttribute('data-wiki') || '')
    if (wikiTitle) {
      router.push({ path: '/wiki', query: { title: wikiTitle } })
    }
  }
}
</script>
