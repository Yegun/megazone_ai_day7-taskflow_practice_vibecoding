import { BRIEFING, useBriefing, type BriefingView } from '../useBriefing'

const MARKS = ['①', '②', '③']

interface CardProps {
  view: BriefingView
  onClose: () => void
}

// 브리핑 카드 한 장. 먼저 할 일(제목 — 이유) · 미뤄도 되는 일(제목만) · 응원 한 줄.
export function BriefingCard({ view, onClose }: CardProps) {
  return (
    <section className="briefing-card" aria-label="오늘 브리핑">
      {view.top3.length > 0 && (
        <>
          <p className="briefing-heading">먼저 할 일</p>
          <ol className="briefing-list">
            {view.top3.map((item, i) => (
              <li key={item.id}>
                <span className="briefing-mark">{MARKS[i]}</span>
                <span>
                  <span className="briefing-title">{item.title}</span> — {item.reason}
                </span>
              </li>
            ))}
          </ol>
        </>
      )}
      {view.later.length > 0 && (
        <>
          <p className="briefing-heading">미뤄도 되는 일</p>
          <ul className="briefing-later">
            {view.later.map((item) => (
              <li key={item.id}>{item.title}</li>
            ))}
          </ul>
        </>
      )}
      <p className="briefing-cheer">{view.cheer}</p>
      <div className="briefing-actions">
        <button type="button" className="suggest-button" onClick={onClose}>
          닫기
        </button>
      </div>
    </section>
  )
}

interface Props {
  onUnauthorized: () => void
}

// 보드 위에 두는 [오늘 브리핑] 버튼과 그 아래 카드 · 안내.
function Briefing({ onUnauthorized }: Props) {
  const { pending, message, view, run, close } = useBriefing(onUnauthorized)
  return (
    <div className="briefing">
      <button type="button" className="suggest-button" onClick={run} disabled={pending}>
        {pending ? BRIEFING : '오늘 브리핑'}
      </button>
      {message && (
        <p className="suggest-note suggest-error" role="alert">
          {message}
        </p>
      )}
      {view && <BriefingCard view={view} onClose={close} />}
    </div>
  )
}

export default Briefing
