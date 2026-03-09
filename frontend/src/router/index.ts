import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue')
  },
  {
    path: '/upload',
    name: 'upload',
    component: () => import('@/views/UploadView.vue')
  },
  {
    path: '/datasets/:id',
    name: 'dataset-detail',
    component: () => import('@/views/DatasetDetailView.vue')
  },
  {
    path: '/feed',
    name: 'feed',
    component: () => import('@/views/InsightFeedView.vue')
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
