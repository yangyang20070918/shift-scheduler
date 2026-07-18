import client from './client'

export interface Pattern {
  id: string
  name: string
  type: string
  start_time: string
  end_time: string
  break_hours: number
  work_hours: number
  is_companion: boolean
  color_code: string
}

export async function listPatterns(): Promise<Pattern[]> {
  const res = await client.get('/patterns')
  return res.data
}

export async function createPattern(data: Omit<Pattern, 'id'>): Promise<Pattern> {
  const res = await client.post('/patterns', data)
  return res.data
}

export async function updatePattern(id: string, data: Omit<Pattern, 'id'>): Promise<Pattern> {
  const res = await client.put(`/patterns/${id}`, data)
  return res.data
}

export async function deletePattern(id: string): Promise<void> {
  await client.delete(`/patterns/${id}`)
}

export async function exportPatternsExcel(): Promise<void> {
  const res = await client.get('/patterns/export/excel', { responseType: 'blob' })
  const url = window.URL.createObjectURL(new Blob([res.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', 'patterns.xlsx')
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export interface PatternImportPreview {
  patterns: Array<Record<string, any>>
  warnings: string[]
}

export async function previewPatternImport(file: File): Promise<PatternImportPreview> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await client.post('/patterns/import/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export interface PatternImportResult {
  created: number
  updated: number
}

export async function executePatternImport(file: File): Promise<PatternImportResult> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await client.post('/patterns/import/execute', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}
