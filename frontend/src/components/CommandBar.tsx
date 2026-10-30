import { useState, type FormEvent } from 'react'
import { PRIORITY_LABEL } from '../types'
import { COMMANDING, useCommand, type CommandLine } from '../useCommand'

function describe(line: CommandLine): string {
  if (line.kind === 'done') return `${line.label} — 완료로`
  if (line.kind === 'due') return `${line.label} — 마감을 ${line.value} 으로`
  const priority = PRIORITY_LABEL[line.priority ?? 'NORMAL']
  return `새 카드 「${line.label}」 — 우선순위 ${priority} · ${line.due_date ? `마감 ${line.due_date}` : '마감 없음'}`
}

interface Props {
  onUnauthorized: () => void
  // 적용이 끝났을 때. 보드가 목록을 다시 받는다.
  onApplied: () => void
}

// [오늘 브리핑] 아래 · 보드 위에 두는 입력란 하나와 [시키기] 버튼, 그 아래 확인 카드 · 안내.
function CommandBar({ onUnauthorized, onApplied }: Props) {
  const [text, setText] = useState('')
  const { pending, applying, message, lines, run, apply, cancel } = useCommand(onUnauthorized, onApplied)

  function submit(e: FormEvent) {
    e.preventDefault()
    void run(text)
  }

  return (
    <div className="briefing">
      <form className="task-form" onSubmit={submit}>
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="한 문장으로 시키기 (예: 결제 오류 내일까지로 하고 장보기 추가)"
          aria-label="한 문장으로 시키기"
          disabled={pending || applying}
        />
        <button type="submit" disabled={pending || applying}>
          {pending ? COMMANDING : '시키기'}
        </button>
      </form>
      {message && (
        <p className="suggest-note suggest-error" role="alert">
          {message}
        </p>
      )}
      {lines && (
        <section className="briefing-card" aria-label="시킨 내용 확인">
          <p className="briefing-heading">이렇게 바꿀까요? {lines.length}개</p>
          <ul className="briefing-later">
            {lines.map((line, i) => (
              <li key={i}>{describe(line)}</li>
            ))}
          </ul>
          <div className="briefing-actions">
            <button type="button" className="suggest-button" onClick={apply} disabled={applying}>
              적용
            </button>
            <button type="button" className="suggest-button" onClick={cancel} disabled={applying}>
              취소
            </button>
          </div>
        </section>
      )}
    </div>
  )
}

export default CommandBar
