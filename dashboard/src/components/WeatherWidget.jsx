import { Cloud, Droplets, Wind, Thermometer } from 'lucide-react'

const WMO_LABELS = {
  0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
  45: 'Foggy', 48: 'Icy fog',
  51: 'Light drizzle', 53: 'Drizzle', 55: 'Heavy drizzle',
  61: 'Light rain', 63: 'Rain', 65: 'Heavy rain',
  71: 'Light snow', 73: 'Snow', 75: 'Heavy snow',
  80: 'Light showers', 81: 'Showers', 82: 'Heavy showers',
  95: 'Thunderstorm',
}

function Stat({ icon, label, value }) {
  return (
    <div className="flex items-center gap-2">
      <div className="text-earth-500">{icon}</div>
      <div>
        <div className="text-xs text-earth-500">{label}</div>
        <div className="text-sm font-mono text-earth-200">{value ?? '—'}</div>
      </div>
    </div>
  )
}

export default function WeatherWidget({ traces }) {
  const weatherTraces = (traces?.traces || []).filter(t => t.domain === 'weather')

  const current = weatherTraces.find(t => t.payload?.type === 'current_weather')?.payload
  const forecasts = weatherTraces
    .filter(t => t.payload?.type === 'daily_forecast')
    .sort((a, b) => new Date(a.payload.date) - new Date(b.payload.date))
    .slice(0, 3)

  return (
    <div className="bg-earth-900/40 border border-earth-800/60 rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Cloud className="w-4 h-4 text-sky-400" />
        <h2 className="font-medium text-earth-100">Weather</h2>
      </div>

      {current ? (
        <>
          <div className="flex items-end justify-between mb-4">
            <div>
              <div className="text-3xl font-mono font-semibold text-earth-100">
                {current.temperature_c?.toFixed(1)}<span className="text-base font-normal text-earth-400">°C</span>
              </div>
              <div className="text-xs text-earth-500 mt-0.5">
                {WMO_LABELS[current.weather_code] || 'Unknown'}
              </div>
            </div>
            <div className="text-4xl opacity-80">
              {current.weather_code <= 1 ? '☀️' : current.weather_code <= 3 ? '⛅' : current.weather_code <= 55 ? '🌧️' : current.weather_code <= 75 ? '❄️' : '⛈️'}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 mb-4">
            <Stat icon={<Droplets className="w-3.5 h-3.5" />} label="Humidity" value={`${current.humidity_pct}%`} />
            <Stat icon={<Droplets className="w-3.5 h-3.5" />} label="Precip" value={`${current.precipitation_mm}mm`} />
            <Stat icon={<Wind className="w-3.5 h-3.5" />} label="Wind" value={`${current.wind_speed_kmh}km/h`} />
          </div>
        </>
      ) : (
        <p className="text-xs text-earth-600 font-mono mb-4">awaiting weather data…</p>
      )}

      {forecasts.length > 0 && (
        <div className="border-t border-earth-800/60 pt-4">
          <div className="text-xs text-earth-500 mb-3">3-Day Forecast</div>
          <div className="space-y-2">
            {forecasts.map((f, i) => {
              const p = f.payload
              const date = new Date(p.date).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })
              return (
                <div key={i} className="flex items-center justify-between text-sm">
                  <span className="text-earth-400 w-28">{date}</span>
                  <span className="text-earth-300 font-mono">
                    {p.temp_min_c?.toFixed(0)}° / {p.temp_max_c?.toFixed(0)}°
                  </span>
                  <span className="text-sky-400 font-mono text-xs">
                    {p.precipitation_mm?.toFixed(1)}mm {p.precipitation_probability_pct ? `(${p.precipitation_probability_pct}%)` : ''}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
