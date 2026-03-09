<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDatasetStore } from '@/stores/datasets'
import * as api from '@/services/api'
import VegaChart from '@/components/VegaChart.vue'
import type { Dataset, DatasetVersion, ColumnSchema, TeamMember, Alert, ChatMessage, Visualization, MetricsResponse } from '@/types'

const route = useRoute()
const router = useRouter()
const datasetStore = useDatasetStore()

const activeTab = ref<'dashboard' | 'structure' | 'settings'>('dashboard')
const dataset = ref<Dataset | null>(null)
const versions = ref<DatasetVersion[]>([])
const schema = ref<ColumnSchema[]>([])
const metrics = ref<MetricsResponse | null>(null)
const teamMembers = ref<TeamMember[]>([])
const alerts = ref<Alert[]>([])
const chatHistory = ref<ChatMessage[]>([])

const isLoading = ref(true)
const isRefreshing = ref(false)
const chatMessage = ref('')
const isSendingMessage = ref(false)
const error = ref<string | null>(null)

// Visualizations
const visualizations = ref<Visualization[]>([])
const vizLoading = ref(true)
const vizError = ref<string | null>(null)

// Settings
const updateFrequency = ref('daily')
const emailAlerts = ref(true)
const weeklyDigest = ref(false)
const savingSettings = ref(false)

async function loadData() {
  const id = route.params.id as string
  isLoading.value = true
  error.value = null

  try {
    const [datasetRes, versionsRes, schemaRes, metricsRes, teamRes, alertsRes, chatRes] = await Promise.all([
      api.fetchDataset(id),
      api.fetchVersions(id),
      api.fetchSchema(id).catch(() => ({ schema: [] })),
      api.fetchMetrics(id).catch(() => null),
      api.fetchTeam(id),
      api.fetchAlerts({ dataset_id: id }),
      api.fetchChatHistory(id)
    ])

    dataset.value = datasetRes
    versions.value = versionsRes.versions
    schema.value = schemaRes.schema
    metrics.value = metricsRes
    teamMembers.value = teamRes.team
    alerts.value = alertsRes.alerts
    chatHistory.value = chatRes.messages

    // Add initial AI greeting if no chat history
    if (chatHistory.value.length === 0) {
      chatHistory.value = [{ id: 'greeting', dataset_id: id, role: 'assistant', content: 'Hi! I can help you understand your data. Ask me anything about trends, anomalies, or insights.', created_at: new Date().toISOString() }]
    }

    // Load dataset settings
    try {
      const settings = await api.fetchDatasetSettings(id)
      updateFrequency.value = settings.update_frequency
      emailAlerts.value = settings.email_alerts
      weeklyDigest.value = settings.weekly_digest
    } catch {
      // Use defaults
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load dataset'
    console.error('Failed to load dataset:', e)
  } finally {
    isLoading.value = false
  }
}

async function loadVisualizations() {
  const id = route.params.id as string
  vizLoading.value = true
  vizError.value = null

  try {
    const response = await api.fetchVisualizations(id)
    visualizations.value = response.visualizations
  } catch (e) {
    vizError.value = 'Failed to load visualizations. Make sure the backend is running.'
    console.error('Error loading visualizations:', e)
  } finally {
    vizLoading.value = false
  }
}

onMounted(async () => {
  await loadData()
  await loadVisualizations()
})

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatTime(d: string) {
  const date = new Date(d)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  if (hours < 1) return 'Just now'
  if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`
  const days = Math.floor(hours / 24)
  return `${days} day${days > 1 ? 's' : ''} ago`
}

async function refresh() {
  isRefreshing.value = true
  await loadVisualizations()
  isRefreshing.value = false
}

async function sendMessage() {
  if (!chatMessage.value.trim() || isSendingMessage.value) return

  const message = chatMessage.value
  chatMessage.value = ''
  isSendingMessage.value = true

  // Add user message immediately
  chatHistory.value.push({
    id: `temp-${Date.now()}`,
    dataset_id: route.params.id as string,
    role: 'user',
    content: message,
    created_at: new Date().toISOString()
  })

  try {
    const response = await api.sendChatMessage(route.params.id as string, message)
    // Update with real messages
    chatHistory.value[chatHistory.value.length - 1] = response.user_message
    chatHistory.value.push(response.assistant_message)
  } catch (e) {
    // Add error message
    chatHistory.value.push({
      id: `error-${Date.now()}`,
      dataset_id: route.params.id as string,
      role: 'assistant',
      content: 'Sorry, I encountered an error. Please try again.',
      created_at: new Date().toISOString()
    })
  } finally {
    isSendingMessage.value = false
  }
}

async function saveSettings() {
  savingSettings.value = true
  try {
    await api.updateDatasetSettings(route.params.id as string, {
      update_frequency: updateFrequency.value as any,
      email_alerts: emailAlerts.value,
      weekly_digest: weeklyDigest.value
    })
  } catch (e) {
    console.error('Failed to save settings:', e)
  } finally {
    savingSettings.value = false
  }
}

async function deleteDataset() {
  if (!confirm('Are you sure you want to delete this dataset? This action cannot be undone.')) return

  try {
    await api.deleteDataset(route.params.id as string)
    // Remove from store and navigate
    const datasets = datasetStore.datasets.filter(d => d.id !== route.params.id)
    datasetStore.setDatasets(datasets)
    router.push('/dashboard')
  } catch (e) {
    alert('Failed to delete dataset')
  }
}

async function acknowledgeAlert(alertId: string) {
  try {
    await api.acknowledgeAlert(alertId, true)
    alerts.value = alerts.value.filter(a => a.id !== alertId)
  } catch (e) {
    console.error('Failed to acknowledge alert:', e)
  }
}

const datasetName = computed(() => dataset.value?.name.replace('.csv', '') || 'Dataset')

const displayMetrics = computed(() => {
  if (!metrics.value) {
    return [
      { label: 'Total Records', value: '-', change: '', positive: true },
      { label: 'Avg. Value', value: '-', change: '', positive: true },
      { label: 'Null Rate', value: '-', change: '', positive: true },
      { label: 'Anomalies', value: '-', change: '', positive: true }
    ]
  }

  const m = metrics.value.metrics
  const c = metrics.value.changes || {}

  return [
    {
      label: 'Total Records',
      value: m.total_records.toLocaleString(),
      change: c.total_records_change ? `${c.total_records_change > 0 ? '+' : ''}${c.total_records_change}%` : '',
      positive: (c.total_records_change || 0) >= 0
    },
    {
      label: 'Avg. Value',
      value: m.avg_value ? `$${m.avg_value.toFixed(2)}` : 'N/A',
      change: c.avg_value_change ? `${c.avg_value_change > 0 ? '+' : ''}${c.avg_value_change}%` : '',
      positive: (c.avg_value_change || 0) >= 0
    },
    {
      label: 'Null Rate',
      value: `${m.null_rate}%`,
      change: c.null_rate_change ? `${c.null_rate_change > 0 ? '+' : ''}${c.null_rate_change}%` : '',
      positive: (c.null_rate_change || 0) <= 0
    },
    {
      label: 'Anomalies',
      value: m.anomaly_count.toString(),
      change: c.anomaly_change ? `${c.anomaly_change > 0 ? '+' : ''}${c.anomaly_change}` : '',
      positive: (c.anomaly_change || 0) <= 0
    }
  ]
})
</script>

<template>
  <div class="flex flex-col h-[calc(100vh-64px)]">
    <!-- Fixed Header -->
    <div class="flex-shrink-0 bg-white pb-0">
      <!-- Back & Header -->
      <div class="flex items-center gap-4 mb-6">
        <button @click="router.push('/dashboard')" class="p-1.5 rounded-md hover:bg-gray-100 transition-colors">
          <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
        </button>
        <div class="flex-1">
          <h1 class="text-[22px] font-semibold text-black">{{ datasetName }}</h1>
          <p class="text-[13px] text-gray-500">Last updated {{ versions[0] ? formatDate(versions[0].uploaded_at || versions[0].created_at || '') : '-' }}</p>
        </div>
        <button
          @click="refresh"
          :disabled="isRefreshing"
          class="inline-flex items-center gap-2 px-4 py-2 text-[13px] text-gray-600 border border-gray-200 rounded-md hover:border-gray-300 hover:bg-gray-50 disabled:opacity-50 transition-all"
        >
          <svg :class="['w-4 h-4', isRefreshing ? 'animate-spin' : '']" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
          {{ isRefreshing ? 'Refreshing...' : 'Refresh' }}
        </button>
        <router-link to="/upload" class="px-4 py-2 bg-black text-white text-[13px] font-medium rounded-md hover:bg-gray-800 transition-colors">
          Upload Version
        </router-link>
      </div>

      <!-- Tabs -->
      <div class="border-b border-gray-200">
        <nav class="flex gap-6">
          <button
            @click="activeTab = 'dashboard'"
            :class="['pb-3 text-[14px] font-medium border-b-2 transition-colors', activeTab === 'dashboard' ? 'border-black text-black' : 'border-transparent text-gray-500 hover:text-black']"
          >
            Dashboard
          </button>
          <button
            @click="activeTab = 'structure'"
            :class="['pb-3 text-[14px] font-medium border-b-2 transition-colors', activeTab === 'structure' ? 'border-black text-black' : 'border-transparent text-gray-500 hover:text-black']"
          >
            Structure & Versions
          </button>
          <button
            @click="activeTab = 'settings'"
            :class="['pb-3 text-[14px] font-medium border-b-2 transition-colors', activeTab === 'settings' ? 'border-black text-black' : 'border-transparent text-gray-500 hover:text-black']"
          >
            Settings
          </button>
        </nav>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="py-12 text-center">
      <div class="animate-spin h-6 w-6 border-2 border-black border-t-transparent rounded-full mx-auto"></div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="py-12 text-center">
      <p class="text-red-600 mb-4">{{ error }}</p>
      <button @click="loadData" class="text-gray-600 underline">Try again</button>
    </div>

    <!-- Dashboard Tab -->
    <div v-else-if="activeTab === 'dashboard'" class="flex gap-6 flex-1 min-h-0 pt-6">
      <!-- Main Content - Scrollable -->
      <div class="flex-1 overflow-y-auto space-y-6 min-w-0 pr-2">
        <!-- Metrics -->
        <div class="grid grid-cols-4 gap-4">
          <div v-for="metric in displayMetrics" :key="metric.label" class="p-4 rounded-lg border border-gray-200">
            <p class="text-[12px] text-gray-500 mb-1">{{ metric.label }}</p>
            <p class="text-[20px] font-semibold text-black">{{ metric.value }}</p>
            <p v-if="metric.change" :class="['text-[12px] mt-1', metric.positive ? 'text-emerald-600' : 'text-red-600']">{{ metric.change }}</p>
          </div>
        </div>

        <!-- Visualization Loading -->
        <div v-if="vizLoading" class="py-12 text-center">
          <div class="animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-3"></div>
          <p class="text-[13px] text-gray-500">Generating visualizations...</p>
        </div>

        <!-- Visualization Error -->
        <div v-else-if="vizError" class="p-6 rounded-lg border border-amber-200 bg-amber-50">
          <p class="text-[14px] text-amber-800">{{ vizError }}</p>
          <p class="text-[12px] text-amber-600 mt-2">Run: <code class="bg-amber-100 px-1.5 py-0.5 rounded">cd backend && python server.py</code></p>
        </div>

        <!-- Dynamic Vega Charts -->
        <template v-else>
          <div class="grid grid-cols-2 gap-6">
            <div
              v-for="viz in visualizations.slice(0, 2)"
              :key="viz.id"
              class="p-5 rounded-lg border border-gray-200"
            >
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-[14px] font-medium text-black">{{ viz.title }}</h3>
                <span class="text-[12px] text-gray-400">{{ viz.description }}</span>
              </div>
              <VegaChart :spec="viz.spec" :height="180" />
            </div>
          </div>

          <div
            v-for="viz in visualizations.slice(2, 3)"
            :key="viz.id"
            class="p-5 rounded-lg border border-gray-200"
          >
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-[14px] font-medium text-black">{{ viz.title }}</h3>
              <span class="text-[12px] text-gray-400">{{ viz.description }}</span>
            </div>
            <VegaChart :spec="viz.spec" :height="200" />
          </div>

          <div class="grid grid-cols-2 gap-6">
            <div
              v-for="viz in visualizations.slice(3)"
              :key="viz.id"
              class="p-5 rounded-lg border border-gray-200"
            >
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-[14px] font-medium text-black">{{ viz.title }}</h3>
                <span class="text-[12px] text-gray-400">{{ viz.description }}</span>
              </div>
              <VegaChart :spec="viz.spec" :height="200" />
            </div>
          </div>
        </template>

        <div class="h-6"></div>
      </div>

      <!-- Sidebar - Fixed height -->
      <div class="w-80 flex-shrink-0 space-y-6 overflow-y-auto">
        <!-- Alerts -->
        <div class="rounded-lg border border-gray-200 overflow-hidden">
          <div class="px-4 py-3 border-b border-gray-200 bg-gray-50">
            <h3 class="text-[13px] font-medium text-black">Alerts</h3>
          </div>
          <div v-if="alerts.length === 0" class="px-4 py-6 text-center text-[13px] text-gray-400">
            No active alerts
          </div>
          <div v-else class="divide-y divide-gray-100 max-h-48 overflow-y-auto">
            <div v-for="alert in alerts" :key="alert.id" class="px-4 py-3 group">
              <div class="flex items-start gap-2">
                <div :class="['w-2 h-2 rounded-full mt-1.5 flex-shrink-0', alert.severity === 'critical' ? 'bg-red-500' : alert.severity === 'warning' ? 'bg-amber-500' : 'bg-blue-500']"></div>
                <div class="flex-1">
                  <p class="text-[13px] text-gray-700">{{ alert.message }}</p>
                  <div class="flex items-center justify-between mt-1">
                    <p class="text-[11px] text-gray-400">{{ formatTime(alert.created_at) }}</p>
                    <button @click="acknowledgeAlert(alert.id)" class="text-[11px] text-gray-400 hover:text-gray-600 opacity-0 group-hover:opacity-100">
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- AI Chat -->
        <div class="rounded-lg border border-gray-200 overflow-hidden flex flex-col" style="height: 380px;">
          <div class="px-4 py-3 border-b border-gray-200 bg-gray-50">
            <h3 class="text-[13px] font-medium text-black">Ask AI</h3>
          </div>
          <div class="flex-1 overflow-y-auto p-4 space-y-3">
            <div v-for="msg in chatHistory" :key="msg.id" :class="['flex', msg.role === 'user' ? 'justify-end' : 'justify-start']">
              <div :class="['max-w-[85%] px-3 py-2 rounded-lg text-[13px]', msg.role === 'user' ? 'bg-black text-white' : 'bg-gray-100 text-gray-700']">
                {{ msg.content }}
              </div>
            </div>
            <div v-if="isSendingMessage" class="flex justify-start">
              <div class="bg-gray-100 text-gray-500 px-3 py-2 rounded-lg text-[13px]">
                Thinking...
              </div>
            </div>
          </div>
          <div class="p-3 border-t border-gray-200">
            <div class="flex gap-2">
              <input
                v-model="chatMessage"
                @keyup.enter="sendMessage"
                type="text"
                placeholder="Ask about your data..."
                :disabled="isSendingMessage"
                class="flex-1 px-3 py-2 text-[13px] border border-gray-200 rounded-md focus:outline-none focus:border-gray-400 disabled:opacity-50"
              />
              <button @click="sendMessage" :disabled="isSendingMessage" class="px-3 py-2 bg-black text-white rounded-md hover:bg-gray-800 disabled:opacity-50 transition-colors">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Structure Tab -->
    <div v-else-if="activeTab === 'structure'" class="space-y-6 pt-6 overflow-y-auto flex-1">
      <!-- Stats -->
      <div class="grid grid-cols-3 gap-5">
        <div class="p-4 rounded-lg border border-gray-200">
          <p class="text-[12px] text-gray-500">Rows</p>
          <p class="text-[20px] font-semibold text-black mt-1">{{ (versions[0]?.row_count || 0).toLocaleString() }}</p>
        </div>
        <div class="p-4 rounded-lg border border-gray-200">
          <p class="text-[12px] text-gray-500">Columns</p>
          <p class="text-[20px] font-semibold text-black mt-1">{{ schema.length || dataset?.schema_info?.length || 0 }}</p>
        </div>
        <div class="p-4 rounded-lg border border-gray-200">
          <p class="text-[12px] text-gray-500">Versions</p>
          <p class="text-[20px] font-semibold text-black mt-1">{{ versions.length }}</p>
        </div>
      </div>

      <!-- Schema -->
      <div class="rounded-lg border border-gray-200">
        <div class="px-5 py-4 border-b border-gray-200">
          <h2 class="text-[14px] font-medium text-black">Schema</h2>
        </div>
        <table class="w-full">
          <thead>
            <tr class="border-b border-gray-100">
              <th class="px-5 py-3 text-left text-[12px] font-medium text-gray-500">Column</th>
              <th class="px-5 py-3 text-left text-[12px] font-medium text-gray-500">Type</th>
              <th class="px-5 py-3 text-left text-[12px] font-medium text-gray-500">Nullable</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="col in (schema.length ? schema : dataset?.schema_info || [])" :key="col.name">
              <td class="px-5 py-3 text-[13px] font-mono text-black">{{ col.name }}</td>
              <td class="px-5 py-3 text-[13px] text-gray-600">{{ col.type }}</td>
              <td class="px-5 py-3 text-[13px] text-gray-500">{{ col.nullable ? 'yes' : 'no' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="!schema.length && !dataset?.schema_info?.length" class="px-5 py-8 text-center text-[13px] text-gray-400">
          No schema information available
        </div>
      </div>

      <!-- Versions -->
      <div class="rounded-lg border border-gray-200">
        <div class="px-5 py-4 border-b border-gray-200">
          <h2 class="text-[14px] font-medium text-black">Version History</h2>
        </div>
        <div v-if="versions.length === 0" class="px-5 py-8 text-center text-[13px] text-gray-400">
          No versions available
        </div>
        <div v-else class="divide-y divide-gray-100">
          <div v-for="(v, i) in versions" :key="v.id" class="px-5 py-4 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <span :class="['text-[12px] font-mono px-2 py-0.5 rounded', i === 0 ? 'bg-black text-white' : 'bg-gray-100 text-gray-600']">v{{ v.version_number || versions.length - i }}</span>
              <div>
                <p class="text-[14px] text-black">{{ v.row_count.toLocaleString() }} rows</p>
                <p class="text-[12px] text-gray-400">{{ formatDate(v.uploaded_at || v.created_at || '') }}</p>
              </div>
            </div>
            <span v-if="i < versions.length - 1" :class="['text-[12px]', v.row_count > (versions[i + 1]?.row_count ?? 0) ? 'text-emerald-600' : 'text-red-600']">
              {{ v.row_count > (versions[i + 1]?.row_count ?? 0) ? '+' : '' }}{{ v.row_count - (versions[i + 1]?.row_count ?? 0) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Settings Tab -->
    <div v-else-if="activeTab === 'settings'" class="max-w-3xl space-y-6 pt-6 overflow-y-auto flex-1">
      <!-- Update Frequency -->
      <div class="rounded-lg border border-gray-200 p-6">
        <h2 class="text-[14px] font-medium text-black mb-4">Sync Settings</h2>
        <div class="space-y-4">
          <div>
            <label class="text-[13px] text-gray-500 mb-2 block">Update Frequency</label>
            <select v-model="updateFrequency" class="w-full px-4 py-2.5 border border-gray-200 rounded-md text-[14px] text-black focus:outline-none focus:border-gray-400">
              <option value="realtime">Real-time</option>
              <option value="hourly">Hourly</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="manual">Manual only</option>
            </select>
          </div>
          <p class="text-[12px] text-gray-400">Choose how often the AI should analyze new data and generate insights.</p>
        </div>
      </div>

      <!-- Team Members -->
      <div class="rounded-lg border border-gray-200 p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-[14px] font-medium text-black">Team Members</h2>
          <button class="text-[13px] text-gray-600 hover:text-black transition-colors">+ Add member</button>
        </div>
        <div v-if="teamMembers.length === 0" class="py-4 text-center text-[13px] text-gray-400">
          No team members
        </div>
        <div v-else class="space-y-3">
          <div v-for="member in teamMembers" :key="member.user_id" class="flex items-center justify-between py-2">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-[12px] font-medium text-gray-600">
                {{ member.email.charAt(0).toUpperCase() }}
              </div>
              <div>
                <p class="text-[14px] text-black">{{ member.name || member.email }}</p>
                <p v-if="member.name" class="text-[12px] text-gray-400">{{ member.email }}</p>
              </div>
            </div>
            <span class="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-md text-[12px] capitalize">{{ member.role }}</span>
          </div>
        </div>
      </div>

      <!-- Notifications -->
      <div class="rounded-lg border border-gray-200 p-6">
        <h2 class="text-[14px] font-medium text-black mb-4">Alert Notifications</h2>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-[14px] text-black">Email alerts</p>
              <p class="text-[12px] text-gray-400">Receive email for critical alerts</p>
            </div>
            <button @click="emailAlerts = !emailAlerts" :class="['relative w-11 h-6 rounded-full transition-colors flex-shrink-0', emailAlerts ? 'bg-black' : 'bg-gray-200']">
              <span :class="['absolute top-1 left-1 w-4 h-4 rounded-full bg-white shadow-sm transition-transform', emailAlerts ? 'translate-x-5' : 'translate-x-0']" />
            </button>
          </div>
          <div class="flex items-center justify-between">
            <div>
              <p class="text-[14px] text-black">Weekly digest</p>
              <p class="text-[12px] text-gray-400">Summary of insights every Monday</p>
            </div>
            <button @click="weeklyDigest = !weeklyDigest" :class="['relative w-11 h-6 rounded-full transition-colors flex-shrink-0', weeklyDigest ? 'bg-black' : 'bg-gray-200']">
              <span :class="['absolute top-1 left-1 w-4 h-4 rounded-full bg-white shadow-sm transition-transform', weeklyDigest ? 'translate-x-5' : 'translate-x-0']" />
            </button>
          </div>
        </div>
      </div>

      <!-- Save Button -->
      <div class="flex justify-start">
        <button @click="saveSettings" :disabled="savingSettings" class="px-6 py-2.5 bg-black text-white text-[14px] font-medium rounded-md hover:bg-gray-800 disabled:opacity-50 transition-colors">
          {{ savingSettings ? 'Saving...' : 'Save Settings' }}
        </button>
      </div>

      <!-- Danger Zone -->
      <div class="rounded-lg border border-red-200 p-6">
        <h2 class="text-[14px] font-medium text-red-600 mb-2">Danger Zone</h2>
        <p class="text-[13px] text-gray-500 mb-4">Permanently delete this data source and all associated data.</p>
        <button @click="deleteDataset" class="px-4 py-2 text-[13px] text-red-600 border border-red-200 rounded-md hover:bg-red-50 transition-colors">
          Delete Data Source
        </button>
      </div>
    </div>
  </div>
</template>
