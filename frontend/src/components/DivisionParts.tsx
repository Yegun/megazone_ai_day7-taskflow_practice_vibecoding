import { DIVIDING } from '../useDivision'
import { PRIORITY_LABEL, type DivisionItem } from '../types'

interface ButtonProps {
  disabled: boolean
  onClick: () => void
}

// [AI 제안] 옆에 두는 버튼. 요청 중에는 잠근다.
export function DivisionButton({ disabled, onClick }: ButtonProps) {
  return (
    <button type="button" className="suggest-button" onClick={onClick} disabled={disabled}>
      AI로 할 일 만들기
    </button>
  )
}

interface NoteProps {
  pending: boolean
  message: string
}

// 대기 · 실패 안내 한 줄. 둘 중 하나만 보인다.
export function DivisionNote({ pending, message }: NoteProps) {
  if (pending) {
    return (
      <p className="suggest-note" role="status">
        {DIVIDING}
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
  return null
}

interface PanelProps {
  items: DivisionItem[]
  // 모두 등록하는 중에는 두 버튼을 잠근다.
  busy: boolean
  onRegisterAll: () => void
  onCancel: () => void
}

// 등록 전 미리 보기. 한 줄에 할 일 하나. 마감일은 월-일만 보이고, 없으면 "-".
export function DivisionPanel({ items, busy, onRegisterAll, onCancel }: PanelProps) {
  return (
    <section className="division-panel" aria-label="AI가 만든 할 일">
      <p className="division-heading">AI가 만든 할 일 {items.length}개</p>
      <ul className="division-list">
        {items.map((item, i) => (
          <li key={i}>
            <span className="division-title">{item.title}</span>
            <span className={`division-priority priority-${item.priority.toLowerCase()}`}>
              우선순위 {PRIORITY_LABEL[item.priority]}
            </span>
            <span className="division-due">{item.due_date ? item.due_date.slice(5) : '-'}</span>
          </li>
        ))}
      </ul>
      <div className="division-actions">
        <button type="button" onClick={onRegisterAll} disabled={busy}>
          모두 등록
        </button>
        <button type="button" onClick={onCancel} disabled={busy}>
          취소
        </button>
      </div>
    </section>
  )
}
