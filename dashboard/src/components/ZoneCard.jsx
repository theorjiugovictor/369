import { Droplets, Thermometer, AlertTriangle } from 'lucide-react'

function Gauge({ value, low = 30, high = 75, unit = '%' }) {
  if (value == null) return <span className="text-earth-600 font-mono text-lg">—</span>

  let color = 'text-moss-400'
  if (value < low) color = 'text-amber-400'
  if (value < 20) color = 'text-red-400'
  if (value > high) color = 'text-sky-400'

  return (
    <span className={`font-mono text-xl font-semibold ${color}`}>
      {value.toFixed(1)}<span className="text-sm font-normal ml-0.5">{unit}</span>
    </span>
  )
}

function Bar({ value, min = 0, max = 100, low = 30, high = 75 }) {
  if (value == null) return null
  const pct = Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100))
  let barColor = 'bg-moss-500'
  if (value < low) barColor = 'bg-amber-500'
  if (value < 20) barColor = 'bg-red-500'
  if (value > high) barColor = 'bg-sky-500'

  return (
    <div className="h-1 bg-earth-800 rounded-full overflow-hidden mt-1">
      <div className={`h-full rounded-full transition-all duration-700 ${barColor}`} style={{ width: `${pct}%` }} />
    </div>
  )
}

export default function ZoneCard({ zone, sensorData }) {
  const readings = sensorData?.readings || []
  const byId = Object.fromEntries(readings.map(r => [r.sensor_id, r]))

  const hasSoilMoisture = zone.sensors.some(s => s.includes('moisture'))
  const hasSoilTemp = zone.sensors.some(s => s.includes('temp'))
  const isCompost = zone.id === 'compost-area'

  const moistureSensor = zone.sensors.find(s => s.includes('moisture'))
  const tempSensor = zone.sensors.find(s => s.includes('temp'))

  const moisture = byId[moistureSensor]?.value ?? null
  const temp = byId[tempSensor]?.value ?? null

  const hasAlert = moisture != null && moisture < 20

  return (
    <div className={`bg-earth-900/40 border rounded-xl p-5 transition-colors ${hasAlert ? 'border-red-800/60' : 'border-earth-800/60 hover:border-earth-700/60'}`}>
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">{zone.icon}</span>
            <span className="font-medium text-earth-100">{zone.label}</span>
            {hasAlert && <AlertTriangle className="w-3.5 h-3.5 text-red-400" />}
          </div>
          <div className="text-xs text-earth-500 mt-0.5">
            {zone.type}{zone.area ? ` · ${zone.area}` : ''}
          </div>
        </div>
        <span className="text-xs font-mono text-earth-600 bg-earth-800/60 px-2 py-0.5 rounded">
          {zone.id}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {hasSoilMoisture && (
          <div>
            <div className="flex items-center gap-1 text-xs text-earth-500 mb-1">
              <Droplets className="w-3 h-3" />
              {isCompost ? 'Moisture' : 'Soil Moisture'}
            </div>
            <Gauge value={moisture} unit="%" />
            <Bar value={moisture} />
          </div>
        )}
        {(hasSoilTemp || isCompost) && (
          <div>
            <div className="flex items-center gap-1 text-xs text-earth-500 mb-1">
              <Thermometer className="w-3 h-3" />
              {isCompost ? 'Compost Temp' : 'Soil Temp'}
            </div>
            <Gauge value={temp} unit="°C" low={10} high={35} />
            <Bar value={temp} min={0} max={80} low={10} high={35} />
          </div>
        )}
      </div>

      {readings.length === 0 && (
        <p className="text-xs text-earth-600 font-mono mt-3">awaiting readings…</p>
      )}
    </div>
  )
}
