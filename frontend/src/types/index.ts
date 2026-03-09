// User types
export interface User {
  id: string
  email: string
  name: string
  created_at: string
}

// Dataset types
export interface ColumnSchema {
  name: string
  type: 'string' | 'number' | 'date' | 'boolean'
  nullable: boolean
  sample_values?: string[]
}

export interface DatasetVersion {
  id: string
  dataset_id: string
  version_number: number
  file_path: string
  row_count: number
  uploaded_at: string
  created_at?: string
}

export interface Dataset {
  id: string
  user_id: string
  name: string
  created_at: string
  updated_at?: string
  version_count: number
  latest_row_count?: number
  schema_info?: ColumnSchema[]
  latest_version?: DatasetVersion
}

export interface DatasetMetrics {
  total_records: number
  null_rate: number
  column_count: number
  avg_value?: number
  anomaly_count: number
}

export interface MetricsResponse {
  metrics: DatasetMetrics
  changes?: {
    total_records_change?: number
    avg_value_change?: number
    null_rate_change?: number
    anomaly_change?: number
  }
}

// Team types
export interface TeamMember {
  id: string
  user_id: string
  email: string
  name: string
  role: 'owner' | 'editor' | 'viewer'
  added_at?: string
  created_at?: string
}

// Insight types
export type InsightSeverity = 'info' | 'warning' | 'critical'

export interface Insight {
  id: string
  dataset_id: string
  dataset_name: string
  severity: InsightSeverity
  title: string
  description: string
  created_at: string
  read: boolean
  dismissed: boolean
}

// Alert types
export interface Alert {
  id: string
  dataset_id: string
  dataset_name: string
  severity: InsightSeverity
  type: string
  title: string
  message: string
  created_at: string
  acknowledged: boolean
}

export interface AlertConfig {
  id?: string
  dataset_id: string
  alert_type: string
  threshold_column?: string
  threshold_value?: number
  enabled: boolean
}

// Chat types
export interface ChatMessage {
  id: string
  dataset_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

// Settings types
export interface UserSettings {
  id?: string
  user_id?: string
  email_notifications: boolean
  notification_frequency: 'realtime' | 'daily' | 'weekly'
  critical_alerts_only: boolean
}

export interface DatasetSettings {
  dataset_id: string
  update_frequency: 'realtime' | 'hourly' | 'daily' | 'weekly' | 'manual'
  email_alerts: boolean
  weekly_digest: boolean
}

// Auth types
export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterCredentials {
  email: string
  password: string
  name: string
}

export interface AuthResponse {
  token: string
  user: User
}

// Visualization types
export interface Visualization {
  id: string
  title: string
  description: string
  spec: Record<string, unknown>
}

export interface VisualizationResponse {
  dataset_id: string
  generated_at: string
  visualizations: Visualization[]
}
