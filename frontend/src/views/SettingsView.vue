<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import * as api from '@/services/api'

const authStore = useAuthStore()

const emailNotifications = ref(true)
const frequency = ref('daily')
const criticalOnly = ref(false)
const saving = ref(false)
const saved = ref(false)
const isLoading = ref(true)
const error = ref<string | null>(null)

async function loadSettings() {
  try {
    isLoading.value = true
    const settings = await api.fetchSettings()
    emailNotifications.value = settings.email_notifications
    frequency.value = settings.notification_frequency
    criticalOnly.value = settings.critical_alerts_only
  } catch (e) {
    console.error('Failed to load settings:', e)
    error.value = e instanceof Error ? e.message : 'Failed to load settings'
  } finally {
    isLoading.value = false
  }
}

async function save() {
  saving.value = true
  error.value = null

  try {
    await api.updateSettings({
      email_notifications: emailNotifications.value,
      notification_frequency: frequency.value as 'realtime' | 'daily' | 'weekly',
      critical_alerts_only: criticalOnly.value
    })
    saved.value = true
    setTimeout(() => saved.value = false, 3000)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to save settings'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<template>
  <div class="max-w-2xl mx-auto">
    <div class="text-center mb-10">
      <h1 class="text-[28px] font-semibold text-black mb-2">Settings</h1>
      <p class="text-[15px] text-gray-500">Manage your account and notification preferences</p>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="py-12 text-center text-gray-500">Loading settings...</div>

    <template v-else>
      <!-- Account -->
      <div class="rounded-lg border border-gray-200 p-6 mb-6">
        <h2 class="text-[14px] font-medium text-black mb-4">Account</h2>
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 rounded-full bg-black text-white text-[16px] font-medium flex items-center justify-center">
            {{ authStore.user?.name?.charAt(0) || 'D' }}
          </div>
          <div>
            <p class="text-[15px] font-medium text-black">{{ authStore.user?.name || 'Demo User' }}</p>
            <p class="text-[13px] text-gray-500">{{ authStore.user?.email || 'demo@startobserving.ai' }}</p>
          </div>
        </div>
      </div>

      <!-- Notifications -->
      <div class="rounded-lg border border-gray-200 p-6 mb-8">
        <h2 class="text-[14px] font-medium text-black mb-6">Notifications</h2>

        <div class="flex items-center justify-between mb-6">
          <div>
            <p class="text-[14px] font-medium text-black">Email Digest</p>
            <p class="text-[13px] text-gray-500">Receive insight summaries via email</p>
          </div>
          <button @click="emailNotifications = !emailNotifications" :class="['relative w-11 h-6 rounded-full transition-colors flex-shrink-0', emailNotifications ? 'bg-black' : 'bg-gray-200']">
            <span :class="['absolute top-1 left-1 w-4 h-4 rounded-full bg-white transition-transform shadow-sm', emailNotifications ? 'translate-x-5' : 'translate-x-0']" />
          </button>
        </div>

        <div v-if="emailNotifications" class="mb-6">
          <label class="text-[13px] text-gray-500 mb-2 block">Frequency</label>
          <select v-model="frequency" class="w-full px-4 py-2.5 border border-gray-200 rounded-md text-[14px] text-black focus:outline-none focus:border-gray-400">
            <option value="realtime">Real-time</option>
            <option value="daily">Daily digest</option>
            <option value="weekly">Weekly digest</option>
          </select>
        </div>

        <div v-if="emailNotifications" class="flex items-center justify-between">
          <div>
            <p class="text-[14px] font-medium text-black">Critical alerts only</p>
            <p class="text-[13px] text-gray-500">Only receive notifications for critical insights</p>
          </div>
          <button @click="criticalOnly = !criticalOnly" :class="['relative w-11 h-6 rounded-full transition-colors flex-shrink-0', criticalOnly ? 'bg-black' : 'bg-gray-200']">
            <span :class="['absolute top-1 left-1 w-4 h-4 rounded-full bg-white transition-transform shadow-sm', criticalOnly ? 'translate-x-5' : 'translate-x-0']" />
          </button>
        </div>
      </div>

      <div v-if="error" class="mb-4 p-4 rounded-lg border border-red-200 bg-red-50 text-red-700 text-[14px]">
        {{ error }}
      </div>

      <div class="flex justify-center items-center gap-4">
        <button @click="save" :disabled="saving" class="px-6 py-2.5 bg-black text-white text-[14px] font-medium rounded-md hover:bg-gray-800 disabled:opacity-50 transition-colors">
          {{ saving ? 'Saving...' : 'Save Changes' }}
        </button>
        <span v-if="saved" class="text-[14px] text-emerald-600">Saved successfully</span>
      </div>
    </template>
  </div>
</template>
