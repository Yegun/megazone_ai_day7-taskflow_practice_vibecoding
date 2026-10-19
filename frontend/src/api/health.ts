export async function getHealth(): Promise<{ status: string }> {
  const res = await fetch('/api/health')
  if (!res.ok) throw new Error(`API 오류: ${res.status}`)
  return res.json()
}
