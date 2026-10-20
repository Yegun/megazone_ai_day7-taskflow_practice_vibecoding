import type { Status, Task } from '../types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) throw new Error(`API 오류: ${res.status}`)
  return res.json()
}

export function listTasks(): Promise<Task[]> {
  return request('/api/tasks')
}

export function updateTask(
  id: number,
  input: { status: Status },
): Promise<Task> {
  return request(`/api/tasks/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}

export function createTask(input: {
  title: string
  description: string
}): Promise<Task> {
  return request('/api/tasks', { method: 'POST', body: JSON.stringify(input) })
}
