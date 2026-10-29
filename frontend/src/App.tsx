import { useEffect, useState } from 'react'
import { getMe, logout } from './api/auth'
import { isUnauthorized } from './api/tasks'
import AuthForm from './components/AuthForm'
import Briefing from './components/BriefingCard'
import WeekPlan from './components/WeekPlanCard'
import StatusMessage from './components/StatusMessage'
import TaskBoard from './components/TaskBoard'
import UserBar from './components/UserBar'
import type { User } from './types'

// checking: 로그인 여부를 확인하는 중. failed: 서버에 연결하지 못함(로그인 안 됨과 구분한다).
type Auth = { kind: 'checking' } | { kind: 'failed' } | { kind: 'anonymous' } | { kind: 'user'; user: User }

const EXPIRED_NOTICE = '로그인이 만료되었습니다. 다시 로그인해 주세요.'

function App() {
  const [auth, setAuth] = useState<Auth>({ kind: 'checking' })
  const [notice, setNotice] = useState('')

  function check() {
    getMe()
      .then((user) => setAuth({ kind: 'user', user }))
      .catch((e: unknown) => setAuth({ kind: isUnauthorized(e) ? 'anonymous' : 'failed' }))
  }

  // 열릴 때 로그인 여부를 확인한다. 상태는 이미 'checking' 이다.
  useEffect(check, [])

  async function handleLogout() {
    try {
      await logout()
    } catch (e) {
      // 이미 만료된 세션이면 로그아웃된 것과 같다. 연결 실패면 로그인 상태를 유지한다.
      if (!isUnauthorized(e)) return
    }
    setNotice('')
    setAuth({ kind: 'anonymous' })
  }

  // 화면을 쓰는 동안 세션이 만료되면(401) 로그인 화면으로 돌아간다.
  function handleUnauthorized() {
    setNotice(EXPIRED_NOTICE)
    setAuth({ kind: 'anonymous' })
  }

  return (
    <main>
      <h1>task-flow</h1>
      {auth.kind === 'checking' && <StatusMessage kind="loading">확인하는 중...</StatusMessage>}
      {auth.kind === 'failed' && (
        <StatusMessage
          kind="error"
          onRetry={() => {
            setAuth({ kind: 'checking' })
            check()
          }}
        >
          서버에 연결하지 못했습니다. 서버가 켜져 있는지 확인해 주세요.
        </StatusMessage>
      )}
      {auth.kind === 'anonymous' && (
        <AuthForm
          notice={notice}
          onAuthenticated={(user) => {
            setNotice('')
            setAuth({ kind: 'user', user })
          }}
        />
      )}
      {auth.kind === 'user' && (
        <>
          <UserBar user={auth.user} onLogout={handleLogout} />
          <Briefing key={auth.user.id} onUnauthorized={handleUnauthorized} />
          <WeekPlan key={auth.user.id} onUnauthorized={handleUnauthorized} />
          {/* key: 다른 계정으로 로그인하면 이전 사용자의 목록 상태를 버린다. */}
          <TaskBoard key={auth.user.id} onUnauthorized={handleUnauthorized} />
        </>
      )}
    </main>
  )
}

export default App
