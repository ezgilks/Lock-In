import { useEffect, useMemo, useState, useCallback } from 'react'
import { getDashboard, getHabits, completeHabit } from './api'
import OverallRating from './components/OverallRating'
import CategoryRadarChart from './components/CategoryRadarChart'
import CategoryProgressList from './components/CategoryProgressList'

function App() {
  const [dashboard, setDashboard] = useState(null)
  const [habits, setHabits] = useState(null)
  const [error, setError] = useState(null)
  const [completingId, setCompletingId] = useState(null)

  const load = useCallback(() => {
    Promise.all([getDashboard(), getHabits()])
      .then(([dashboardData, habitsData]) => {
        setDashboard(dashboardData)
        setHabits(habitsData)
        setError(null)
      })
      .catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const habitsByCategory = useMemo(() => {
    const map = new Map()
    for (const h of habits ?? []) {
      if (!map.has(h.category_id)) map.set(h.category_id, [])
      map.get(h.category_id).push(h)
    }
    return map
  }, [habits])

  const handleComplete = useCallback(async (habitId) => {
    setCompletingId(habitId)
    try {
      await completeHabit(habitId)
      const [d, h] = await Promise.all([getDashboard(), getHabits()])
      setDashboard(d)
      setHabits(h)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setCompletingId(null)
    }
  }, [])

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
      <div className="mx-auto max-w-3xl px-6 py-10">
        <div className="mb-8 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">
            Lock In
          </h1>
          <button
            type="button"
            onClick={load}
            className="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 dark:border-neutral-800 dark:text-neutral-300 dark:hover:bg-neutral-900"
          >
            Refresh
          </button>
        </div>

        {error && (
          <p className="mb-6 rounded-lg bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
            {error}
          </p>
        )}

        {!error && !dashboard && (
          <p className="text-neutral-500 dark:text-neutral-400">Loading…</p>
        )}

        {dashboard && dashboard.categories.length === 0 && (
          <p className="text-neutral-500 dark:text-neutral-400">
            No categories yet — create one to get started.
          </p>
        )}

        {dashboard && dashboard.categories.length > 0 && (
          <div className="flex flex-col gap-6">
            <OverallRating ovr={dashboard.ovr} />
            <CategoryRadarChart categories={dashboard.categories} />
            <CategoryProgressList
              categories={dashboard.categories}
              habitsByCategory={habitsByCategory}
              completingId={completingId}
              onComplete={handleComplete}
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default App
