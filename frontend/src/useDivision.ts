import { useEffect, useRef, useState } from 'react'
import { ApiError, divideTask, isUnauthorized } from './api/tasks'
import type { DivisionItem } from './types'

export const DIVIDING = '할 일을 나누는 중...'
const NEED_TITLE = '제목을 먼저 입력해 주세요.'
const UNAVAILABLE = '지금은 AI 기능을 쓸 수 없습니다.'
const FAILED = 'AI가 일을 세분화 하지 못했습니다. - 버튼을 다시 눌러주세요.'
const EMPTY = '나눌 수 있는 할 일이 없습니다. 제목을 더 구체적으로 써 보세요.'

// 실패 문구. 502 는 다시 눌러 볼 수 있고, 그 밖(503 · 연결 불가)은 AI 기능을 쓸 수 없다고 알린다.
function failMessage(e: unknown): string {
  return e instanceof ApiError && e.status === 502 ? FAILED : UNAVAILABLE
}

// [AI로 할 일 만들기] 버튼의 상태. 받은 할 일은 items 에 담아 보여 주기만 하고 저장하지 않는다.
// 폼의 등록 · AI 제안은 이 상태와 상관없이 그대로 동작한다.
export function useDivision(onUnauthorized: () => void) {
  const [pending, setPending] = useState(false)
  const [message, setMessage] = useState('')
  const [items, setItems] = useState<DivisionItem[]>([])
  // 마지막 요청만 반영한다. 취소하거나 폼이 닫힌 뒤 늦게 온 응답은 버린다.
  const latest = useRef(0)

  useEffect(
    () => () => {
      latest.current += 1
    },
    [],
  )

  // 원래대로 돌아간다: 패널과 안내를 지우고 진행 중인 요청의 응답도 버린다.
  function clear() {
    latest.current += 1
    setPending(false)
    setMessage('')
    setItems([])
  }

  async function run(title: string) {
    setMessage('')
    // 화면은 같은 규칙을 먼저 안내만 한다. 최종 판정은 API. (D-004)
    if (!title.trim()) {
      setMessage(NEED_TITLE)
      return
    }
    const id = ++latest.current
    setPending(true)
    try {
      const result = await divideTask(title)
      if (id !== latest.current) return
      setItems(result)
      if (result.length === 0) setMessage(EMPTY)
    } catch (e) {
      if (id !== latest.current) return
      if (isUnauthorized(e)) return onUnauthorized()
      setMessage(failMessage(e))
    } finally {
      if (id === latest.current) setPending(false)
    }
  }

  return { pending, message, items, setItems, run, clear }
}
