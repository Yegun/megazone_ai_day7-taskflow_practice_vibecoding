import { useState, type FormEvent } from 'react'
import { PRIORITIES, PRIORITY_LABEL, type Priority } from '../types'

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
}

function TaskForm({ onSubmit, disabled = false }: Props) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<Priority>('NORMAL')
  const [dueDate, setDueDate] = useState('')
  const [hint, setHint] = useState('')
  const [saving, setSaving] = useState(false)

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
      <button type="submit" disabled={saving || disabled}>
        등록
      </button>
      {hint && (
        <p className="hint" role="alert">
          {hint}
        </p>
      )}
    </form>
  )
}

export default TaskForm
