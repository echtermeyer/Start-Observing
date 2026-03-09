<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import embed, { type VisualizationSpec } from 'vega-embed'

const props = defineProps<{
  spec: VisualizationSpec
  width?: number | 'container'
  height?: number
}>()

const chartRef = ref<HTMLDivElement | null>(null)
const error = ref<string | null>(null)
const loading = ref(true)

let view: any = null

async function renderChart() {
  if (!chartRef.value || !props.spec) return

  loading.value = true
  error.value = null

  // Clean up previous view
  if (view) {
    view.finalize()
    view = null
  }

  try {
    // Deep clone to strip Vue reactivity proxies
    const rawSpec = JSON.parse(JSON.stringify(props.spec))
    const spec = {
      ...rawSpec,
      width: props.width === 'container' ? 'container' : (props.width || 'container'),
      height: props.height || 200,
      autosize: { type: 'fit', contains: 'padding' }
    }

    const result = await embed(chartRef.value, spec as VisualizationSpec, {
      actions: false,
      renderer: 'svg'
    })

    view = result.view
  } catch (e) {
    console.error('Vega render error:', e)
    error.value = 'Failed to render chart'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  renderChart()
})

onUnmounted(() => {
  if (view) {
    view.finalize()
  }
})

watch(() => props.spec, () => {
  renderChart()
}, { deep: true })
</script>

<template>
  <div class="vega-chart-container w-full">
    <div v-if="loading" class="flex items-center justify-center h-48">
      <div class="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full"></div>
    </div>
    <div v-else-if="error" class="flex items-center justify-center h-48 text-red-500 text-sm">
      {{ error }}
    </div>
    <div ref="chartRef" class="w-full" :class="{ 'opacity-0': loading }"></div>
  </div>
</template>

<style>
.vega-chart-container .vega-embed {
  width: 100%;
}
</style>
