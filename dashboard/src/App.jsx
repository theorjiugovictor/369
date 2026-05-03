import { useState, useEffect, useCallback } from 'react'
import {
  fetchAllData, fetchAgents, fetchAgentState, fetchZoneSensors, ZONES,
} from './api'
import Header from './components/Header'
import ZoneCard from './components/ZoneCard'
import AlertsPanel from './components/AlertsPanel'
import WeatherWidget from './components/WeatherWidget'
import AgentPanel from './components/AgentPanel'
import BriefingCard from './components/BriefingCard'
import TracesFeed from './components/TracesFeed'

const REFRESH_MS = 30_000

export default function App() {
  const [data, setData] = useState(null)
  const [agentIds, setAgentIds] = useState([])
  const [agentStates, setAgentStates] = useState({})
  const [zoneSensors, setZoneSensors] = useState({})
  const [lastUpdated, setLastUpdated] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  const refresh = useCallback(async () => {
    setRefreshing(true)
    try {
      const [main, ids] = await Promise.all([fetchAllData(), fetchAgents().catch(() => [])])
      setData(main)
      setAgentIds(ids)

      // fetch agent states
      const states = {}
      await Promise.allSettled(
        ids.map(async id => {
          try { states[id] = await fetchAgentState(id) } catch {}
        })
      )
      setAgentStates(states)

      // fetch zone sensors
      const sensors = {}
      await Promise.allSettled(
        ZONES.map(async zone => {
          try { sensors[zone.id] = await fetchZoneSensors(zone.id) } catch {}
        })
      )
      setZoneSensors(sensors)

      setLastUpdated(new Date())
    } catch (err) {
      console.error('Refresh error:', err)
    } finally {
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, REFRESH_MS)
    return () => clearInterval(timer)
  }, [refresh])

  return (
    <div className="min-h-screen bg-[#0f0d0a] text-earth-200">
      <Header
        health={data?.health}
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      />

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">

        {/* Briefing */}
        <BriefingCard briefing={data?.briefing} />

        {/* Zones grid */}
        <section>
          <h2 className="text-xs font-mono text-earth-500 uppercase tracking-widest mb-3">Zones</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {ZONES.map(zone => (
              <ZoneCard key={zone.id} zone={zone} sensorData={zoneSensors[zone.id]} />
            ))}
          </div>
        </section>

        {/* Middle row: alerts + weather */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <AlertsPanel alerts={data?.alerts} recommendations={data?.recommendations} />
          <WeatherWidget traces={data?.traces} />
        </div>

        {/* Bottom row: agents + feed */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <AgentPanel agentIds={agentIds} agentStates={agentStates} />
          <TracesFeed traces={data?.traces} />
        </div>

      </main>

      <footer className="max-w-7xl mx-auto px-6 py-4 border-t border-earth-900 mt-4">
        <p className="text-xs text-earth-700 font-mono text-center">
          369 · stigmergic multi-agent OS for regenerative living · auto-refresh {REFRESH_MS / 1000}s
        </p>
      </footer>
    </div>
  )
}
