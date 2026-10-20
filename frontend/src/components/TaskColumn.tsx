import { STATUS_LABEL, type Status, type Task } from '../types'
import TaskCard from './TaskCard'

function TaskColumn({ status, tasks }: { status: Status; tasks: Task[] }) {
  return (
    <section className="task-column" aria-label={STATUS_LABEL[status]}>
      <h2>{STATUS_LABEL[status]}</h2>
      <ul>
        {tasks.map((t) => (
          <TaskCard key={t.id} task={t} />
        ))}
      </ul>
    </section>
  )
}

export default TaskColumn
