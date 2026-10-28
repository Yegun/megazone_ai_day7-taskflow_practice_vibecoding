import { useEffect, useRef, useState } from 'react'
import { ApiError, isUnauthorized, suggestTask } from './api/tasks'
import type { Suggestion } from './types'

export const SUGGESTING = '제안을 받는 중...'
const NEED_TITLE = '제목을 먼저 입력해 주세요.'
const UNAVAILABLE = '지금은 AI 제안을 쓸 수 없습니다. 직접 입력해 주세요.'
const FAILED = '제안을 못 받았습니다. 제안 버튼을 다시 눌러주세요.'

// 실패 문구. 502 는 다시 눌러 볼 수 있고, 그 밖(503 · 연결 불가)은 직접 입력을 안내한다.
function failMessage(e: unknown): string {
  return e instanceof ApiError && e.status === 502 ? FAILED : UNAVAILABLE
}

// [AI 제안] 버튼의 상태. 제안은 폼의 입력 칸만 채운다. 저장은 하지 않는다.
// 폼의 등록 · 저장 버튼은 이 상태와 상관없이 그대로 동작한다.
export function useSuggest(onUnauthorized: () => void) {
  const [pending, setPending] = useState(false)
  const [message, setMessage] = useState('')
  const [reason, setReason] = useState('')
  // 마지막 요청만 반영한다. 폼이 닫히거나 비워진 뒤 늦게 온 응답은 버린다.
  const latest = useRef(0)

  useEffect(
    () => () => {
      latest.current += 1
    },
    [],
  )

  function reset() {
    latest.current += 1
    setPending(false)
    setMessage('')
    setReason('')
  }

  async function run(
    input: { title: string; description: string },
    apply: (s: Suggestion) => void,
  ) {
    setMessage('')
    setReason('')
    // 화면은 같은 규칙을 먼저 안내만 한다. 최종 판정은 API. (D-004)
    if (!input.title.trim()) {
      setMessage(NEED_TITLE)
      return
    }
    const id = ++latest.current
    setPending(true)
    try {
      const s = await suggestTask(input)
      if (id !== latest.current) return
      apply(s)
      setReason(s.reason)
    } catch (e) {
      if (id !== latest.current) return
      if (isUnauthorized(e)) return onUnauthorized()
      setMessage(failMessage(e))
    } finally {
      if (id === latest.current) setPending(false)
    }
  }

  return { pending, message, reason, run, reset }
}
