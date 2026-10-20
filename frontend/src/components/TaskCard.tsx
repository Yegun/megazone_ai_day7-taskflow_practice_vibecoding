import type { Task } from '../types'

function TaskCard({ task }: { task: Task }) {
  return (
    <li className="task-card">
      <strong>{task.title}</strong>
      {task.description && <p>{task.description}</p>}
    </li>
  )
}

export default TaskCard
