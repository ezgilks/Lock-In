export default function OverallRating({ ovr }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-neutral-200 bg-white p-8 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <span className="text-sm font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
        Overall Rating
      </span>
      <span className="mt-2 text-6xl font-bold tabular-nums text-neutral-900 dark:text-neutral-50">
        {ovr.toFixed(1)}
      </span>
    </div>
  )
}
