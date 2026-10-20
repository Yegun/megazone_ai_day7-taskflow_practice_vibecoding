import { useEffect, useState } from 'react'
import { createTask, listTasks, updateTask } from '../api/tasks'
import { STATUSES, type Status, type Task } from '../types'
import TaskColumn from './TaskColumn'
import TaskForm from './TaskForm'

function TaskBoard() {
  // null = 아직 불러오지 못함. 빈 목록([])과 구분한다.
  const [tasks, setTasks] = useState<Task[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    listTasks()
      .then(setTasks)
      .catch((e: Error) => setError(`카드를 불러오지 못했습니다. (${e.message})`))
  }, [])

  async function handleCreate(input: { title: string; description: string }) {
    try {
      const created = await createTask(input)
      // 성공 응답을 받은 뒤에만 목록을 바꾼다. (D-003)
      setTasks((prev) => [...(prev ?? []), created])
      setError('')
      return true
    } catch (e) {
      setError(`등록하지 못했습니다. (${(e as Error).message})`)
      return false
    }
  }

  async function handleChangeStatus(task: Task, status: Status) {
    if (status === task.status) return
    try {
      const updated = await updateTask(task.id, { status })
      // 성공 응답을 받은 뒤에만 바꾼다. 실패하면 이전 상태 그대로. (D-003)
      setTasks((prev) =>
        (prev ?? []).map((t) => (t.id === updated.id ? updated : t)),
      )
      setError('')
    } catch (e) {
      setError(`상태를 바꾸지 못했습니다. (${(e as Error).message})`)
    }
  }

  return (
    <>
      <TaskForm onSubmit={handleCreate} />
      {error && <p className="error" role="alert">{error}</p>}
      {tasks && (
        <div className="board">
          {STATUSES.map((s) => (
            <TaskColumn
              key={s}
              status={s}
              tasks={tasks.filter((t) => t.status === s)}
              onChangeStatus={handleChangeStatus}
            />
          ))}
        </div>
      )}
    </>
  )
}

export default TaskBoard
