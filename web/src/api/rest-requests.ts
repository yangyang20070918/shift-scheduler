import client from './client'

export interface RestDayRequest {
  id: string
  schedule_id: string
  member_id: string
  member_name: string
  requested_dates: string[]
  status: string
  submitted_at?: string | null
  is_auto_submitted: boolean
}

export async function listRestRequests(scheduleId: string): Promise<RestDayRequest[]> {
  const res = await client.get(`/schedules/${scheduleId}/rest-requests`)
  return res.data
}

export async function updateRestRequest(
  scheduleId: string,
  memberId: string,
  dates: string[],
): Promise<RestDayRequest> {
  const res = await client.put(`/schedules/${scheduleId}/rest-requests/${memberId}`, {
    requested_dates: dates,
  })
  return res.data
}

export async function openRestRequests(scheduleId: string): Promise<{ status: string; members_count: number }> {
  const res = await client.post(`/schedules/${scheduleId}/rest-requests/open`)
  return res.data
}

export async function closeRestRequests(
  scheduleId: string,
): Promise<{ status: string; auto_submitted: number; fixed_assignments_created: number }> {
  const res = await client.post(`/schedules/${scheduleId}/rest-requests/close`)
  return res.data
}

export async function getMemberToken(memberId: string): Promise<{ member_id: string; personal_token: string | null }> {
  const res = await client.get(`/members/${memberId}/token`)
  return res.data
}

export async function generateMemberToken(memberId: string): Promise<{ member_id: string; personal_token: string }> {
  const res = await client.post(`/members/${memberId}/token`)
  return res.data
}
