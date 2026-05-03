const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8369'

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${path}`)
  return res.json()
}

export async function fetchHealth() {
  return get('/health')
}

export async function fetchAgents() {
  const { agents } = await get('/api/agents/')
  return agents
}

export async function fetchAgentState(agentId) {
  return get(`/api/agents/${agentId}/state`)
}

export async function fetchZoneSensors(zoneId) {
  return get(`/api/sensors/zone/${zoneId}`)
}

export async function fetchAlerts() {
  return get('/api/insights/alerts')
}

export async function fetchBriefing() {
  return get('/api/insights/briefing')
}

export async function fetchRecommendations(domain) {
  const q = domain ? `?domain=${domain}` : ''
  return get(`/api/insights/recommendations${q}`)
}

export async function fetchTraces(domain, limit = 30) {
  const q = domain ? `?domain=${domain}&limit=${limit}` : `?limit=${limit}`
  return get(`/api/traces/${q}`)
}

export async function fetchAllData() {
  const [health, alerts, briefing, recommendations, traces] = await Promise.allSettled([
    fetchHealth(),
    fetchAlerts(),
    fetchBriefing(),
    fetchRecommendations(),
    fetchTraces(null, 40),
  ])

  return {
    health: health.status === 'fulfilled' ? health.value : null,
    alerts: alerts.status === 'fulfilled' ? alerts.value : { alerts: [], count: 0 },
    briefing: briefing.status === 'fulfilled' ? briefing.value : null,
    recommendations: recommendations.status === 'fulfilled' ? recommendations.value : { recommendations: [] },
    traces: traces.status === 'fulfilled' ? traces.value : { traces: [] },
  }
}

export const ZONES = [
  { id: 'raised-beds',  label: 'Raised Beds',  type: 'Growing',  area: '120 sqft', icon: '🌱', sensors: ['soil-moisture-rb-1', 'soil-temp-rb-1'] },
  { id: 'fruit-trees',  label: 'Fruit Trees',  type: 'Orchard',  area: '400 sqft', icon: '🌳', sensors: ['soil-moisture-ft-1'] },
  { id: 'compost-area', label: 'Compost Area', type: 'Compost',  area: '',         icon: '♻️', sensors: ['compost-temp-1', 'compost-moisture-1'] },
  { id: 'lawn',         label: 'Lawn',         type: 'Lawn',     area: '600 sqft', icon: '🌿', sensors: ['soil-moisture-lawn-1'] },
]
