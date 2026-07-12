import client from './client'

export interface User {
  id: string
  email: string
  name: string
  role: string
  tenant_id: string
}

export interface LoginResponse {
  access_token: string
}

export async function register(data: {
  email: string
  password: string
  name: string
  tenant_name: string
}): Promise<User> {
  const res = await client.post('/auth/register', data)
  return res.data
}

export async function login(email: string, password: string): Promise<string> {
  const params = new URLSearchParams()
  params.append('username', email)
  params.append('password', password)
  const res = await client.post<LoginResponse>('/auth/login', params)
  return res.data.access_token
}

export async function getMe(): Promise<User> {
  const res = await client.get('/auth/me')
  return res.data
}
