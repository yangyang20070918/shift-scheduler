import client from './client'

export async function downloadTemplate(): Promise<void> {
  const res = await client.get('/import/template', { responseType: 'blob' })
  const url = window.URL.createObjectURL(new Blob([res.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', 'import_template.xlsx')
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export interface ImportPreview {
  members: Array<{ name: string; status: string; pattern_ids: string[]; pattern_names: string[] }>
  constraints: Array<Record<string, any>>
  demands: Array<Record<string, any>>
  warnings: string[]
}

export async function previewImport(file: File): Promise<ImportPreview> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await client.post('/import/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export interface ImportResult {
  members_created: number
  members_updated: number
  constraints_processed: number
  demands_count: number
}

export async function executeImport(file: File): Promise<ImportResult> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await client.post('/import/execute', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}
