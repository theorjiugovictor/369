import { BookOpen } from 'lucide-react'

export default function BriefingCard({ briefing }) {
  if (!briefing) {
    return (
      <div className="bg-earth-900/40 border border-earth-800/60 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-3">
          <BookOpen className="w-4 h-4 text-earth-500" />
          <h2 className="font-medium text-earth-500">Daily Briefing</h2>
        </div>
        <p className="text-xs text-earth-600 font-mono">awaiting awareness agent…</p>
      </div>
    )
  }

  const ts = new Date(briefing.timestamp).toLocaleString([], {
    weekday: 'short', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })

  return (
    <div className="bg-earth-900/40 border border-moss-600/30 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-moss-400" />
          <h2 className="font-medium text-earth-100">Daily Briefing</h2>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-earth-500">
          {briefing.source && (
            <span className="bg-earth-800/60 px-2 py-0.5 rounded">{briefing.source}</span>
          )}
          <span>{ts}</span>
        </div>
      </div>
      <p className="text-sm text-earth-300 leading-relaxed">{briefing.insight}</p>
      {briefing.domains_analyzed?.length > 0 && (
        <div className="flex items-center gap-1.5 mt-3 flex-wrap">
          {briefing.domains_analyzed.map(d => (
            <span key={d} className="text-xs font-mono text-earth-500 bg-earth-800/60 px-2 py-0.5 rounded">
              {d}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
