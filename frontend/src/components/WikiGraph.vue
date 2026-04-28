<template>
  <div class="relative w-full h-full">
    <div ref="container" class="w-full h-full bg-white rounded-xl border" style="border-color: var(--color-border);" />

    <!-- 빈 상태 -->
    <div v-if="!loading && !nodeCount" class="absolute inset-0 flex items-center justify-center pointer-events-none">
      <div class="text-center">
        <NodeIndexOutlined class="text-5xl text-gray-300 mb-3" />
        <div class="text-gray-500">아직 그릴 페이지가 없습니다</div>
      </div>
    </div>

    <!-- 로딩 -->
    <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-white/80 rounded-xl">
      <a-spin size="large" />
    </div>

    <!-- 통계 -->
    <div v-if="!loading && nodeCount" class="absolute top-3 left-3 bg-white/95 backdrop-blur rounded-lg px-3 py-1.5 text-xs shadow border" style="border-color: var(--color-border);">
      <span class="text-gray-700 font-medium">노드 {{ nodeCount }}</span>
      <span class="mx-2 text-gray-300">·</span>
      <span class="text-gray-700 font-medium">링크 {{ edgeCount }}</span>
    </div>

    <!-- 범례 -->
    <div v-if="!loading && nodeCount" class="absolute top-3 right-3 bg-white/95 backdrop-blur rounded-lg px-3 py-2 text-xs shadow border space-y-1" style="border-color: var(--color-border);">
      <div class="text-gray-500 font-medium mb-1">카테고리</div>
      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-full" style="background:#4f46e5;"></span><span>entities</span></div>
      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-full" style="background:#7c3aed;"></span><span>concepts</span></div>
      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-full" style="background:#db2777;"></span><span>comparisons</span></div>
      <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-full" style="background:#9ca3af;"></span><span>misc</span></div>
    </div>

    <!-- 액션 -->
    <div class="absolute bottom-3 right-3 flex gap-2">
      <a-button size="small" @click="fitGraph">
        <ExpandOutlined /> 화면 맞춤
      </a-button>
      <a-button size="small" @click="reload" :loading="loading">
        <SyncOutlined /> 새로고침
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { Network } from 'vis-network/standalone'
import { DataSet } from 'vis-data/peer'
import { NodeIndexOutlined, ExpandOutlined, SyncOutlined } from '@ant-design/icons-vue'
import { wikiApi } from '@/api/wiki'

const container = ref<HTMLElement>()
const loading = ref(false)
const nodeCount = ref(0)
const edgeCount = ref(0)
let network: Network | null = null
let nodesDS: DataSet<any> | null = null
let edgesDS: DataSet<any> | null = null
const router = useRouter()
const pathById = new Map<number, string>()

async function reload() {
  loading.value = true
  try {
    const res = await wikiApi.getGraph()
    nodeCount.value = res.data.stats.node_count
    edgeCount.value = res.data.stats.edge_count
    pathById.clear()
    for (const n of res.data.nodes) pathById.set(n.id, n.path)

    // edges에 id 필드를 부여 (vis-data가 요구)
    const edgesWithId = res.data.edges.map((e, i) => ({ ...e, id: `e${i}` }))

    if (!nodesDS || !edgesDS) {
      nodesDS = new DataSet(res.data.nodes as any[])
      edgesDS = new DataSet(edgesWithId as any[])
    } else {
      nodesDS.clear()
      nodesDS.add(res.data.nodes as any[])
      edgesDS.clear()
      edgesDS.add(edgesWithId as any[])
    }

    if (!network && container.value) {
      network = new Network(
        container.value,
        { nodes: nodesDS as any, edges: edgesDS as any },
        {
          autoResize: true,
          nodes: {
            shape: 'dot',
            scaling: { min: 10, max: 40, label: { min: 12, max: 18 } },
            font: { face: 'Pretendard, sans-serif', size: 13, color: '#1f2937' },
            borderWidth: 2,
            borderWidthSelected: 3,
            color: { border: '#ffffff', highlight: { border: '#fff', background: '#facc15' } },
            shadow: { enabled: true, size: 4, x: 0, y: 2, color: 'rgba(15,23,42,0.15)' },
          },
          edges: {
            color: { color: '#cbd5e1', highlight: '#4f46e5', hover: '#4f46e5' },
            width: 1,
            smooth: { enabled: true, type: 'continuous', roundness: 0.4 },
            arrows: { to: { enabled: true, scaleFactor: 0.5 } },
          },
          physics: {
            enabled: true,
            barnesHut: {
              gravitationalConstant: -3000,
              centralGravity: 0.2,
              springLength: 130,
              springConstant: 0.04,
              damping: 0.4,
            },
            stabilization: { iterations: 200 },
          },
          interaction: {
            hover: true,
            tooltipDelay: 100,
            zoomView: true,
            navigationButtons: false,
          },
        }
      )

      network.on('doubleClick', (params) => {
        if (params.nodes && params.nodes.length) {
          const id = params.nodes[0]
          const path = pathById.get(id)
          if (path) router.push({ path: '/wiki', query: { path } })
        }
      })
    }

    setTimeout(() => network?.fit({ animation: { duration: 600, easingFunction: 'easeInOutQuad' } }), 300)
  } finally {
    loading.value = false
  }
}

function fitGraph() {
  network?.fit({ animation: { duration: 400, easingFunction: 'easeInOutQuad' } })
}

onMounted(reload)

onBeforeUnmount(() => {
  network?.destroy()
  network = null
})
</script>
