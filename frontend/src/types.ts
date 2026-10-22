// 허용 상태 세 값. API(app/schemas.py Status)와 같은 값을 쓴다. (D-005)
export const STATUSES = ['TODO', 'IN_PROGRESS', 'DONE'] as const

export type Status = (typeof STATUSES)[number]

export const STATUS_LABEL: Record<Status, string> = {
  TODO: '할 일',
  IN_PROGRESS: '진행 중',
  DONE: '완료',
}

export interface Task {
  id: number
  title: string
  description: string
  status: Status
  created_at: string
  updated_at: string
}

export interface User {
  id: number
  username: string
}
