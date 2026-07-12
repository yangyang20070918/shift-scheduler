import client from './client'

export interface DailyDemand {
  id: string
  schedule_id: string
  date: string
  min_total: number
  max_total: number
}

export interface DailyDemandBatch {
  min_total: number
  max_total: number
}

export async function listDemands(scheduleId: string): Promise<DailyDemand[]> {
  const res = await client.get(`/schedules/${scheduleId}/demands`)
  return res.data
}

export async function batchSetDemands(scheduleId: string, data: DailyDemandBatch): Promise<DailyDemand[]> {
  const res = await client.post(`/schedules/${scheduleId}/demands/batch`, data)
  return res.data
}

export async function clearDemands(scheduleId: string): Promise<void> {
  await client.delete(`/schedules/${scheduleId}/demands`)
}
