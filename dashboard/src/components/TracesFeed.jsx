import { ScrollText } from 'lucide-react'

const TYPE_STYLES = {
  observation:    'text-earth-400 border-earth-700/50',
  action:         'text-sky-400 border-sky-800/50',
  recommendation: 'text-moss-400 border-moss-700/50',
  alert:          'text-red-400 border-red-800/50',
}

const DOMAIN_EMOJI = {
  soil: '🌱', water: '💧', weather: '☁️', compost: '♻️',
  energy: '⚡', livestock: '🐄', system: '⚙️',
}

export default function TracesFeed({ traces }) {
  const list = traces?.traces || []

  return (
    <div className="bg-earth-900/40 border border-earth-800/60 rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <ScrollText className="w-4 h-4 text-earth-500" />
        <h2 className="font-medium text-earth-100">Activity Feed</h2>
        <span className="ml-auto text-xs font-mono text-earth-600">{list.length} traces</span>
      </div>

      {list.length === 0 ? (
        <p className="text-xs text-earth-600 font-mono text-center py-6">no traces yet</p>
      ) : (
        <div className="space-y-1.5 max-h-96 overflow-y-auto pr-1">
          {list.map(t => {
            const style = TYPE_STYLES[t.type] || TYPE_STYLES.observation
            const emoji = DOMAIN_EMOJI[t.domain] || '•'
            const summary = t.payload?.type
              || t.payload?.alert
              || t.payload?.recommendation
              || t.payload?.action
              || t.payload?.summary
              || t.payload?.metric
              || t.type

            const ts = new Date(t.timestamp).toLocaleTimeString([], {
              hour: '2-digit', minute: '2-digit', second: '2-digit',
            })

            return (
              <div key={t.id} className={`flex items-start gap-2.5 border rounded-lg px-3 py-2 text-xs ${style}`}>
                <span className="mt-0.5">{emoji}</span>
                <div className="flex-1 min-w-0">
                  <span className="truncate block text-earth-300">{summary}</span>
                  <div className="flex gap-2 mt-0.5 opacity-60 font-mono">
                    <span className="uppercase">{t.type}</span>
                    <span>·</span>
                    <span>{t.agent_id}</span>
                    {t.location && <><span>·</span><span>{t.location}</span></>}
                    <span className="ml-auto">{ts}</span>
                  </div>
                </div>
                {t.confidence != null && (
                  <span className="font-mono text-earth-600 flex-shrink-0">
                    {(t.confidence * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
