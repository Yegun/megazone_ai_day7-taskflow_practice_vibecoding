import { useState, type FormEvent } from 'react'
import { PRIORITIES, PRIORITY_LABEL, type DivisionItem, type Priority } from '../types'
import { useDivision } from '../useDivision'
import { useSuggest } from '../useSuggest'
import { DivisionButton, DivisionNote, DivisionPanel } from './DivisionParts'
import { SuggestButton, SuggestNote } from './SuggestParts'

interface Props {
  // 저장이 성공하면 true. 실패하면 false 를 돌려주고 입력값은 남긴다.
  onSubmit: (input: {
    title: string
    description: string
    priority: Priority
    due_date?: string
  }) => Promise<boolean>
  // 목록을 불러오기 전에는 등록하지 못하게 막는다.
  disabled?: boolean
  // AI 가 나눈 할 일을 모두 등록한다. 등록하지 못한 항목을 돌려준다. 전부 성공하면 빈 배열.
  onCreateMany: (items: DivisionItem[]) => Promise<DivisionItem[]>
  // AI 제안을 받다가 세션이 만료되어 401 을 받았을 때.
  onUnauthorized: () => void
}

function TaskForm({ onSubmit, disabled = false, onCreateMany, onUnauthorized }: Props) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<Priority>('NORMAL')
  const [dueDate, setDueDate] = useState('')
  const [hint, setHint] = useState('')
  const [saving, setSaving] = useState(false)
  const suggest = useSuggest(onUnauthorized)
  const division = useDivision(onUnauthorized)
  const [registeringAll, setRegisteringAll] = useState(false)

  // 미리 보기의 할 일을 저장한다. 전부 성공하면 원래대로, 일부 실패하면 실패한 항목만 남긴다.
  async function handleRegisterAll() {
    setRegisteringAll(true)
    const failed = await onCreateMany(division.items)
    setRegisteringAll(false)
    if (failed.length === 0) division.clear()
    else division.setItems(failed)
  }

  // 제안은 입력 칸만 채운다. 저장은 등록 버튼을 눌러야 한다. 마감일 단서가 없으면(null) 마감일 칸은 그대로 둔다.
  function handleSuggest() {
    return suggest.run({ title, description }, (s) => {
      setPriority(s.priority)
      if (s.due_date) setDueDate(s.due_date)
    })
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    // 화면은 같은 규칙을 먼저 안내만 한다. 최종 판정은 API. (D-004)
    if (!title.trim()) {
      setHint('제목을 입력해 주세요.')
      return
    }
    setHint('')
    setSaving(true)
    // 마감일을 비워 두면 담지 않는다. (마감일 없음)
    const ok = await onSubmit({
      title,
      description,
      priority,
      ...(dueDate && { due_date: dueDate }),
    })
    setSaving(false)
    if (ok) {
      setTitle('')
      setDescription('')
      setPriority('NORMAL')
      setDueDate('')
      suggest.reset()
    }
  }

  return (
    <form className="task-form" onSubmit={handleSubmit}>
      <input
        aria-label="제목"
        placeholder="새 Task 제목"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <input
        aria-label="설명"
        placeholder="설명 (선택)"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <SuggestButton pending={suggest.pending} onClick={handleSuggest} />
      <DivisionButton
        disabled={division.pending || registeringAll}
        onClick={() => division.run(title)}
      />
      <select
        aria-label="우선순위"
        value={priority}
        onChange={(e) => setPriority(e.target.value as Priority)}
      >
        {PRIORITIES.map((p) => (
          <option key={p} value={p}>
            우선순위 {PRIORITY_LABEL[p]}
          </option>
        ))}
      </select>
      <input
        type="date"
        aria-label="마감일"
        value={dueDate}
        onChange={(e) => setDueDate(e.target.value)}
      />
      <SuggestNote
        pending={suggest.pending}
        message={suggest.message}
        reason={suggest.reason}
      />
      <DivisionNote pending={division.pending} message={division.message} />
      <button type="submit" disabled={saving || disabled}>
        등록
      </button>
      {hint && (
        <p className="hint" role="alert">
          {hint}
        </p>
      )}
      {division.items.length > 0 && (
        <DivisionPanel
          items={division.items}
          busy={registeringAll || disabled}
          onRegisterAll={handleRegisterAll}
          onCancel={division.clear}
        />
      )}
    </form>
  )
}

export default TaskForm
