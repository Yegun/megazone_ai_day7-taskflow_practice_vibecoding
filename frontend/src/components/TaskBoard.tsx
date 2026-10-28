import { useCallback, useEffect, useState } from 'react'
import {
  createTask,
  deleteTask,
  describeError,
  isNotFound,
  isUnauthorized,
  listTasks,
  updateTask,
} from '../api/tasks'
import { STATUSES, type Priority, type Status, type Task, type TaskEdit } from '../types'
import StatusMessage from './StatusMessage'
import TaskColumn from './TaskColumn'
import TaskForm from './TaskForm'

type LoadState = 'loading' | 'ready' | 'failed'

interface Props {
  // 세션이 만료되어 401 을 받았을 때. 로그인 화면으로 돌아간다.
  onUnauthorized: () => void
}

function TaskBoard({ onUnauthorized }: Props) {
  // 불러오기 실패(failed)는 빈 목록(ready + [])과 구분해서 보여 준다.
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [tasks, setTasks] = useState<Task[]>([])
  const [loadError, setLoadError] = useState('')
  // 등록 · 수정 · 삭제가 실패했을 때의 알림. 목록은 바뀌지 않는다. (D-003)
  const [error, setError] = useState('')

  const fetchTasks = useCallback(() => {
    listTasks()
      .then((list) => {
        setTasks(list)
        setLoadState('ready')
      })
      .catch((e: unknown) => {
        if (isUnauthorized(e)) return onUnauthorized()
        setLoadError(describeError(e))
        setLoadState('failed')
      })
  }, [onUnauthorized])

  // 처음 열 때. 상태는 이미 'loading' 이다.
  useEffect(fetchTasks, [fetchTasks])

  function retry() {
    setLoadState('loading')
    fetchTasks()
  }

  // 없는 카드를 고치거나 지우려 했을 때 목록을 저장소와 맞춘다. 실패하면 지금 목록을 그대로 둔다.
  function refresh() {
    listTasks()
      .then(setTasks)
      .catch(() => {})
  }

  function fail(message: string, e: unknown) {
    if (isUnauthorized(e)) return onUnauthorized()
    setError(`${message} ${describeError(e)}`)
    if (isNotFound(e)) refresh()
  }

  async function handleCreate(input: {
    title: string
    description: string
    priority: Priority
    due_date?: string
  }) {
    try {
      const created = await createTask(input)
      // 성공 응답을 받은 뒤에만 목록을 바꾼다. (D-003)
      setTasks((prev) => [...prev, created])
      setError('')
      // 순서는 서버가 정한다. 다시 불러와 서버 정렬을 따른다. (R-011)
      refresh()
      return true
    } catch (e) {
      fail('등록하지 못했습니다.', e)
      return false
    }
  }

  // 상태 변경과 내용 수정이 같은 흐름이다. 성공 응답을 받은 뒤에만 바꾼다. (D-003)
  async function handleUpdate(
    task: Task,
    input: Partial<TaskEdit>,
    failMessage: string,
  ) {
    try {
      const updated = await updateTask(task.id, input)
      setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
      setError('')
      // 우선순위 · 마감일 · 상태가 바뀌면 순서도 바뀐다. 서버 정렬을 다시 받는다. (R-011)
      refresh()
      return true
    } catch (e) {
      fail(failMessage, e)
      return false
    }
  }

  async function handleChangeStatus(task: Task, status: Status) {
    if (status === task.status) return
    await handleUpdate(task, { status }, '상태를 바꾸지 못했습니다.')
  }

  function handleSave(task: Task, input: TaskEdit) {
    return handleUpdate(task, input, '수정하지 못했습니다.')
  }

  async function handleDelete(task: Task) {
    // 삭제 전에 한 번 묻는다. 취소하면 아무 일도 없다. (D-015)
    if (!window.confirm(`"${task.title}" 카드를 삭제할까요?`)) return
    try {
      await deleteTask(task.id)
      setTasks((prev) => prev.filter((t) => t.id !== task.id))
      setError('')
    } catch (e) {
      fail('삭제하지 못했습니다.', e)
    }
  }

  return (
    <>
      <TaskForm
        onSubmit={handleCreate}
        disabled={loadState !== 'ready'}
        onUnauthorized={onUnauthorized}
      />

      {loadState === 'loading' && (
        <StatusMessage kind="loading">불러오는 중...</StatusMessage>
      )}

      {loadState === 'failed' && (
        <StatusMessage kind="error" onRetry={retry}>
          카드를 불러오지 못했습니다. {loadError}
        </StatusMessage>
      )}

      {loadState === 'ready' && (
        <>
          {error && <StatusMessage kind="error">{error}</StatusMessage>}
          {tasks.length === 0 && (
            <StatusMessage kind="empty">
              아직 Task가 없습니다. 위에서 첫 Task를 만들어 보세요.
            </StatusMessage>
          )}
          <div className="board">
            {STATUSES.map((s) => (
              <TaskColumn
                key={s}
                status={s}
                tasks={tasks.filter((t) => t.status === s)}
                onChangeStatus={handleChangeStatus}
                onSave={handleSave}
                onDelete={handleDelete}
                onUnauthorized={onUnauthorized}
              />
            ))}
          </div>
        </>
      )}
    </>
  )
}

export default TaskBoard
