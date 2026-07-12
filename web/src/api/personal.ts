import axios from 'axios'

function createPersonalClient(token: string) {
  const client = axios.create({
    baseURL: '/api/personal',
    headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' },
  })
  client.interceptors.request.use((config) => {
    config.params = { ...config.params, token, _t: Date.now() }
    return config
  })
  return client
}

export interface PersonalInfo {
  member_id: string
  member_name: string
  schedules: PersonalSchedule[]
}

export interface PersonalSchedule {
  id: string
  name: string
  start_date: string
  num_days: number
  status: string
  rest_request_max_days: number
  rest_request_deadline?: string | null
  my_request_status?: string | null
  my_requested_dates: string[]
}

export interface PersonalRestRequest {
  schedule_id: string
  schedule_name: string
  start_date: string
  num_days: number
  status: string
  rest_request_max_days: number
  rest_request_deadline?: string | null
  request: {
    requested_dates: string[]
    status: string
    submitted_at?: string | null
  }
}

export interface MyScheduleAssignment {
  member_id: string
  date: string
  pattern_id?: string | null
  is_rest: boolean
}

export interface MySchedule {
  schedule_name: string
  start_date: string
  num_days: number
  status: string
  assignments: MyScheduleAssignment[]
}

export async function getPersonalInfo(token: string): Promise<PersonalInfo> {
  const client = createPersonalClient(token)
  const res = await client.get('/info')
  return res.data
}

export async function getRestRequest(token: string, scheduleId: string): Promise<PersonalRestRequest> {
  const client = createPersonalClient(token)
  const res = await client.get(`/schedules/${scheduleId}/rest-request`)
  return res.data
}

export async function updateRestRequest(
  token: string,
  scheduleId: string,
  dates: string[],
): Promise<{ requested_dates: string[]; status: string }> {
  const client = createPersonalClient(token)
  const res = await client.put(`/schedules/${scheduleId}/rest-request`, {
    requested_dates: dates,
  })
  return res.data
}

export async function submitRestRequest(
  token: string,
  scheduleId: string,
): Promise<{ requested_dates: string[]; status: string; submitted_at: string }> {
  const client = createPersonalClient(token)
  const res = await client.post(`/schedules/${scheduleId}/rest-request/submit`)
  return res.data
}

export async function getMySchedule(token: string, scheduleId: string): Promise<MySchedule> {
  const client = createPersonalClient(token)
  const res = await client.get(`/schedules/${scheduleId}/my-schedule`)
  return res.data
}
