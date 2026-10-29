import type { Briefing, DivisionItem, Priority, Status, Suggestion, Task } from '../types'

export class ApiError extends Error {
  status: number

  constructor(status: number) {
    super(`API 오류: ${status}`)
    this.status = status
  }
}

export function isNotFound(e: unknown): boolean {
  return e instanceof ApiError && e.status === 404
}

export function isUnauthorized(e: unknown): boolean {
  return e instanceof ApiError && e.status === 401
}

// 사용자에게 보여 줄 실패 원인. 연결 불가(fetch 실패, 프록시의 5xx) · 입력 오류 · 없는 카드를 구분한다.
export function describeError(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 404) return '카드를 찾을 수 없습니다. 이미 지워졌을 수 있습니다.'
    if (e.status === 422) return '입력 내용을 확인해 주세요.'
  }
  return '서버에 연결하지 못했거나 저장에 실패했습니다. 서버가 켜져 있는지 확인해 주세요.'
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) throw new ApiError(res.status)
  // 삭제 성공(204)은 본문이 없다.
  return res.status === 204 ? (undefined as T) : res.json()
}

export function listTasks(): Promise<Task[]> {
  return request('/api/tasks')
}

// 보낸 값만 바뀐다. 설명을 비우려면 '' 를, 마감일을 지우려면 null 을 보낸다.
export function updateTask(
  id: number,
  input: {
    title?: string
    description?: string
    status?: Status
    priority?: Priority
    due_date?: string | null
  },
): Promise<Task> {
  return request(`/api/tasks/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}

export function deleteTask(id: number): Promise<void> {
  return request(`/api/tasks/${id}`, { method: 'DELETE' })
}

// 우선순위 · 마감일 제안만 받는다. 서버는 이 요청으로 아무것도 저장하지 않는다.
export function suggestTask(input: {
  title: string
  description: string
}): Promise<Suggestion> {
  return request('/api/tasks/suggest', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

// 제목을 주제로 할 일을 나눈 제안만 받는다. 서버는 이 요청으로 아무것도 저장하지 않는다.
export function divideTask(title: string): Promise<DivisionItem[]> {
  return request('/api/tasks/division', {
    method: 'POST',
    body: JSON.stringify({ title }),
  })
}

// 우선순위를 담지 않으면 보통, 마감일을 담지 않으면 마감일 없음으로 저장된다.
export function createTask(input: {
  title: string
  description: string
  priority?: Priority
  due_date?: string
}): Promise<Task> {
  return request('/api/tasks', { method: 'POST', body: JSON.stringify(input) })
}

// 오늘의 브리핑만 받는다. 본문 없이 보내면 서버가 로그인한 사람의 끝나지 않은 할 일을 모은다. 아무것도 저장하지 않는다.
export function briefTasks(): Promise<Briefing> {
  return request('/api/tasks/briefing', { method: 'POST' })
}
