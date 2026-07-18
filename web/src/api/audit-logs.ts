import client from './client'

export interface AuditLogItem {
  id: string
  timestamp: string
  user_id: string | null
  user_email: string | null
  action: string
  resource_type: string
  resource_id: string | null
  detail: Record<string, unknown> | null
  ip_address: string | null
}

export interface AuditLogListResponse {
  items: AuditLogItem[]
  total: number
}

export interface AuditStatItem {
  key: string
  count: number
}

export interface AuditStatsResponse {
  by_action: AuditStatItem[]
  by_resource: AuditStatItem[]
  by_user: AuditStatItem[]
  total: number
}

export async function listAuditLogs(params: {
  action?: string
  resource_type?: string
  user_id?: string
  date_from?: string
  date_to?: string
  offset?: number
  limit?: number
}): Promise<AuditLogListResponse> {
  const res = await client.get('/audit-logs', { params })
  return res.data
}

export async function getAuditStats(params?: {
  date_from?: string
  date_to?: string
}): Promise<AuditStatsResponse> {
  const res = await client.get('/audit-logs/stats', { params })
  return res.data
}
