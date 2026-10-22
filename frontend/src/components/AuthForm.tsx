import { useState, type FormEvent } from 'react'
import { login, register } from '../api/auth'
import { ApiError } from '../api/tasks'
import type { User } from '../types'

interface Props {
  onAuthenticated: (user: User) => void
  // 세션이 만료되어 돌아왔을 때 보여 줄 안내.
  notice?: string
}

type Mode = 'login' | 'register'

// 실패 원인을 구분해서 안내한다. 로그인 실패는 아이디 · 비밀번호 중 무엇이 틀렸는지 알리지 않는다.
function describeAuthError(e: unknown, mode: Mode): string {
  if (e instanceof ApiError) {
    if (e.status === 401) return '아이디 또는 비밀번호가 올바르지 않습니다.'
    if (e.status === 409) return '이미 사용 중인 아이디입니다.'
    if (e.status === 422) {
      return mode === 'register'
        ? '아이디는 영문 · 숫자 4~20자, 비밀번호는 8~128자로 입력해 주세요.'
        : '아이디와 비밀번호를 입력해 주세요.'
    }
  }
  return '서버에 연결하지 못했습니다. 서버가 켜져 있는지 확인해 주세요.'
}

function AuthForm({ onAuthenticated, notice }: Props) {
  const [mode, setMode] = useState<Mode>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    // 화면은 빈 입력만 먼저 안내한다. 규칙의 최종 판정은 API. (D-004)
    if (!username.trim() || !password) {
      setError('아이디와 비밀번호를 입력해 주세요.')
      return
    }
    setError('')
    setBusy(true)
    try {
      const user = await (mode === 'login' ? login : register)(username, password)
      onAuthenticated(user)
    } catch (err) {
      setError(describeAuthError(err, mode))
      setBusy(false)
    }
  }

  function switchMode() {
    setMode(mode === 'login' ? 'register' : 'login')
    setError('')
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <h2>{mode === 'login' ? '로그인' : '가입'}</h2>
      {notice && <p className="hint">{notice}</p>}
      <input
        aria-label="아이디"
        placeholder="아이디 (영문 · 숫자)"
        autoComplete="username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />
      <input
        aria-label="비밀번호"
        type="password"
        placeholder="비밀번호"
        autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <button type="submit" disabled={busy}>
        {mode === 'login' ? '로그인' : '가입'}
      </button>
      <button type="button" className="link" onClick={switchMode}>
        {mode === 'login' ? '계정이 없나요? 가입' : '이미 계정이 있나요? 로그인'}
      </button>
    </form>
  )
}

export default AuthForm
