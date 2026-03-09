<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDatasetStore } from '@/stores/datasets'
import { useInsightStore } from '@/stores/insights'
import * as api from '@/services/api'
import type { Insight } from '@/types'

const router = useRouter()
const datasetStore = useDatasetStore()
const insightStore = useInsightStore()
const isLoading = ref(true)
const error = ref<string | null>(null)

const recentInsights = computed(() => insightStore.insights.slice(0, 3))

async function loadData() {
  try {
    isLoading.value = true
    error.value = null

    const [datasetsRes, insightsRes] = await Promise.all([
      api.fetchDatasets(),
      api.fetchInsights()
    ])

    datasetStore.setDatasets(datasetsRes.datasets)
    insightStore.setInsights(insightsRes.insights)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load data'
    console.error('Failed to load dashboard data:', e)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadData()
})

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function getInsightContent(insight: Insight) {
  return insight.description || insight.title
}
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-[22px] font-semibold text-black">Overview</h1>
        <p class="text-[14px] text-gray-500 mt-1">Monitor your dashboards and insights</p>
      </div>
      <router-link to="/upload" class="inline-flex items-center gap-2 px-4 py-2 bg-black text-white text-[13px] font-medium rounded-md hover:bg-gray-800 transition-colors">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        Add Data Source
      </router-link>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="flex items-center justify-center py-20">
      <div class="text-gray-500">Loading...</div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="rounded-lg border border-red-200 bg-red-50 p-5 mb-8">
      <p class="text-red-700">{{ error }}</p>
      <button @click="loadData" class="mt-2 text-red-600 underline text-sm">Try again</button>
    </div>

    <template v-else>
      <!-- Stats -->
      <div class="grid grid-cols-3 gap-5 mb-8">
        <div class="p-5 rounded-lg border border-gray-200">
          <p class="text-[13px] text-gray-500">Active Dashboards</p>
          <p class="text-[28px] font-semibold text-black mt-1">{{ datasetStore.datasets.length }}</p>
        </div>
        <div class="p-5 rounded-lg border border-gray-200">
          <p class="text-[13px] text-gray-500">Total Insights</p>
          <p class="text-[28px] font-semibold text-black mt-1">{{ insightStore.insights.length }}</p>
        </div>
        <div class="p-5 rounded-lg border border-gray-200">
          <p class="text-[13px] text-gray-500">Critical Alerts</p>
          <p class="text-[28px] font-semibold text-red-600 mt-1">{{ insightStore.criticalInsights.length }}</p>
        </div>
      </div>

      <!-- Recent Insights -->
      <div class="rounded-lg border border-gray-200 mb-8">
        <div class="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 class="text-[14px] font-medium text-black">Recent Insights</h2>
          <router-link to="/feed" class="text-[13px] text-gray-500 hover:text-black">View all →</router-link>
        </div>
        <div v-if="recentInsights.length === 0" class="px-5 py-8 text-center text-gray-500 text-sm">
          No insights yet. Upload a dataset to generate insights.
        </div>
        <div v-else class="divide-y divide-gray-100">
          <div v-for="insight in recentInsights" :key="insight.id" class="px-5 py-4">
            <div class="flex items-start gap-3">
              <div :class="['w-2 h-2 rounded-full mt-1.5 flex-shrink-0', insight.severity === 'critical' ? 'bg-red-500' : insight.severity === 'warning' ? 'bg-amber-500' : 'bg-emerald-500']"></div>
              <div>
                <p class="text-[14px] text-gray-700 leading-relaxed">{{ getInsightContent(insight) }}</p>
                <div class="flex items-center gap-3 mt-2">
                  <span class="text-[12px] text-gray-400 px-2 py-0.5 bg-gray-100 rounded">{{ insight.dataset_name }}</span>
                  <span class="text-[12px] text-gray-400">{{ formatDate(insight.created_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Dashboards -->
      <div class="rounded-lg border border-gray-200">
        <div class="px-5 py-4 border-b border-gray-200">
          <h2 class="text-[14px] font-medium text-black">Dashboards</h2>
        </div>
        <div v-if="datasetStore.datasets.length === 0" class="px-5 py-8 text-center text-gray-500 text-sm">
          No dashboards yet. Upload a dataset to get started.
        </div>
        <div v-else class="divide-y divide-gray-100">
          <div
            v-for="dataset in datasetStore.datasets"
            :key="dataset.id"
            @click="router.push(`/datasets/${dataset.id}`)"
            class="px-5 py-4 flex items-center justify-between cursor-pointer hover:bg-gray-50 transition-colors"
          >
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-md bg-gray-100 flex items-center justify-center">
                <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" />
                </svg>
              </div>
              <div>
                <p class="text-[14px] font-medium text-black">{{ dataset.name.replace('.csv', '') }}</p>
                <p class="text-[12px] text-gray-400">{{ dataset.version_count }} versions · {{ (dataset.latest_row_count || dataset.latest_version?.row_count || 0).toLocaleString() }} rows</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-[12px] text-gray-400">{{ formatDate(dataset.updated_at || dataset.created_at) }}</span>
              <svg class="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
