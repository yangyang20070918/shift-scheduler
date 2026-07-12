import client from './client'

export interface Group {
  id: string
  name: string
  member_ids: string[]
}

export interface GroupInput {
  name: string
  member_ids: string[]
}

export interface GroupDemand {
  id: string
  schedule_id: string
  date: string
  group_id: string
  pattern_id: string
  min_count: number
}

export interface GroupDemandInput {
  date: string
  group_id: string
  pattern_id: string
  min_count: number
}

export async function listGroups(): Promise<Group[]> {
  const res = await client.get('/groups')
  return res.data
}

export async function createGroup(data: GroupInput): Promise<Group> {
  const res = await client.post('/groups', data)
  return res.data
}

export async function updateGroup(id: string, data: GroupInput): Promise<Group> {
  const res = await client.put(`/groups/${id}`, data)
  return res.data
}

export async function deleteGroup(id: string): Promise<void> {
  await client.delete(`/groups/${id}`)
}

export async function listGroupDemands(scheduleId: string): Promise<GroupDemand[]> {
  const res = await client.get(`/schedules/${scheduleId}/group-demands`)
  return res.data
}

export async function createGroupDemand(scheduleId: string, data: GroupDemandInput): Promise<GroupDemand> {
  const res = await client.post(`/schedules/${scheduleId}/group-demands`, data)
  return res.data
}

export async function deleteGroupDemand(scheduleId: string, demandId: string): Promise<void> {
  await client.delete(`/schedules/${scheduleId}/group-demands/${demandId}`)
}

export async function clearGroupDemands(scheduleId: string): Promise<void> {
  await client.delete(`/schedules/${scheduleId}/group-demands`)
}
