import { SUGGESTING } from '../useSuggest'

interface ButtonProps {
  pending: boolean
  onClick: () => void
}

// 제목 · 설명 옆에 두는 버튼. 요청 중에는 잠근다.
export function SuggestButton({ pending, onClick }: ButtonProps) {
  return (
    <button type="button" className="suggest-button" onClick={onClick} disabled={pending}>
      AI 제안
    </button>
  )
}

interface NoteProps {
  pending: boolean
  message: string
  reason: string
}

// 우선순위 · 마감일 아래에 두는 안내 한 줄. 대기 · 실패 · 제안 이유 중 하나만 보인다.
export function SuggestNote({ pending, message, reason }: NoteProps) {
  if (pending) {
    return (
      <p className="suggest-note" role="status">
        {SUGGESTING}
      </p>
    )
  }
  if (message) {
    return (
      <p className="suggest-note suggest-error" role="alert">
        {message}
      </p>
    )
  }
  if (reason) return <p className="suggest-note">AI 제안 이유: {reason}</p>
  return null
}
