import { STATUS_LABEL, type Status, type Task, type TaskEdit } from '../types'
import TaskCard from './TaskCard'

interface Props {
  status: Status
  tasks: Task[]
  onChangeStatus: (task: Task, status: Status) => void
  onSave: (task: Task, input: TaskEdit) => Promise<boolean>
  onDelete: (task: Task) => void
  onUnauthorized: () => void
}

function TaskColumn({
  status,
  tasks,
  onChangeStatus,
  onSave,
  onDelete,
  onUnauthorized,
}: Props) {
  return (
    <section className="task-column" aria-label={STATUS_LABEL[status]}>
      <h2>{STATUS_LABEL[status]}</h2>
      <ul>
        {tasks.map((t) => (
          <TaskCard
            key={t.id}
            task={t}
            onChangeStatus={onChangeStatus}
            onSave={onSave}
            onDelete={onDelete}
            onUnauthorized={onUnauthorized}
          />
        ))}
      </ul>
    </section>
  )
}

export default TaskColumn
