import { Activity, Circle } from 'lucide-react'

const AGENT_META = {
  'soil-agent':       { icon: '🌱', label: 'Soil',       cycle: '5m' },
  'irrigation-agent': { icon: '💧', label: 'Irrigation', cycle: '10m' },
  'compost-agent':    { icon: '♻️', label: 'Compost',    cycle: '15m' },
  'weather-agent':    { icon: '☁️', label: 'Weather',    cycle: '30m' },
  'awareness-agent':  { icon: '🧠', label: 'Awareness',  cycle: '60m' },
}

function AgentRow({ agentId, state }) {
  const meta = AGENT_META[agentId] || { icon: '🤖', label: agentId, cycle: '?' }
  const status = state?.status || 'unknown'

  const statusColor = {
    active:  'text-moss-400',
    dormant: 'text-earth-500',
    error:   'text-red-400',
    unknown: 'text-earth-600',
  }[status] || 'text-earth-600'

  const heartbeat = state?.last_heartbeat
    ? new Date(state.last_heartbeat).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : null

  return (
    <div className="flex items-center justify-between py-2.5 border-b border-earth-800/40 last:border-0">
      <div className="flex items-center gap-2.5">
        <span className="text-lg">{meta.icon}</span>
        <div>
          <div className="text-sm text-earth-200">{meta.label}</div>
          <div className="text-xs text-earth-600 font-mono">cycle {meta.cycle}</div>
        </div>
      </div>
      <div className="flex items-center gap-3 text-xs font-mono">
        {heartbeat && <span className="text-earth-600">{heartbeat}</span>}
        <div className={`flex items-center gap-1 ${statusColor}`}>
          <Circle className="w-2 h-2 fill-current" />
          {status}
        </div>
      </div>
    </div>
  )
}

export default function AgentPanel({ agentIds, agentStates }) {
  const agents = agentIds?.length
    ? agentIds
    : Object.keys(AGENT_META)

  return (
    <div className="bg-earth-900/40 border border-earth-800/60 rounded-xl p-5">
      <div className="flex items-center gap-2 mb-3">
        <Activity className="w-4 h-4 text-moss-400" />
        <h2 className="font-medium text-earth-100">Agents</h2>
        <span className="ml-auto text-xs font-mono text-earth-600">{agents.length} registered</span>
      </div>

      <div>
        {agents.map(id => (
          <AgentRow key={id} agentId={id} state={agentStates?.[id]} />
        ))}
      </div>
    </div>
  )
}
