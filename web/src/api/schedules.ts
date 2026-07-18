import client from './client'

export interface Schedule {
  id: string
  name: string
  start_date: string
  num_days: number
  status: string
  result_status?: string
  solve_time_seconds?: number
  total_penalty?: number
  health_score?: number
  score_breakdown?: Record<string, number>
}

export interface ScheduleResult {
  id: string
  name: string
  start_date: string
  num_days: number
  status: string
  result_status?: string
  solve_time_seconds?: number
  health_score?: number
  score_breakdown?: ScoreBreakdown
  assignments?: Assignment[]
  violations?: Violation[]
  warnings?: Warning[]
}

export interface ScoreBreakdown {
  personal: number
  group: number
  demand: number
  balance: number
  total_penalty: number
}

export interface Assignment {
  member_id: string
  member_name: string
  date: string
  pattern_id: string | null
  pattern_name: string
  is_rest: boolean
}

export interface Violation {
  priority: string
  constraint_group: string
  constraint_type: string
  target_member_id?: string
  target_date?: string
  setting_value?: string
  actual_value?: string
  contributing_factors?: string[]
  suggestions?: string[]
}

export interface Warning {
  warning_type: string
  severity: string
  target?: string
  message: string
}

export async function listSchedules(): Promise<Schedule[]> {
  const res = await client.get('/schedules')
  return res.data
}

export async function createSchedule(data: { name: string; start_date: string; num_days: number }): Promise<Schedule> {
  const res = await client.post('/schedules', data)
  return res.data
}

export async function updateSchedule(id: string, data: { name: string }): Promise<Schedule> {
  const res = await client.put(`/schedules/${id}`, data)
  return res.data
}

export async function getScheduleResult(id: string): Promise<ScheduleResult> {
  const res = await client.get(`/schedules/${id}`)
  return res.data
}

export async function generateSchedule(id: string): Promise<Schedule> {
  const res = await client.post(`/schedules/${id}/generate`)
  return res.data
}

export interface ScenarioSummary {
  name: string
  description: string
  health_score: number
  total_penalty: number
  violations_count: number
  score_breakdown: ScoreBreakdown
  solve_time_seconds: number
  assignments?: Assignment[]
}

export async function compareScenarios(id: string): Promise<{ scenarios: ScenarioSummary[] }> {
  const res = await client.post(`/schedules/${id}/compare`)
  return res.data
}

export async function exportExcel(id: string): Promise<void> {
  const res = await client.get(`/schedules/${id}/export/excel`, { responseType: 'blob' })
  const url = window.URL.createObjectURL(new Blob([res.data]))
  const link = document.createElement('a')
  link.href = url
  const disposition = res.headers['content-disposition']
  const filename = disposition?.match(/filename="(.+)"/)?.[1] || `schedule_${id}.xlsx`
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export async function exportPdf(id: string): Promise<void> {
  const res = await client.get(`/schedules/${id}/export/pdf`, { responseType: 'blob' })
  const url = window.URL.createObjectURL(new Blob([res.data]))
  const link = document.createElement('a')
  link.href = url
  const disposition = res.headers['content-disposition']
  const filename = disposition?.match(/filename="(.+)"/)?.[1] || `schedule_${id}.pdf`
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export interface ScheduleImportChange {
  member_id: string
  member_name: string
  date: string
  date_label: string
  before: { pattern_name: string; is_rest: boolean }
  after: { pattern_name: string; is_rest: boolean; pattern_id: string | null }
}

export interface ScheduleImportPreview {
  changes: ScheduleImportChange[]
  warnings: string[]
  total_imported: number
}

export async function previewScheduleImport(id: string, file: File): Promise<ScheduleImportPreview> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await client.post(`/schedules/${id}/import/preview`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export interface ScheduleImportResult {
  applied: number
  total_assignments: number
}

export async function executeScheduleImport(id: string, file: File): Promise<ScheduleImportResult> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await client.post(`/schedules/${id}/import/execute`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}
