'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import useSWR from 'swr'
import { api } from '@/lib/api'
import { Battery, Zap, DollarSign, Plus, X, TrendingDown } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts'

export default function OptimizationPage() {
  const router = useRouter()
  const [selectedOptimizationId, setSelectedOptimizationId] = useState<string | null>(null)
  
  // Fetch saved optimizations from database
  const { data: optimizationsData, isLoading } = useSWR('/api/optimize/optimizations', async () => {
    try {
      const response = await fetch('/api/optimize/optimizations?limit=20')
      if (!response.ok) {
        throw new Error('Failed to fetch')
      }
      const data = await response.json()
      return data.optimizations || []
    } catch (e) {
      console.error('Failed to load optimizations:', e)
      return []
    }
  }, {
    revalidateOnFocus: false,
    refreshInterval: 10000 // Refresh every 10 seconds
  })
  
  const { data: types } = useSWR('/api/optimize/types', () => api.optimization.listTypes())

  if (isLoading) {
    return <div className="flex items-center justify-center min-h-screen">
      <div className="text-gray-600">Loading...</div>
    </div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Optimization</h1>
          <p className="text-gray-600 mt-2">Battery dispatch and asset optimization</p>
        </div>
        <button 
          onClick={() => router.push('/optimization/new')}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          New Optimization
        </button>
      </div>

      {/* Optimization Types */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {types?.map((type: any) => (
          <TypeCard key={type.name} type={type} />
        ))}
      </div>

      {/* Recent Optimizations */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Recent Optimizations</h2>
        {!optimizationsData || optimizationsData.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <TrendingDown className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No optimizations yet. Create your first optimization to get started!</p>
          </div>
        ) : (
          <div className="space-y-4">
            {optimizationsData.map((opt: any) => (
              <OptimizationCard 
                key={opt.optimization_id} 
                optimization={opt}
                onClick={() => setSelectedOptimizationId(opt.optimization_id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Optimization Detail Modal */}
      {selectedOptimizationId && (
        <OptimizationDetailModal
          optimizationId={selectedOptimizationId}
          onClose={() => setSelectedOptimizationId(null)}
        />
      )}
    </div>
  )
}

function TypeCard({ type }: { type: any }) {
  return (
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200 hover:border-primary-300 transition-colors">
      <h3 className="font-semibold text-lg mb-2">{type.name}</h3>
      <p className="text-sm text-gray-600 mb-3">{type.description}</p>
      {type.requires && (
        <div className="flex flex-wrap gap-1">
          {type.requires.map((req: string) => (
            <span key={req} className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
              {req}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function OptimizationCard({ optimization, onClick }: { optimization: any; onClick?: () => void }) {
  const statusColors = {
    pending: 'bg-gray-100 text-gray-800',
    running: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  }

  return (
    <div 
      className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 hover:shadow-md transition-all cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold capitalize">{optimization.optimization_type.replace('_', ' ')}</h3>
          <p className="text-sm text-gray-600">ID: {optimization.optimization_id.slice(0, 8)}...</p>
        </div>
        <span className={`px-2 py-1 text-xs rounded ${statusColors[optimization.status as keyof typeof statusColors]}`}>
          {optimization.status}
        </span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        {optimization.total_cost !== null && (
          <div>
            <div className="text-gray-600">Total Cost</div>
            <div className="font-semibold">${optimization.total_cost.toFixed(2)}</div>
          </div>
        )}
        {optimization.solver && (
          <div>
            <div className="text-gray-600">Solver</div>
            <div className="font-semibold">{optimization.solver}</div>
          </div>
        )}
        {optimization.solve_time_seconds && (
          <div>
            <div className="text-gray-600">Solve Time</div>
            <div className="font-semibold">{optimization.solve_time_seconds.toFixed(2)}s</div>
          </div>
        )}
        {optimization.result_count > 0 && (
          <div>
            <div className="text-gray-600">Schedule Points</div>
            <div className="font-semibold">{optimization.result_count}</div>
          </div>
        )}
      </div>
    </div>
  )
}

function OptimizationDetailModal({ optimizationId, onClose }: { optimizationId: string; onClose: () => void }) {
  const { data: optimization, isLoading } = useSWR(
    optimizationId ? `/api/optimize/optimizations/${optimizationId}` : null,
    async () => {
      const response = await fetch(`/api/optimize/optimizations/${optimizationId}`)
      if (!response.ok) throw new Error('Failed to fetch')
      return response.json()
    }
  )

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl p-6 max-w-6xl w-full mx-4">
          <div className="text-center py-8">Loading optimization details...</div>
        </div>
      </div>
    )
  }

  if (!optimization || !optimization.results) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl p-6 max-w-4xl w-full mx-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold">Optimization Not Found</h2>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded">
              <X className="h-5 w-5" />
            </button>
          </div>
          <p>No optimization data available.</p>
        </div>
      </div>
    )
  }

  // Prepare schedule chart data
  const scheduleData = optimization.results.map((point: any) => ({
    time: new Date(point.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
    soc: point.battery_soc,
    charge: point.battery_charge,
    discharge: point.battery_discharge,
    gridImport: point.grid_import,
    gridExport: point.grid_export
  }))

  // Prepare cost breakdown
  const costData = Object.entries(optimization.costs || {}).map(([type, amount]) => ({
    type: type.charAt(0).toUpperCase() + type.slice(1),
    amount: amount as number
  }))

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-7xl w-full my-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold capitalize">
              {optimization.optimization_type.replace('_', ' ')} Optimization
            </h2>
            <p className="text-gray-600">ID: {optimization.optimization_id}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Metadata */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm text-gray-600">Status</div>
            <div className="font-semibold">{optimization.status}</div>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm text-gray-600">Solver</div>
            <div className="font-semibold">{optimization.solver}</div>
          </div>
          <div className="bg-green-50 p-3 rounded">
            <div className="text-sm text-gray-600">Total Cost</div>
            <div className="font-semibold text-lg text-green-700">${optimization.total_cost?.toFixed(2)}</div>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm text-gray-600">Solve Time</div>
            <div className="font-semibold">{optimization.solve_time_seconds?.toFixed(2)}s</div>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm text-gray-600">Schedule Points</div>
            <div className="font-semibold">{optimization.results.length}</div>
          </div>
        </div>

        {/* Cost Breakdown */}
        {costData.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
            <h3 className="font-semibold mb-4">Cost Breakdown</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={costData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="type" fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip formatter={(value: number) => `$${value.toFixed(2)}`} />
                <Bar dataKey="amount" fill="#2563eb" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Battery Schedule */}
        <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
          <h3 className="font-semibold mb-4">Battery Schedule</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={scheduleData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" fontSize={12} angle={-45} textAnchor="end" height={80} />
              <YAxis fontSize={12} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="soc" stroke="#10b981" name="SOC (%)" strokeWidth={2} />
              <Line type="monotone" dataKey="charge" stroke="#3b82f6" name="Charge (kW)" strokeWidth={1.5} />
              <Line type="monotone" dataKey="discharge" stroke="#ef4444" name="Discharge (kW)" strokeWidth={1.5} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Grid Schedule */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="font-semibold mb-4">Grid Schedule</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={scheduleData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" fontSize={12} angle={-45} textAnchor="end" height={80} />
              <YAxis fontSize={12} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="gridImport" stroke="#f59e0b" name="Import (kW)" strokeWidth={2} />
              <Line type="monotone" dataKey="gridExport" stroke="#8b5cf6" name="Export (kW)" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
