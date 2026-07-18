import client from './client'

export interface ForbiddenTransition {
  id: string
  from_pattern_id: string
  to_pattern_id: string
}

export interface ChainNode {
  day_offset: number
  candidates: string[]
  is_rest: boolean
}

export interface PatternChain {
  id: string
  name: string
  trigger_pattern_id: string
  nodes: ChainNode[]
  total_length: number
}

export async function listForbiddenTransitions(): Promise<ForbiddenTransition[]> {
  const res = await client.get('/forbidden-transitions')
  return res.data
}

export async function createForbiddenTransition(data: Omit<ForbiddenTransition, 'id'>): Promise<ForbiddenTransition> {
  const res = await client.post('/forbidden-transitions', data)
  return res.data
}

export async function deleteForbiddenTransition(id: string): Promise<void> {
  await client.delete(`/forbidden-transitions/${id}`)
}

export async function listPatternChains(): Promise<PatternChain[]> {
  const res = await client.get('/pattern-chains')
  return res.data
}

export async function createPatternChain(data: Omit<PatternChain, 'id' | 'total_length'>): Promise<PatternChain> {
  const res = await client.post('/pattern-chains', data)
  return res.data
}

export async function updatePatternChain(id: string, data: Omit<PatternChain, 'id' | 'total_length'>): Promise<PatternChain> {
  const res = await client.put(`/pattern-chains/${id}`, data)
  return res.data
}

export async function deletePatternChain(id: string): Promise<void> {
  await client.delete(`/pattern-chains/${id}`)
}
