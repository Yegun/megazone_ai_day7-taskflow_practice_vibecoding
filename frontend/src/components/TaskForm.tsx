import { useState, type FormEvent } from 'react'

interface Props {
  // 저장이 성공하면 true. 실패하면 false 를 돌려주고 입력값은 남긴다.
  onSubmit: (input: { title: string; description: string }) => Promise<boolean>
}

function TaskForm({ onSubmit }: Props) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
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
    const ok = await onSubmit({ title, description })
    setSaving(false)
    if (ok) {
      setTitle('')
      setDescription('')
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
      <button type="submit" disabled={saving}>
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
