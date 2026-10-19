import { useEffect, useState } from 'react'
import { getHealth } from './api/health'

function App() {
  const [api, setApi] = useState('확인 중...')

  useEffect(() => {
    getHealth()
      .then((h) => setApi(h.status))
      .catch((e: Error) => setApi(`연결 실패 (${e.message})`))
  }, [])

  return (
    <main>
      <h1>task-flow</h1>
      <p>API 상태: {api}</p>
    </main>
  )
}

export default App
