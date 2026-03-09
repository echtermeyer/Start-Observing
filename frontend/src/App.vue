<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useDatasetStore } from '@/stores/datasets'
import { useAuthStore } from '@/stores/auth'
import * as api from '@/services/api'

const route = useRoute()
const datasetStore = useDatasetStore()
const authStore = useAuthStore()
const dashboardsExpanded = ref(true)
const isAuthReady = ref(false)
const isLoadingDatasets = ref(false)

async function loadDatasets() {
  if (!authStore.token) return

  try {
    isLoadingDatasets.value = true
    const { datasets } = await api.fetchDatasets()
    datasetStore.setDatasets(datasets)
  } catch (error) {
    console.error('Failed to load datasets:', error)
  } finally {
    isLoadingDatasets.value = false
  }
}

onMounted(async () => {
  // Always try to login fresh - this ensures we have a valid token
  // Clear any existing token first to avoid using stale tokens
  localStorage.removeItem('token')
  authStore.logout()

  try {
    const response = await api.login('demo@startobserving.ai', 'demo123')
    authStore.setAuth(response.token, response.user)
  } catch {
    // Demo user doesn't exist, try to register
    try {
      const response = await api.register('demo@startobserving.ai', 'demo123', 'Demo User')
      authStore.setAuth(response.token, response.user)
    } catch (e) {
      console.error('Auth failed:', e)
    }
  }

  // Mark auth as ready - child views can now make API calls
  isAuthReady.value = true
  await loadDatasets()
})

// Reload datasets when token changes
watch(() => authStore.token, async (newToken) => {
  if (newToken && isAuthReady.value) {
    await loadDatasets()
  }
})

const isActive = (path: string) => route.path === path || route.path.startsWith(path + '/')
</script>

<template>
  <div class="min-h-screen bg-white">
    <!-- Loading screen while auth initializes -->
    <div v-if="!isAuthReady" class="min-h-screen flex items-center justify-center">
      <div class="text-center">
        <div class="animate-spin h-8 w-8 border-2 border-black border-t-transparent rounded-full mx-auto mb-4"></div>
        <p class="text-gray-500 text-sm">Loading...</p>
      </div>
    </div>

    <template v-else>
      <!-- Sidebar -->
      <aside class="fixed inset-y-0 left-0 w-[240px] border-r border-gray-200 bg-white">
        <!-- Logo -->
        <div class="h-[60px] flex items-center px-5 border-b border-gray-200">
          <span class="text-[15px] font-semibold text-black">StartObserving</span>
        </div>

        <!-- Nav -->
        <nav class="p-3">
          <!-- Dashboards -->
          <div>
            <button
              @click="dashboardsExpanded = !dashboardsExpanded"
              :class="[
                'w-full flex items-center justify-between px-3 py-2 rounded-md text-[13px] transition-colors',
                isActive('/dashboard') || route.path.startsWith('/datasets/')
                  ? 'bg-gray-100 text-black font-medium'
                  : 'text-gray-600 hover:bg-gray-50'
              ]"
            >
              <div class="flex items-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
                </svg>
                Dashboards
              </div>
              <svg :class="['w-3 h-3 text-gray-400 transition-transform', dashboardsExpanded ? '' : '-rotate-90']" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            <div v-show="dashboardsExpanded" class="mt-1 ml-3 pl-3 border-l border-gray-200">
              <router-link
                to="/dashboard"
                :class="['block px-3 py-1.5 text-[13px] rounded-md transition-colors', route.path === '/dashboard' ? 'text-black font-medium' : 'text-gray-500 hover:text-black']"
              >
                Overview
              </router-link>
              <div v-if="isLoadingDatasets" class="px-3 py-1.5 text-[13px] text-gray-400">
                Loading...
              </div>
              <router-link
                v-else
                v-for="d in datasetStore.datasets"
                :key="d.id"
                :to="`/datasets/${d.id}`"
                :class="['block px-3 py-1.5 text-[13px] rounded-md transition-colors', route.path === `/datasets/${d.id}` ? 'text-black font-medium' : 'text-gray-500 hover:text-black']"
              >
                {{ d.name.replace('.csv', '') }}
              </router-link>
            </div>
          </div>

          <router-link
            to="/upload"
            :class="['flex items-center gap-2 px-3 py-2 mt-1 rounded-md text-[13px] transition-colors', isActive('/upload') ? 'bg-gray-100 text-black font-medium' : 'text-gray-600 hover:bg-gray-50']"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            Add Data Source
          </router-link>

          <router-link
            to="/feed"
            :class="['flex items-center gap-2 px-3 py-2 rounded-md text-[13px] transition-colors', isActive('/feed') ? 'bg-gray-100 text-black font-medium' : 'text-gray-600 hover:bg-gray-50']"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
            </svg>
            Insights
          </router-link>

          <router-link
            to="/settings"
            :class="['flex items-center gap-2 px-3 py-2 rounded-md text-[13px] transition-colors', isActive('/settings') ? 'bg-gray-100 text-black font-medium' : 'text-gray-600 hover:bg-gray-50']"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Settings
          </router-link>
        </nav>

        <!-- User -->
        <div class="absolute bottom-0 left-0 right-0 p-3 border-t border-gray-200">
          <div class="flex items-center gap-2 px-3 py-2">
            <div class="w-7 h-7 rounded-full bg-black text-white text-xs font-medium flex items-center justify-center">
              {{ authStore.user?.name?.charAt(0) || 'D' }}
            </div>
            <span class="text-[13px] text-gray-700">{{ authStore.user?.name || 'Demo User' }}</span>
          </div>
        </div>
      </aside>

      <!-- Main -->
      <main class="ml-[240px]">
        <div class="px-6 py-8">
          <router-view />
        </div>
      </main>
    </template>
  </div>
</template>
