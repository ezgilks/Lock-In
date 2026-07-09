export default function CategoryProgressList({ categories, habitsByCategory, completingId, onComplete }) {
  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <h2 className="mb-4 text-sm font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
        Categories
      </h2>
      <ul className="flex flex-col gap-5">
        {categories.map((c) => {
          const span = c.xp_for_next_level - c.xp_for_current_level
          const progress = span > 0 ? (c.current_xp - c.xp_for_current_level) / span : 0
          const pct = Math.min(100, Math.max(0, progress * 100))
          const habits = habitsByCategory.get(c.id) ?? []

          return (
            <li key={c.id}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="flex items-center gap-2 font-medium text-neutral-800 dark:text-neutral-100">
                  <span
                    className="inline-block h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: c.color }}
                  />
                  {c.name}
                </span>
                <span className="text-neutral-500 dark:text-neutral-400">
                  Lvl {c.current_level}
                  {c.streak_days > 0 && ` · 🔥 ${c.streak_days}`}
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${pct}%`, backgroundColor: c.color }}
                />
              </div>
              <div className="mt-1 text-right text-xs text-neutral-400 dark:text-neutral-500">
                {c.current_xp} / {c.xp_for_next_level} xp
              </div>

              {habits.length > 0 && (
                <ul className="mt-3 flex flex-col gap-1.5">
                  {habits.map((h) => (
                    <li
                      key={h.id}
                      className="flex items-center justify-between rounded-lg bg-neutral-50 px-3 py-1.5 text-sm dark:bg-neutral-800/60"
                    >
                      <span className="text-neutral-700 dark:text-neutral-200">{h.name}</span>
                      <button
                        type="button"
                        disabled={completingId === h.id}
                        onClick={() => onComplete(h.id)}
                        className="rounded-md px-2 py-1 text-xs font-medium text-white disabled:opacity-50"
                        style={{ backgroundColor: c.color }}
                      >
                        {completingId === h.id ? '…' : 'Complete'}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
