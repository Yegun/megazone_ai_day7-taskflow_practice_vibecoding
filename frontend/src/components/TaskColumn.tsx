import { STATUS_LABEL, type Status, type Task } from '../types'
import TaskCard from './TaskCard'

interface Props {
  status: Status
  tasks: Task[]
  onChangeStatus: (task: Task, status: Status) => void
}

function TaskColumn({ status, tasks, onChangeStatus }: Props) {
  return (
    <section className="task-column" aria-label={STATUS_LABEL[status]}>
      <h2>{STATUS_LABEL[status]}</h2>
      <ul>
        {tasks.map((t) => (
          <TaskCard key={t.id} task={t} onChangeStatus={onChangeStatus} />
        ))}
      </ul>
    </section>
  )
}

export default TaskColumn
