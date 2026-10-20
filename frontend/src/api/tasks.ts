import type { Status, Task } from '../types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) throw new Error(`API 오류: ${res.status}`)
  // 삭제 성공(204)은 본문이 없다.
  return res.status === 204 ? (undefined as T) : res.json()
}

export function listTasks(): Promise<Task[]> {
  return request('/api/tasks')
}

// 보낸 값만 바뀐다. 설명을 비우려면 '' 를 보낸다.
export function updateTask(
  id: number,
  input: { title?: string; description?: string; status?: Status },
): Promise<Task> {
  return request(`/api/tasks/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}

export function deleteTask(id: number): Promise<void> {
  return request(`/api/tasks/${id}`, { method: 'DELETE' })
}

export function createTask(input: {
  title: string
  description: string
}): Promise<Task> {
  return request('/api/tasks', { method: 'POST', body: JSON.stringify(input) })
}
