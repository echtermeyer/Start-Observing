<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useInsightStore } from '@/stores/insights'
import * as api from '@/services/api'
import type { InsightSeverity, Insight } from '@/types'

const insightStore = useInsightStore()
const selectedFilter = ref<InsightSeverity | 'all'>('all')
const isLoading = ref(true)
const error = ref<string | null>(null)

const filteredInsights = computed(() => {
  if (selectedFilter.value === 'all') return insightStore.insights
  return insightStore.insights.filter(i => i.severity === selectedFilter.value)
})

async function loadInsights() {
  try {
    isLoading.value = true
    error.value = null
    const response = await api.fetchInsights()
    insightStore.setInsights(response.insights)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load insights'
    console.error('Failed to load insights:', e)
  } finally {
    isLoading.value = false
  }
}

async function markAsRead(insight: Insight) {
  try {
    await api.updateInsight(insight.id, { read: true })
  } catch (e) {
    console.error('Failed to mark insight as read:', e)
  }
}

async function dismissInsight(insight: Insight) {
  try {
    await api.updateInsight(insight.id, { dismissed: true })
    // Remove from store
    const insights = insightStore.insights.filter(i => i.id !== insight.id)
    insightStore.setInsights(insights)
  } catch (e) {
    console.error('Failed to dismiss insight:', e)
  }
}

onMounted(() => {
  loadInsights()
})

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function getInsightContent(insight: Insight) {
  return insight.description || insight.title
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-[22px] font-semibold text-black">Insights</h1>
        <p class="text-[14px] text-gray-500 mt-1">AI-generated insights from your data</p>
      </div>
      <button @click="loadInsights" :disabled="isLoading" class="px-4 py-2 text-[13px] text-gray-600 border border-gray-200 rounded-md hover:bg-gray-50 disabled:opacity-50">
        {{ isLoading ? 'Loading...' : 'Refresh' }}
      </button>
    </div>

    <!-- Filters -->
    <div class="flex gap-2 mb-6">
      <button @click="selectedFilter = 'all'" :class="['px-3 py-1.5 rounded-md text-[13px] font-medium transition-colors', selectedFilter === 'all' ? 'bg-black text-white' : 'text-gray-600 hover:bg-gray-100']">All</button>
      <button @click="selectedFilter = 'critical'" :class="['px-3 py-1.5 rounded-md text-[13px] font-medium transition-colors', selectedFilter === 'critical' ? 'bg-red-500 text-white' : 'text-gray-600 hover:bg-gray-100']">Critical</button>
      <button @click="selectedFilter = 'warning'" :class="['px-3 py-1.5 rounded-md text-[13px] font-medium transition-colors', selectedFilter === 'warning' ? 'bg-amber-500 text-white' : 'text-gray-600 hover:bg-gray-100']">Warning</button>
      <button @click="selectedFilter = 'info'" :class="['px-3 py-1.5 rounded-md text-[13px] font-medium transition-colors', selectedFilter === 'info' ? 'bg-emerald-500 text-white' : 'text-gray-600 hover:bg-gray-100']">Info</button>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="py-12 text-center text-gray-500">Loading insights...</div>

    <!-- Error -->
    <div v-else-if="error" class="rounded-lg border border-red-200 bg-red-50 p-5">
      <p class="text-red-700">{{ error }}</p>
      <button @click="loadInsights" class="mt-2 text-red-600 underline text-sm">Try again</button>
    </div>

    <!-- List -->
    <div v-else class="space-y-3">
      <div v-for="insight in filteredInsights" :key="insight.id" class="p-5 rounded-lg border border-gray-200 group" @click="markAsRead(insight)">
        <div class="flex items-start gap-3">
          <div :class="['w-2 h-2 rounded-full mt-1.5 flex-shrink-0', insight.severity === 'critical' ? 'bg-red-500' : insight.severity === 'warning' ? 'bg-amber-500' : 'bg-emerald-500']"></div>
          <div class="flex-1">
            <p v-if="insight.title" class="text-[14px] font-medium text-black mb-1">{{ insight.title }}</p>
            <p class="text-[14px] text-gray-700 leading-relaxed">{{ getInsightContent(insight) }}</p>
            <div class="flex items-center gap-3 mt-3">
              <span class="text-[12px] text-gray-400 px-2 py-0.5 bg-gray-100 rounded">{{ insight.dataset_name }}</span>
              <span class="text-[12px] text-gray-400">{{ formatDate(insight.created_at) }}</span>
              <button
                @click.stop="dismissInsight(insight)"
                class="ml-auto text-[12px] text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      </div>
      <div v-if="filteredInsights.length === 0" class="py-12 text-center text-[14px] text-gray-400">
        {{ insightStore.insights.length === 0 ? 'No insights yet. Upload a dataset to generate insights.' : 'No insights match your filter' }}
      </div>
    </div>
  </div>
</template>
