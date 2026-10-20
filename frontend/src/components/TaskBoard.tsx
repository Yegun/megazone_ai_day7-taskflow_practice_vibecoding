import { useEffect, useState } from 'react'
import { createTask, deleteTask, listTasks, updateTask } from '../api/tasks'
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

  // 상태 변경과 내용 수정이 같은 흐름이다. 성공 응답을 받은 뒤에만 바꾼다. (D-003)
  async function handleUpdate(
    task: Task,
    input: { title?: string; description?: string; status?: Status },
    failMessage: string,
  ) {
    try {
      const updated = await updateTask(task.id, input)
      setTasks((prev) =>
        (prev ?? []).map((t) => (t.id === updated.id ? updated : t)),
      )
      setError('')
      return true
    } catch (e) {
      setError(`${failMessage} (${(e as Error).message})`)
      return false
    }
  }

  function handleChangeStatus(task: Task, status: Status) {
    if (status === task.status) return
    void handleUpdate(task, { status }, '상태를 바꾸지 못했습니다.')
  }

  function handleSave(
    task: Task,
    input: { title: string; description: string; status: Status },
  ) {
    return handleUpdate(task, input, '수정하지 못했습니다.')
  }

  async function handleDelete(task: Task) {
    // 삭제 전에 한 번 묻는다. 취소하면 아무 일도 없다. (D-015)
    if (!window.confirm(`"${task.title}" 카드를 삭제할까요?`)) return
    try {
      await deleteTask(task.id)
      setTasks((prev) => (prev ?? []).filter((t) => t.id !== task.id))
      setError('')
    } catch (e) {
      setError(`삭제하지 못했습니다. (${(e as Error).message})`)
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
              onSave={handleSave}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </>
  )
}

export default TaskBoard
