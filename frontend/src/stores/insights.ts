import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Insight } from '@/types'

export const useInsightStore = defineStore('insights', () => {
  const insights = ref<Insight[]>([])
  const isLoading = ref(false)

  const criticalInsights = computed(() =>
    insights.value.filter(i => i.severity === 'critical')
  )

  const warningInsights = computed(() =>
    insights.value.filter(i => i.severity === 'warning')
  )

  const infoInsights = computed(() =>
    insights.value.filter(i => i.severity === 'info')
  )

  function setInsights(newInsights: Insight[]) {
    insights.value = newInsights
  }

  function addInsight(insight: Insight) {
    insights.value.unshift(insight)
  }

  function addInsights(newInsights: Insight[]) {
    insights.value = [...newInsights, ...insights.value]
  }

  return {
    insights,
    isLoading,
    criticalInsights,
    warningInsights,
    infoInsights,
    setInsights,
    addInsight,
    addInsights
  }
})
