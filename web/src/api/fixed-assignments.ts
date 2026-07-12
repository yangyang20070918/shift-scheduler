import client from './client'

export interface FixedAssignment {
  id: string
  schedule_id: string
  member_id: string
  date: string
  type: 'work' | 'rest'
  pattern_id?: string | null
}

export interface FixedAssignmentInput {
  member_id: string
  date: string
  type: 'work' | 'rest'
  pattern_id?: string | null
}

export async function listFixedAssignments(scheduleId: string): Promise<FixedAssignment[]> {
  const res = await client.get(`/schedules/${scheduleId}/fixed-assignments`)
  return res.data
}

export async function createFixedAssignment(scheduleId: string, data: FixedAssignmentInput): Promise<FixedAssignment> {
  const res = await client.post(`/schedules/${scheduleId}/fixed-assignments`, data)
  return res.data
}

export async function deleteFixedAssignment(scheduleId: string, assignmentId: string): Promise<void> {
  await client.delete(`/schedules/${scheduleId}/fixed-assignments/${assignmentId}`)
}

export async function clearFixedAssignments(scheduleId: string): Promise<void> {
  await client.delete(`/schedules/${scheduleId}/fixed-assignments`)
}
