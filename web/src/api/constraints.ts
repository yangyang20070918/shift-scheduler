import client from './client'

export interface PersonConstraint {
  id: string
  member_id: string
  weekly_work_days_min?: number | null
  weekly_work_days_max?: number | null
  period_work_days_min?: number | null
  period_work_days_max?: number | null
  weekly_work_hours_min?: number | null
  weekly_work_hours_max?: number | null
  period_work_hours_min?: number | null
  period_work_hours_max?: number | null
  max_consecutive_work_days?: number | null
  max_consecutive_rest_days?: number | null
}

export type PersonConstraintInput = Omit<PersonConstraint, 'id'>

export async function listConstraints(): Promise<PersonConstraint[]> {
  const res = await client.get('/constraints')
  return res.data
}

export async function createConstraint(data: PersonConstraintInput): Promise<PersonConstraint> {
  const res = await client.post('/constraints', data)
  return res.data
}

export async function updateConstraint(id: string, data: PersonConstraintInput): Promise<PersonConstraint> {
  const res = await client.put(`/constraints/${id}`, data)
  return res.data
}

export async function deleteConstraint(id: string): Promise<void> {
  await client.delete(`/constraints/${id}`)
}
