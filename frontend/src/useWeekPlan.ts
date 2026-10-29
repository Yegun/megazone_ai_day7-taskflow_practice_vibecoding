import { useEffect, useRef, useState } from 'react'
import { ApiError, isUnauthorized, listTasks, planWeek } from './api/tasks'

export const PLANNING = '만드는 중…'
const UNAVAILABLE = '지금은 계획을 쓸 수 없습니다'
const FAILED = '계획표을 받지 못했습니다'
const EMPTY = '할 일이 비어 있어요'

// 카드에 그릴 값. 제목은 id 로 찾아 채운다.
export interface WeekPlanView {
  days: { date: string; titles: string[] }[]
  note: string
}

// 실패 문구. 502 는 받지 못한 것이고, 그 밖(503 · 연결 불가)은 쓸 수 없다고 알린다.
function failMessage(e: unknown): string {
  return e instanceof ApiError && e.status === 502 ? FAILED : UNAVAILABLE
}

// [이번 주 계획] 버튼의 상태. 받은 계획은 view 에 담아 보여 주기만 하고 저장하지 않는다.
// 보드 · 등록 폼 · 기존 AI 버튼의 상태와는 따로 동작한다.
export function useWeekPlan(onUnauthorized: () => void) {
  const [pending, setPending] = useState(false)
  const [message, setMessage] = useState('')
  const [view, setView] = useState<WeekPlanView | null>(null)
  // 마지막 요청만 반영한다. 닫은 뒤나 사라진 뒤 늦게 온 응답은 버린다.
  const latest = useRef(0)

  useEffect(
    () => () => {
      latest.current += 1
    },
    [],
  )

  function close() {
    latest.current += 1
    setPending(false)
    setMessage('')
    setView(null)
  }

  async function run() {
    const id = ++latest.current
    setPending(true)
    setMessage('')
    try {
      // 제목은 id 로 찾는다. 보드의 상태를 건드리지 않도록 목록을 따로 받는다.
      const [plan, tasks] = await Promise.all([planWeek(), listTasks()])
      if (id !== latest.current) return
      const titles = new Map(tasks.map((t) => [t.id, t.title]))
      const days = plan.days.map((day) => ({
        date: day.date,
        titles: day.task_ids.flatMap((taskId) => {
          const title = titles.get(taskId)
          return title === undefined ? [] : [title]
        }),
      }))
      if (days.every((day) => day.titles.length === 0)) {
        setView(null)
        setMessage(EMPTY)
        return
      }
      setView({ days, note: plan.note })
    } catch (e) {
      if (id !== latest.current) return
      if (isUnauthorized(e)) return onUnauthorized()
      setView(null)
      setMessage(failMessage(e))
    } finally {
      if (id === latest.current) setPending(false)
    }
  }

  return { pending, message, view, run, close }
}
