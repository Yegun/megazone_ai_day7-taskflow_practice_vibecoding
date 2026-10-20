import { STATUSES, STATUS_LABEL, type Status, type Task } from '../types'

interface Props {
  task: Task
  onChangeStatus: (task: Task, status: Status) => void
}

function TaskCard({ task, onChangeStatus }: Props) {
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
    </li>
  )
}

export default TaskCard
