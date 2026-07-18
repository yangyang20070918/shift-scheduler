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

export async function batchSetDemandsByWeekday(
  scheduleId: string,
  weekdaySettings: Record<number, { min_total: number; max_total: number }>,
): Promise<DailyDemand[]> {
  const res = await client.post(`/schedules/${scheduleId}/demands/batch-weekday`, { weekday_settings: weekdaySettings })
  return res.data
}

export interface PatternDemand {
  id: string
  schedule_id: string
  date: string
  pattern_id: string
  min_count: number
}

export async function listPatternDemands(scheduleId: string): Promise<PatternDemand[]> {
  const res = await client.get(`/schedules/${scheduleId}/pattern-demands`)
  return res.data
}

export async function batchSetPatternDemand(scheduleId: string, data: { pattern_id: string; min_count: number }): Promise<PatternDemand[]> {
  const res = await client.post(`/schedules/${scheduleId}/pattern-demands/batch`, data)
  return res.data
}

export async function clearPatternDemands(scheduleId: string): Promise<void> {
  await client.delete(`/schedules/${scheduleId}/pattern-demands`)
}

export async function updateDemand(
  scheduleId: string,
  demandId: string,
  data: { min_total: number; max_total: number },
): Promise<DailyDemand> {
  const res = await client.put(`/schedules/${scheduleId}/demands/${demandId}`, data)
  return res.data
}

export async function updatePatternDemand(
  scheduleId: string,
  demandId: string,
  data: { min_count: number },
): Promise<PatternDemand> {
  const res = await client.put(`/schedules/${scheduleId}/pattern-demands/${demandId}`, data)
  return res.data
}

export async function batchSetPatternDemandByWeekday(
  scheduleId: string,
  data: { pattern_id: string; weekday_settings: Record<number, { min_count: number }> },
): Promise<PatternDemand[]> {
  const res = await client.post(`/schedules/${scheduleId}/pattern-demands/batch-weekday`, data)
  return res.data
}
