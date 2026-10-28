import { useState } from 'react'
import {
  PRIORITY_LABEL,
  STATUSES,
  STATUS_LABEL,
  type Status,
  type Task,
  type TaskEdit,
} from '../types'
import TaskEditForm from './TaskEditForm'

interface Props {
  task: Task
  onChangeStatus: (task: Task, status: Status) => void
  onSave: (task: Task, input: TaskEdit) => Promise<boolean>
  onDelete: (task: Task) => void
  onUnauthorized: () => void
}

function TaskCard({ task, onChangeStatus, onSave, onDelete, onUnauthorized }: Props) {
  const [editing, setEditing] = useState(false)

  if (editing) {
    return (
      <li className="task-card">
        <TaskEditForm
          task={task}
          onSave={(input) => onSave(task, input)}
          onCancel={() => setEditing(false)}
          onUnauthorized={onUnauthorized}
        />
      </li>
    )
  }

  return (
    <li className={task.is_overdue ? 'task-card overdue' : 'task-card'}>
      <strong>{task.title}</strong>
      {task.description && <p>{task.description}</p>}
      <div className="meta">
        <span className={`badge priority-${task.priority.toLowerCase()}`}>
          우선순위 {PRIORITY_LABEL[task.priority]}
        </span>
        {task.due_date && <span className="due">마감 {task.due_date}</span>}
        {/* 색만으로 구분하지 않도록 텍스트를 함께 쓴다. 판단은 서버가 준 값을 따른다. (R-010) */}
        {task.is_overdue && <span className="badge overdue-badge">기한 초과</span>}
      </div>
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
