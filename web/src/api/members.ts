import client from './client'

export interface Member {
  id: string
  name: string
  available_pattern_ids: string[]
}

export async function listMembers(): Promise<Member[]> {
  const res = await client.get('/members')
  return res.data
}

export async function createMember(data: { name: string; available_pattern_ids?: string[] }): Promise<Member> {
  const res = await client.post('/members', data)
  return res.data
}

export async function updateMember(id: string, data: { name: string; available_pattern_ids?: string[] }): Promise<Member> {
  const res = await client.put(`/members/${id}`, data)
  return res.data
}

export async function deleteMember(id: string): Promise<void> {
  await client.delete(`/members/${id}`)
}
