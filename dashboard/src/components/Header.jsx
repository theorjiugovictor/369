import { Leaf, Wifi, WifiOff, RefreshCw } from 'lucide-react'

export default function Header({ health, lastUpdated, refreshing, onRefresh }) {
  const online = health?.status === 'healthy'
  const time = lastUpdated ? lastUpdated.toLocaleTimeString() : '—'

  return (
    <header className="border-b border-earth-800 bg-earth-900/60 backdrop-blur sticky top-0 z-10">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-moss-600/20 border border-moss-600/40 flex items-center justify-center">
            <Leaf className="w-4 h-4 text-moss-400" />
          </div>
          <div>
            <h1 className="text-base font-semibold tracking-wide text-earth-100">
              369 <span className="text-earth-400 font-normal">· Regenerative Intelligence</span>
            </h1>
            <p className="text-xs text-earth-500 font-mono">Marcus's Backyard · San Francisco</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-xs font-mono">
            {online ? (
              <Wifi className="w-3.5 h-3.5 text-moss-400" />
            ) : (
              <WifiOff className="w-3.5 h-3.5 text-red-400" />
            )}
            <span className={online ? 'text-moss-400' : 'text-red-400'}>
              {online ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>
          <span className="text-earth-600 text-xs font-mono">updated {time}</span>
          <button
            onClick={onRefresh}
            className="p-1.5 rounded hover:bg-earth-800 transition-colors"
            disabled={refreshing}
          >
            <RefreshCw className={`w-3.5 h-3.5 text-earth-400 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  )
}
