import { useState, type FormEvent } from 'react'
import {
  PRIORITIES,
  PRIORITY_LABEL,
  STATUSES,
  STATUS_LABEL,
  type Priority,
  type Status,
  type Task,
  type TaskEdit,
} from '../types'

export const UNTITLED = '제목없음'

interface Props {
  task: Task
  // 저장이 성공하면 true. 실패하면 false 를 돌려주고 폼을 열어 둔다.
  onSave: (input: TaskEdit) => Promise<boolean>
  onCancel: () => void
}

function TaskEditForm({ task, onSave, onCancel }: Props) {
  const [title, setTitle] = useState(task.title)
  const [description, setDescription] = useState(task.description)
  const [status, setStatus] = useState<Status>(task.status)
  const [priority, setPriority] = useState<Priority>(task.priority)
  const [dueDate, setDueDate] = useState(task.due_date ?? '')
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    // 제목을 비우고 저장하면 '제목없음'으로 채워 그 값으로 저장한다. (R-004)
    // 우선순위 · 마감일은 바꾼 때만 담는다. 건드리지 않으면 서버의 기존 값이 유지된다. 마감일을 지우면 null.
    const ok = await onSave({
      title: title.trim() || UNTITLED,
      description,
      status,
      ...(priority !== task.priority && { priority }),
      ...(dueDate !== (task.due_date ?? '') && { due_date: dueDate || null }),
    })
    setSaving(false)
    if (ok) onCancel()
  }

  return (
    <form className="task-edit-form" onSubmit={handleSubmit}>
      <input
        aria-label="제목"
        placeholder={UNTITLED}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <textarea
        aria-label="설명"
        placeholder="설명 (선택)"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <select
        aria-label="상태"
        value={status}
        onChange={(e) => setStatus(e.target.value as Status)}
      >
        {STATUSES.map((s) => (
          <option key={s} value={s}>
            {STATUS_LABEL[s]}
          </option>
        ))}
      </select>
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
      <div className="due-field">
        <input
          type="date"
          aria-label="마감일"
          value={dueDate}
          onChange={(e) => setDueDate(e.target.value)}
        />
        <button
          type="button"
          onClick={() => setDueDate('')}
          disabled={saving || !dueDate}
        >
          마감일 지우기
        </button>
      </div>
      <div className="actions">
        <button type="submit" disabled={saving}>
          저장
        </button>
        <button type="button" onClick={onCancel} disabled={saving}>
          취소
        </button>
      </div>
    </form>
  )
}

export default TaskEditForm
