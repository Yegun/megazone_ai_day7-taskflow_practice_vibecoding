import { useEffect, useRef, useState } from 'react'
import { ApiError, briefTasks, isUnauthorized, listTasks } from './api/tasks'

export const BRIEFING = '만드는 중…'
const UNAVAILABLE = '지금은 브리핑을 쓸 수 없습니다'
const FAILED = '브리핑을 받지 못했습니다'
const EMPTY = '오늘은 비어 있어요'

// 카드에 그릴 값. 제목은 id 로 찾아 채운다.
export interface BriefingView {
  top3: { id: number; title: string; reason: string }[]
  later: { id: number; title: string }[]
  cheer: string
}

// 실패 문구. 502 는 받지 못한 것이고, 그 밖(503 · 연결 불가)은 쓸 수 없다고 알린다.
function failMessage(e: unknown): string {
  return e instanceof ApiError && e.status === 502 ? FAILED : UNAVAILABLE
}

// [오늘 브리핑] 버튼의 상태. 받은 브리핑은 view 에 담아 보여 주기만 하고 저장하지 않는다.
// 보드 · 등록 폼 · 기존 AI 버튼의 상태와는 따로 동작한다.
export function useBriefing(onUnauthorized: () => void) {
  const [pending, setPending] = useState(false)
  const [message, setMessage] = useState('')
  const [view, setView] = useState<BriefingView | null>(null)
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
      const [briefing, tasks] = await Promise.all([briefTasks(), listTasks()])
      if (id !== latest.current) return
      const titles = new Map(tasks.map((t) => [t.id, t.title]))
      const named = <T extends { id: number }>(items: T[]) =>
        items.flatMap((item) => {
          const title = titles.get(item.id)
          return title === undefined ? [] : [{ ...item, title }]
        })
      const top3 = named(briefing.top3)
      const later = named(briefing.later.map((id) => ({ id })))
      if (top3.length === 0 && later.length === 0) {
        setView(null)
        setMessage(EMPTY)
        return
      }
      setView({ top3, later, cheer: briefing.cheer })
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
