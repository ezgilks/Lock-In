import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from 'recharts'

export default function CategoryRadarChart({ categories }) {
  const data = categories.map((c) => ({ subject: c.name, level: c.current_level }))
  const maxLevel = Math.max(3, ...data.map((d) => d.level))

  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <h2 className="mb-2 text-sm font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
        Level by Category
      </h2>
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={data} outerRadius="70%">
          <PolarGrid stroke="currentColor" className="text-neutral-200 dark:text-neutral-700" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: 'currentColor' }}
            className="text-neutral-600 dark:text-neutral-300"
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, maxLevel]}
            allowDecimals={false}
            tick={{ fill: 'currentColor' }}
            className="text-neutral-400 dark:text-neutral-500"
          />
          <Radar
            name="Level"
            dataKey="level"
            stroke="#6366f1"
            fill="#6366f1"
            fillOpacity={0.35}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
