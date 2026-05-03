import { AlertTriangle, Lightbulb, Info } from 'lucide-react'

const DOMAIN_COLORS = {
  soil:      'text-amber-400 bg-amber-900/20 border-amber-800/40',
  water:     'text-sky-400 bg-sky-900/20 border-sky-800/40',
  weather:   'text-blue-400 bg-blue-900/20 border-blue-800/40',
  compost:   'text-orange-400 bg-orange-900/20 border-orange-800/40',
  energy:    'text-yellow-400 bg-yellow-900/20 border-yellow-800/40',
  system:    'text-earth-400 bg-earth-800/20 border-earth-700/40',
  livestock: 'text-green-400 bg-green-900/20 border-green-800/40',
}

function TraceItem({ trace }) {
  const isAlert = trace.type === 'alert'
  const isRec = trace.type === 'recommendation'
  const colorClass = DOMAIN_COLORS[trace.domain] || DOMAIN_COLORS.system

  const icon = isAlert
    ? <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
    : isRec
    ? <Lightbulb className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
    : <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />

  const summary = trace.payload?.alert
    || trace.payload?.recommendation
    || trace.payload?.type
    || trace.payload?.summary
    || JSON.stringify(trace.payload).slice(0, 80)

  const zone = trace.location || trace.payload?.zone
  const ts = new Date(trace.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  return (
    <div className={`flex items-start gap-2.5 border rounded-lg px-3 py-2.5 text-sm ${colorClass}`}>
      {icon}
      <div className="flex-1 min-w-0">
        <span className="block truncate">{summary}</span>
        <div className="flex items-center gap-2 mt-0.5 text-xs opacity-60">
          <span className="font-mono uppercase">{trace.domain}</span>
          {zone && <span>· {zone}</span>}
          <span>· {ts}</span>
        </div>
      </div>
    </div>
  )
}

export default function AlertsPanel({ alerts, recommendations }) {
  const alertList = alerts?.alerts || []
  const recList = recommendations?.recommendations || []
  const all = [...alertList, ...recList].sort(
    (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
  )

  return (
    <div className="bg-earth-900/40 border border-earth-800/60 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-medium text-earth-100">Alerts & Recommendations</h2>
        <div className="flex items-center gap-2 text-xs font-mono">
          {alertList.length > 0 && (
            <span className="bg-red-900/40 text-red-400 border border-red-800/40 px-2 py-0.5 rounded">
              {alertList.length} alert{alertList.length !== 1 ? 's' : ''}
            </span>
          )}
          {recList.length > 0 && (
            <span className="bg-moss-600/20 text-moss-400 border border-moss-600/30 px-2 py-0.5 rounded">
              {recList.length} rec{recList.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {all.length === 0 ? (
        <p className="text-xs text-earth-600 font-mono text-center py-6">
          no active alerts — system nominal
        </p>
      ) : (
        <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
          {all.map(t => <TraceItem key={t.id} trace={t} />)}
        </div>
      )}
    </div>
  )
}
