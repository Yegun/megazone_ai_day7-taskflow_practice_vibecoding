import { useState, type FormEvent } from 'react'
import { STATUSES, STATUS_LABEL, type Status, type Task } from '../types'

export const UNTITLED = '제목없음'

interface Props {
  task: Task
  // 저장이 성공하면 true. 실패하면 false 를 돌려주고 폼을 열어 둔다.
  onSave: (input: {
    title: string
    description: string
    status: Status
  }) => Promise<boolean>
  onCancel: () => void
}

function TaskEditForm({ task, onSave, onCancel }: Props) {
  const [title, setTitle] = useState(task.title)
  const [description, setDescription] = useState(task.description)
  const [status, setStatus] = useState<Status>(task.status)
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    // 제목을 비우고 저장하면 '제목없음'으로 채워 그 값으로 저장한다. (R-004)
    const ok = await onSave({ title: title.trim() || UNTITLED, description, status })
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
