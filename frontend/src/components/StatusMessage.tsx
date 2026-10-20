import type { ReactNode } from 'react'

interface Props {
  kind: 'loading' | 'empty' | 'error'
  children: ReactNode
  // 있으면 "다시 시도" 버튼을 보여 준다.
  onRetry?: () => void
}

function StatusMessage({ kind, children, onRetry }: Props) {
  return (
    <div
      className={`status-message ${kind}`}
      role={kind === 'error' ? 'alert' : 'status'}
    >
      <p>{children}</p>
      {onRetry && (
        <button type="button" onClick={onRetry}>
          다시 시도
        </button>
      )}
    </div>
  )
}

export default StatusMessage
