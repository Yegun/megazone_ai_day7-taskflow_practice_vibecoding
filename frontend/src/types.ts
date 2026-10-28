// 허용 상태 세 값. API(app/schemas.py Status)와 같은 값을 쓴다. (D-005)
export const STATUSES = ['TODO', 'IN_PROGRESS', 'DONE'] as const

export type Status = (typeof STATUSES)[number]

export const STATUS_LABEL: Record<Status, string> = {
  TODO: '할 일',
  IN_PROGRESS: '진행 중',
  DONE: '완료',
}

// 허용 우선순위 세 값. API(app/schemas.py Priority)와 같은 값을 쓴다. (R-009)
export const PRIORITIES = ['LOW', 'NORMAL', 'HIGH'] as const

export type Priority = (typeof PRIORITIES)[number]

export const PRIORITY_LABEL: Record<Priority, string> = {
  LOW: '낮음',
  NORMAL: '보통',
  HIGH: '높음',
}

export interface Task {
  id: number
  title: string
  description: string
  status: Status
  priority: Priority
  // YYYY-MM-DD. 마감일이 없으면 null.
  due_date: string | null
  // 기한 초과 여부는 서버가 계산해 준다. 화면이 날짜를 비교하지 않는다. (R-010)
  is_overdue: boolean
  created_at: string
  updated_at: string
}

// 수정 요청 값. 담지 않은 우선순위 · 마감일은 서버에서 그대로 유지된다. due_date 는 null 이면 마감일을 지운다.
export interface TaskEdit {
  title: string
  description: string
  status: Status
  priority?: Priority
  due_date?: string | null
}

// AI 제안 결과. 제안일 뿐 저장되지 않는다. due_date 는 마감일 단서가 없으면 null.
export interface Suggestion {
  priority: Priority
  due_date: string | null
  reason: string
}

export interface User {
  id: number
  username: string
}
