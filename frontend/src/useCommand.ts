import { useEffect, useRef, useState } from 'react'
import {
  ApiError,
  ReasonError,
  commandTasks,
  createTask,
  isUnauthorized,
  listTasks,
  updateTask,
} from './api/tasks'
import type { CommandAction } from './types'

export const COMMANDING = '알아듣는 중…'
const UNAVAILABLE = '지금은 시킬 수 없습니다'
const NOT_UNDERSTOOD = '알아듣지 못했습니다'
const NOT_FOUND = '바꿀 카드를 찾지 못했습니다. 다시 시켜 주세요.'

// 카드에 그릴 동작 하나. due · done 은 제목을 id 로 찾아 채운다.
export type CommandLine = CommandAction & { label: string }

// 실패 문구. 422 는 서버의 이유 그대로, 502 는 알아듣지 못한 것, 그 밖(503 · 연결 불가)은 쓸 수 없다고 알린다.
function failMessage(e: unknown): string {
  if (e instanceof ReasonError && e.reason) return e.reason
  if (e instanceof ApiError && e.status === 502) return NOT_UNDERSTOOD
  return UNAVAILABLE
}

async function applyOne(line: CommandLine) {
  if (line.kind === 'add') {
    await createTask({
      title: line.title ?? '',
      description: '',
      ...(line.priority ? { priority: line.priority } : {}),
      ...(line.due_date ? { due_date: line.due_date } : {}),
    })
  } else if (line.kind === 'due') {
    // 마감 하나만 보낸다. 다른 값은 서버에서 그대로 유지된다.
    await updateTask(line.id as number, { due_date: line.value })
  } else {
    await updateTask(line.id as number, { status: 'DONE' })
  }
}

// [시키기] 의 상태. 받은 동작은 lines 에 담아 확인만 받고, [적용] 때에만 기존 API 로 한 건씩 바꾼다.
// 보드 · 등록 폼 · 기존 AI 버튼의 상태와는 따로 동작한다.
export function useCommand(onUnauthorized: () => void, onApplied: () => void) {
  const [pending, setPending] = useState(false)
  const [applying, setApplying] = useState(false)
  const [message, setMessage] = useState('')
  const [lines, setLines] = useState<CommandLine[] | null>(null)
  // 마지막 요청만 반영한다. 취소한 뒤나 사라진 뒤 늦게 온 응답은 버린다.
  const latest = useRef(0)

  useEffect(
    () => () => {
      latest.current += 1
    },
    [],
  )

  function cancel() {
    latest.current += 1
    setPending(false)
    setMessage('')
    setLines(null)
  }

  async function run(text: string) {
    const id = ++latest.current
    setPending(true)
    setMessage('')
    setLines(null)
    try {
      // 제목은 id 로 찾는다. 보드의 상태를 건드리지 않도록 목록을 따로 받는다.
      const [result, tasks] = await Promise.all([commandTasks(text), listTasks()])
      if (id !== latest.current) return
      const titles = new Map(tasks.map((t) => [t.id, t.title]))
      const found = result.actions.flatMap((a): CommandLine[] => {
        if (a.kind === 'add') return [{ ...a, label: a.title ?? '' }]
        const title = a.id === null ? undefined : titles.get(a.id)
        return title === undefined ? [] : [{ ...a, label: title }]
      })
      if (found.length === 0) {
        setMessage(result.ask || NOT_FOUND)
        return
      }
      setLines(found)
    } catch (e) {
      if (id !== latest.current) return
      if (isUnauthorized(e)) return onUnauthorized()
      setMessage(failMessage(e))
    } finally {
      if (id === latest.current) setPending(false)
    }
  }

  // 카드마다 기존 API 를 한 번씩. 한 건이 실패해도 나머지는 계속하고, 끝나면 목록을 다시 받게 한다.
  async function apply() {
    if (!lines) return
    const id = latest.current
    setApplying(true)
    let failed = 0
    for (const line of lines) {
      try {
        await applyOne(line)
      } catch (e) {
        if (isUnauthorized(e)) return onUnauthorized()
        failed += 1
      }
    }
    if (id !== latest.current) return
    setApplying(false)
    setLines(null)
    setMessage(failed > 0 ? `${failed}개는 적용하지 못했습니다` : '')
    onApplied()
  }

  return { pending, applying, message, lines, run, apply, cancel }
}
