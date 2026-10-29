import { PLANNING, useWeekPlan, type WeekPlanView } from '../useWeekPlan'
import './weekplan.css'

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

// YYYY-MM-DD → YYYY-MM-DD(요일). 시간대에 흔들리지 않게 숫자로 나눠 로컬 날짜로 만든다.
function label(date: string): string {
  const [y, m, d] = date.split('-').map(Number)
  return `${date}(${WEEKDAYS[new Date(y, m - 1, d).getDay()]})`
}

interface CardProps {
  view: WeekPlanView
  onClose: () => void
}

// 일주일 계획 카드 한 장. 날짜마다 같은 모양으로 할 일 제목들 · 조언 한 줄 · 닫기.
export function WeekPlanCard({ view, onClose }: CardProps) {
  return (
    <section className="weekplan-card" aria-label="이번 주 계획">
      <ul className="weekplan-list">
        {view.days.map((day) => (
          <li key={day.date}>
            <span className="weekplan-date">{label(day.date)}</span>
            <span className="weekplan-titles">{day.titles.length > 0 ? day.titles.join(', ') : '—'}</span>
          </li>
        ))}
      </ul>
      {view.note && <p className="weekplan-note">{view.note}</p>}
      <div className="weekplan-actions">
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

// 보드 위, [오늘 브리핑] 아래에 두는 [이번 주 계획] 버튼과 그 아래 카드 · 안내.
function WeekPlan({ onUnauthorized }: Props) {
  const { pending, message, view, run, close } = useWeekPlan(onUnauthorized)
  return (
    <div className="weekplan">
      <button type="button" className="suggest-button" onClick={run} disabled={pending}>
        {pending ? PLANNING : '이번 주 계획'}
      </button>
      {message && (
        <p className="suggest-note suggest-error" role="alert">
          {message}
        </p>
      )}
      {view && <WeekPlanCard view={view} onClose={close} />}
    </div>
  )
}

export default WeekPlan
