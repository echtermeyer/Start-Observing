<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDatasetStore } from '@/stores/datasets'
import { useInsightStore } from '@/stores/insights'
import * as api from '@/services/api'

const router = useRouter()
const datasetStore = useDatasetStore()
const insightStore = useInsightStore()

const isDragging = ref(false)
const isUploading = ref(false)
const uploadProgress = ref(0)
const selectedFile = ref<File | null>(null)
const uploadError = ref('')
const showModal = ref(false)
const selectedSource = ref('')

const sources = [
  { id: 'postgres', name: 'PostgreSQL', icon: 'postgres' },
  { id: 'mysql', name: 'MySQL', icon: 'mysql' },
  { id: 'snowflake', name: 'Snowflake', icon: 'snowflake' },
  { id: 'bigquery', name: 'BigQuery', icon: 'bigquery' },
  { id: 'redshift', name: 'Redshift', icon: 'redshift' },
  { id: 's3', name: 'Amazon S3', icon: 's3' },
]

function clickSource(id: string) { selectedSource.value = id; showModal.value = true }
function handleDragOver(e: DragEvent) { e.preventDefault(); isDragging.value = true }
function handleDragLeave() { isDragging.value = false }
function handleDrop(e: DragEvent) {
  e.preventDefault(); isDragging.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f) handleFile(f)
}
function handleInput(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) handleFile(f)
}
function handleFile(f: File) {
  uploadError.value = ''
  if (!f.name.endsWith('.csv')) { uploadError.value = 'Please select a CSV file'; return }
  selectedFile.value = f
}

async function upload() {
  if (!selectedFile.value) return

  isUploading.value = true
  uploadProgress.value = 0
  uploadError.value = ''

  // Simulate progress while upload happens
  const progressInterval = setInterval(() => {
    if (uploadProgress.value < 90) {
      uploadProgress.value += 10
    }
  }, 200)

  try {
    const result = await api.uploadDataset(selectedFile.value)
    uploadProgress.value = 100

    // Add dataset to store
    datasetStore.addDataset(result.dataset)

    // Generate insights for the new dataset
    try {
      const insightsResult = await api.generateInsights(result.dataset.id)
      insightStore.addInsights(insightsResult.insights)
    } catch (e) {
      console.warn('Failed to generate insights:', e)
    }

    // Navigate to the new dataset
    setTimeout(() => {
      router.push(`/datasets/${result.dataset.id}`)
    }, 500)
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : 'Upload failed'
    isUploading.value = false
    uploadProgress.value = 0
  } finally {
    clearInterval(progressInterval)
  }
}

function clear() { selectedFile.value = null; uploadProgress.value = 0 }
function formatSize(b: number) { return b < 1024 ? b + ' B' : b < 1048576 ? (b / 1024).toFixed(1) + ' KB' : (b / 1048576).toFixed(1) + ' MB' }
</script>

<template>
  <div class="max-w-3xl mx-auto">
    <div class="text-center mb-10">
      <h1 class="text-[28px] font-semibold text-black mb-2">Connect Data Source</h1>
      <p class="text-[15px] text-gray-500 max-w-md mx-auto">Connect your database or upload a file to start monitoring your data with AI-powered insights</p>
    </div>

    <!-- Live Sources -->
    <div class="mb-10">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-[14px] font-medium text-black">Live Connections</h2>
        <span class="text-[12px] text-gray-400">Select a data source</span>
      </div>
      <div class="grid grid-cols-3 gap-3">
        <button
          v-for="s in sources"
          :key="s.id"
          @click="clickSource(s.id)"
          class="flex items-center gap-3 px-4 py-4 rounded-lg border border-gray-200 text-left hover:border-gray-300 hover:bg-gray-50 transition-all group"
        >
          <!-- Icons -->
          <div class="w-8 h-8 rounded-md bg-gray-100 flex items-center justify-center group-hover:bg-gray-200 transition-colors">
            <svg v-if="s.icon === 'postgres'" class="w-5 h-5 text-[#336791]" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
            </svg>
            <svg v-else-if="s.icon === 'mysql'" class="w-5 h-5 text-[#00758F]" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15h-2v-6h2v6zm4 0h-2v-6h2v6zm0-8H9V7h6v2z"/>
            </svg>
            <svg v-else-if="s.icon === 'snowflake'" class="w-5 h-5 text-[#29B5E8]" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2l1.09 3.41L16 4l-1.41 1.09L18 6.5l-3.41 1.09L16 11l-2.91-1.41L12 13l-1.09-3.41L8 11l1.41-1.09L6 8.5l3.41-1.09L8 4l2.91 1.41L12 2zm0 11l1.09 3.41L16 15l-1.41 1.09L18 17.5l-3.41 1.09L16 22l-2.91-1.41L12 24l-1.09-3.41L8 22l1.41-1.09L6 19.5l3.41-1.09L8 15l2.91 1.41L12 13z"/>
            </svg>
            <svg v-else-if="s.icon === 'bigquery'" class="w-5 h-5 text-[#4285F4]" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
            <svg v-else-if="s.icon === 'redshift'" class="w-5 h-5 text-[#8C4FFF]" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/>
            </svg>
            <svg v-else-if="s.icon === 's3'" class="w-5 h-5 text-[#FF9900]" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2L2 7v10l10 5 10-5V7L12 2zm0 2.18l6.9 3.45L12 11.08 5.1 7.63 12 4.18zM4 8.82l7 3.5v7.36l-7-3.5V8.82zm9 10.86v-7.36l7-3.5v7.36l-7 3.5z"/>
            </svg>
          </div>
          <div>
            <p class="text-[14px] font-medium text-black">{{ s.name }}</p>
          </div>
        </button>
      </div>
      <p class="text-[12px] text-gray-400 mt-3 text-center">Connect directly to your database for real-time monitoring and automated syncing</p>
    </div>

    <!-- Divider -->
    <div class="relative mb-10">
      <div class="absolute inset-0 flex items-center"><div class="w-full border-t border-gray-200"></div></div>
      <div class="relative flex justify-center"><span class="px-4 bg-white text-[13px] text-gray-400">or upload a file</span></div>
    </div>

    <!-- Upload -->
    <div class="mb-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-[14px] font-medium text-black">File Upload</h2>
        <span class="text-[12px] text-gray-400">CSV format supported</span>
      </div>
      <div
        :class="['border border-dashed rounded-lg p-10 text-center transition-all', isDragging ? 'border-black bg-gray-50' : 'border-gray-300 hover:border-gray-400']"
        @dragover="handleDragOver" @dragleave="handleDragLeave" @drop="handleDrop"
      >
        <div v-if="!selectedFile">
          <div class="w-12 h-12 mx-auto rounded-full bg-gray-100 flex items-center justify-center mb-4">
            <svg class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
          </div>
          <p class="text-[15px] text-gray-600 mb-1">Drop your CSV file here</p>
          <p class="text-[14px] text-gray-500">or <label class="text-black font-medium cursor-pointer hover:underline">browse from your computer<input type="file" class="hidden" accept=".csv" @change="handleInput" /></label></p>
          <p class="text-[12px] text-gray-400 mt-3">Maximum file size: 50MB</p>
        </div>
        <div v-else>
          <div class="flex items-center justify-center gap-4 mb-4">
            <div class="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
              <svg class="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
            </div>
            <div class="text-left">
              <p class="text-[15px] font-medium text-black">{{ selectedFile.name }}</p>
              <p class="text-[13px] text-gray-500">{{ formatSize(selectedFile.size) }}</p>
            </div>
          </div>
          <div v-if="isUploading" class="max-w-xs mx-auto">
            <div class="h-1.5 bg-gray-200 rounded-full overflow-hidden"><div class="h-full bg-black transition-all" :style="{ width: uploadProgress + '%' }"></div></div>
            <p class="text-[12px] text-gray-500 mt-2">Analyzing your data... {{ uploadProgress }}%</p>
          </div>
        </div>
      </div>
    </div>

    <div v-if="uploadError" class="text-[13px] text-red-600 mb-4 text-center">{{ uploadError }}</div>

    <div class="flex justify-center gap-3">
      <button v-if="selectedFile && !isUploading" @click="clear" class="px-5 py-2.5 text-[14px] text-gray-600 hover:text-black transition-colors">Clear</button>
      <button @click="upload" :disabled="!selectedFile || isUploading" class="px-6 py-2.5 bg-black text-white text-[14px] font-medium rounded-md hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
        {{ isUploading ? 'Creating...' : 'Create Dashboard' }}
      </button>
    </div>

    <!-- Info -->
    <div class="mt-12 p-6 rounded-lg bg-gray-50 border border-gray-200">
      <h3 class="text-[14px] font-medium text-black mb-3">What happens next?</h3>
      <div class="grid grid-cols-2 gap-4">
        <div class="flex items-start gap-3">
          <div class="w-6 h-6 rounded-full bg-black text-white text-[11px] font-medium flex items-center justify-center flex-shrink-0">1</div>
          <div>
            <p class="text-[13px] font-medium text-black">Schema Detection</p>
            <p class="text-[12px] text-gray-500">AI analyzes your data structure and column types</p>
          </div>
        </div>
        <div class="flex items-start gap-3">
          <div class="w-6 h-6 rounded-full bg-black text-white text-[11px] font-medium flex items-center justify-center flex-shrink-0">2</div>
          <div>
            <p class="text-[13px] font-medium text-black">Pattern Analysis</p>
            <p class="text-[12px] text-gray-500">Identifies trends, distributions, and anomalies</p>
          </div>
        </div>
        <div class="flex items-start gap-3">
          <div class="w-6 h-6 rounded-full bg-black text-white text-[11px] font-medium flex items-center justify-center flex-shrink-0">3</div>
          <div>
            <p class="text-[13px] font-medium text-black">Dashboard Creation</p>
            <p class="text-[12px] text-gray-500">Auto-generates insights and monitoring alerts</p>
          </div>
        </div>
        <div class="flex items-start gap-3">
          <div class="w-6 h-6 rounded-full bg-black text-white text-[11px] font-medium flex items-center justify-center flex-shrink-0">4</div>
          <div>
            <p class="text-[13px] font-medium text-black">Ongoing Monitoring</p>
            <p class="text-[12px] text-gray-500">Upload new versions to track changes over time</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal -->
    <Teleport to="body">
      <div v-if="showModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="showModal = false">
        <div class="bg-white rounded-lg p-6 max-w-sm mx-4 shadow-xl">
          <div class="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center mb-4">
            <svg class="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
          </div>
          <h3 class="text-[16px] font-semibold text-black">Coming Soon</h3>
          <p class="text-[14px] text-gray-500 mt-2">{{ sources.find(s => s.id === selectedSource)?.name }} connections are coming soon. For now, please upload a CSV file to get started.</p>
          <button @click="showModal = false" class="mt-5 w-full px-4 py-2.5 bg-black text-white text-[14px] font-medium rounded-md hover:bg-gray-800 transition-colors">Got it</button>
        </div>
      </div>
    </Teleport>
  </div>
</template>
