export async function getDashboard() {
  const res = await fetch('/api/dashboard')
  if (!res.ok) {
    throw new Error(`GET /dashboard failed: ${res.status}`)
  }
  return res.json()
}

export async function getHabits() {
  const res = await fetch('/api/habits')
  if (!res.ok) {
    throw new Error(`GET /habits failed: ${res.status}`)
  }
  return res.json()
}

export async function completeHabit(habitId) {
  const res = await fetch(`/api/habits/${habitId}/complete`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ idempotency_key: crypto.randomUUID() }),
  })
  if (!res.ok) {
    throw new Error(`POST /habits/${habitId}/complete failed: ${res.status}`)
  }
  return res.json()
}
