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

export async function deletePattern(id: string): Promise<void> {
  await client.delete(`/patterns/${id}`)
}
