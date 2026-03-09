import type {
  User,
  Dataset,
  DatasetVersion,
  ColumnSchema,
  MetricsResponse,
  TeamMember,
  Insight,
  Alert,
  AlertConfig,
  ChatMessage,
  UserSettings,
  DatasetSettings,
  AuthResponse,
  Visualization,
  VisualizationResponse
} from '@/types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

// Helper to get auth headers
function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// Helper for API requests
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...options.headers
    }
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

// ============ AUTH ============

export async function login(email: string, password: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password })
  })
}

export async function register(email: string, password: string, name: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, name })
  })
}

export async function logout(): Promise<void> {
  await apiRequest('/auth/logout', { method: 'POST' })
}

export async function getCurrentUser(): Promise<User> {
  return apiRequest<User>('/auth/me')
}

// ============ DATASETS ============

export async function fetchDatasets(): Promise<{ datasets: Dataset[] }> {
  return apiRequest<{ datasets: Dataset[] }>('/datasets')
}

export async function fetchDataset(datasetId: string): Promise<Dataset> {
  return apiRequest<Dataset>(`/datasets/${datasetId}`)
}

export async function uploadDataset(file: File): Promise<{
  dataset: Dataset
  version: DatasetVersion
  schema: ColumnSchema[]
  metrics: MetricsResponse['metrics']
}> {
  const formData = new FormData()
  formData.append('file', file)

  const token = localStorage.getItem('token')
  const response = await fetch(`${API_BASE}/datasets`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(error.detail || 'Upload failed')
  }

  return response.json()
}

export async function deleteDataset(datasetId: string): Promise<void> {
  await apiRequest(`/datasets/${datasetId}`, { method: 'DELETE' })
}

export async function fetchVersions(datasetId: string): Promise<{ versions: DatasetVersion[] }> {
  return apiRequest<{ versions: DatasetVersion[] }>(`/datasets/${datasetId}/versions`)
}

export async function uploadVersion(datasetId: string, file: File): Promise<{
  version: DatasetVersion
  schema: ColumnSchema[]
  metrics: MetricsResponse['metrics']
}> {
  const formData = new FormData()
  formData.append('file', file)

  const token = localStorage.getItem('token')
  const response = await fetch(`${API_BASE}/datasets/${datasetId}/versions`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(error.detail || 'Upload failed')
  }

  return response.json()
}

export async function fetchSchema(datasetId: string): Promise<{ schema: ColumnSchema[] }> {
  return apiRequest<{ schema: ColumnSchema[] }>(`/datasets/${datasetId}/schema`)
}

export async function fetchMetrics(datasetId: string): Promise<MetricsResponse> {
  return apiRequest<MetricsResponse>(`/datasets/${datasetId}/metrics`)
}

// ============ TEAM ============

export async function fetchTeam(datasetId: string): Promise<{ team: TeamMember[] }> {
  return apiRequest<{ team: TeamMember[] }>(`/datasets/${datasetId}/team`)
}

export async function addTeamMember(
  datasetId: string,
  email: string,
  role: string = 'viewer'
): Promise<{ member: TeamMember }> {
  return apiRequest<{ member: TeamMember }>(`/datasets/${datasetId}/team`, {
    method: 'POST',
    body: JSON.stringify({ email, role })
  })
}

export async function updateTeamMember(
  datasetId: string,
  userId: string,
  role: string
): Promise<{ member: TeamMember }> {
  return apiRequest<{ member: TeamMember }>(`/datasets/${datasetId}/team/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify({ role })
  })
}

export async function removeTeamMember(datasetId: string, userId: string): Promise<void> {
  await apiRequest(`/datasets/${datasetId}/team/${userId}`, { method: 'DELETE' })
}

// ============ INSIGHTS ============

export async function fetchInsights(params?: {
  severity?: string
  dataset_id?: string
  unread_only?: boolean
}): Promise<{ insights: Insight[] }> {
  const searchParams = new URLSearchParams()
  if (params?.severity) searchParams.set('severity', params.severity)
  if (params?.dataset_id) searchParams.set('dataset_id', params.dataset_id)
  if (params?.unread_only) searchParams.set('unread_only', 'true')

  const query = searchParams.toString()
  return apiRequest<{ insights: Insight[] }>(`/insights${query ? `?${query}` : ''}`)
}

export async function fetchInsight(insightId: string): Promise<Insight> {
  return apiRequest<Insight>(`/insights/${insightId}`)
}

export async function updateInsight(
  insightId: string,
  updates: { read?: boolean; dismissed?: boolean }
): Promise<Insight> {
  return apiRequest<Insight>(`/insights/${insightId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates)
  })
}

export async function generateInsights(datasetId: string): Promise<{
  message: string
  insights: Insight[]
}> {
  return apiRequest<{ message: string; insights: Insight[] }>('/insights/generate', {
    method: 'POST',
    body: JSON.stringify({ dataset_id: datasetId })
  })
}

// ============ ALERTS ============

export async function fetchAlerts(params?: {
  dataset_id?: string
  severity?: string
  acknowledged?: boolean
}): Promise<{ alerts: Alert[] }> {
  const searchParams = new URLSearchParams()
  if (params?.dataset_id) searchParams.set('dataset_id', params.dataset_id)
  if (params?.severity) searchParams.set('severity', params.severity)
  if (params?.acknowledged !== undefined) searchParams.set('acknowledged', String(params.acknowledged))

  const query = searchParams.toString()
  return apiRequest<{ alerts: Alert[] }>(`/alerts${query ? `?${query}` : ''}`)
}

export async function acknowledgeAlert(alertId: string, acknowledged: boolean): Promise<Alert> {
  return apiRequest<Alert>(`/alerts/${alertId}`, {
    method: 'PATCH',
    body: JSON.stringify({ acknowledged })
  })
}

export async function configureAlert(config: AlertConfig): Promise<{ config: AlertConfig; message: string }> {
  return apiRequest<{ config: AlertConfig; message: string }>('/alerts/configure', {
    method: 'POST',
    body: JSON.stringify(config)
  })
}

export async function fetchAlertConfigs(datasetId: string): Promise<{ configs: AlertConfig[] }> {
  return apiRequest<{ configs: AlertConfig[] }>(`/alerts/configs/${datasetId}`)
}

// ============ CHAT ============

export async function sendChatMessage(
  datasetId: string,
  message: string
): Promise<{ user_message: ChatMessage; assistant_message: ChatMessage }> {
  return apiRequest<{ user_message: ChatMessage; assistant_message: ChatMessage }>('/chat', {
    method: 'POST',
    body: JSON.stringify({ dataset_id: datasetId, message })
  })
}

export async function fetchChatHistory(datasetId: string): Promise<{ messages: ChatMessage[] }> {
  return apiRequest<{ messages: ChatMessage[] }>(`/chat/history/${datasetId}`)
}

export async function clearChatHistory(datasetId: string): Promise<void> {
  await apiRequest(`/chat/history/${datasetId}`, { method: 'DELETE' })
}

// ============ SETTINGS ============

export async function fetchSettings(): Promise<UserSettings> {
  return apiRequest<UserSettings>('/settings')
}

export async function updateSettings(settings: Partial<UserSettings>): Promise<UserSettings> {
  return apiRequest<UserSettings>('/settings', {
    method: 'PUT',
    body: JSON.stringify(settings)
  })
}

export async function fetchNotificationSettings(): Promise<UserSettings> {
  return apiRequest<UserSettings>('/settings/notifications')
}

export async function updateNotificationSettings(settings: Partial<UserSettings>): Promise<UserSettings> {
  return apiRequest<UserSettings>('/settings/notifications', {
    method: 'PUT',
    body: JSON.stringify(settings)
  })
}

export async function fetchDatasetSettings(datasetId: string): Promise<DatasetSettings> {
  return apiRequest<DatasetSettings>(`/settings/datasets/${datasetId}`)
}

export async function updateDatasetSettings(
  datasetId: string,
  settings: Partial<DatasetSettings>
): Promise<DatasetSettings> {
  return apiRequest<DatasetSettings>(`/settings/datasets/${datasetId}`, {
    method: 'PUT',
    body: JSON.stringify({ ...settings, dataset_id: datasetId })
  })
}

// ============ VISUALIZATIONS ============

export async function fetchVisualizations(datasetId: string): Promise<VisualizationResponse> {
  return apiRequest<VisualizationResponse>(`/visualizations/${datasetId}`)
}

// Re-export types for convenience
export type {
  User,
  Dataset,
  DatasetVersion,
  ColumnSchema,
  MetricsResponse,
  TeamMember,
  Insight,
  Alert,
  AlertConfig,
  ChatMessage,
  UserSettings,
  DatasetSettings,
  AuthResponse,
  Visualization,
  VisualizationResponse
}
