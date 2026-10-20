import { useState } from 'react'
import { STATUSES, STATUS_LABEL, type Status, type Task } from '../types'
import TaskEditForm from './TaskEditForm'

interface Props {
  task: Task
  onChangeStatus: (task: Task, status: Status) => void
  onSave: (
    task: Task,
    input: { title: string; description: string; status: Status },
  ) => Promise<boolean>
  onDelete: (task: Task) => void
}

function TaskCard({ task, onChangeStatus, onSave, onDelete }: Props) {
  const [editing, setEditing] = useState(false)

  if (editing) {
    return (
      <li className="task-card">
        <TaskEditForm
          task={task}
          onSave={(input) => onSave(task, input)}
          onCancel={() => setEditing(false)}
        />
      </li>
    )
  }

  return (
    <li className="task-card">
      <strong>{task.title}</strong>
      {task.description && <p>{task.description}</p>}
      {/* 선택값은 task.status 에 고정(controlled). 성공 응답으로 목록이 바뀌면 카드가 옮겨간다. (D-003) */}
      <select
        aria-label={`${task.title} 상태`}
        value={task.status}
        onChange={(e) => onChangeStatus(task, e.target.value as Status)}
      >
        {STATUSES.map((s) => (
          <option key={s} value={s}>
            {STATUS_LABEL[s]}
          </option>
        ))}
      </select>
      <div className="actions">
        <button type="button" onClick={() => setEditing(true)}>
          수정
        </button>
        <button type="button" onClick={() => onDelete(task)}>
          삭제
        </button>
      </div>
    </li>
  )
}

export default TaskCard
