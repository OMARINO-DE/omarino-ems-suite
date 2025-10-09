'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { api } from '@/lib/api'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Zap, TrendingDown, Clock, Plus, X } from 'lucide-react'

interface OptimizationClientProps {
  initialOptimizations: any[]
  initialTypes: any[]
}

export function OptimizationClient({ initialOptimizations, initialTypes }: OptimizationClientProps) {
  const router = useRouter()
  // Use server-side rendered data, with manual refresh capability
  const [optimizations, setOptimizations] = useState(initialOptimizations)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [selectedOptimizationId, setSelectedOptimizationId] = useState<string | null>(null)

  const handleRefresh = () => {
    setIsRefreshing(true)
    // Use Next.js router refresh to trigger server-side re-fetch
    router.refresh()
    // The page will re-render with new SSR data
    setTimeout(() => setIsRefreshing(false), 1000)
  }

  // Update local state when props change (after router.refresh())
  useEffect(() => {
    setOptimizations(initialOptimizations)
  }, [initialOptimizations])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Optimization</h1>
          <p className="text-gray-600 mt-2">Energy cost optimization and scheduling</p>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50"
            title="Refresh data"
          >
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </button>
          <button 
            onClick={() => router.push('/optimization/new')}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            New Optimization
          </button>
        </div>
      </div>

      {/* Available Optimization Types */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Available Optimization Types</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {initialTypes?.map((type: any) => (
            <TypeCard key={type.name} type={type} />
          ))}
        </div>
      </div>

      {/* Recent Optimizations */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Recent Optimizations</h2>
        {!optimizations || optimizations.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Zap className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No optimizations yet. Create your first optimization to get started!</p>
          </div>
        ) : (
          <div className="space-y-4">
            {optimizations.map((optimization: any) => (
              <OptimizationCard 
                key={optimization.optimization_id} 
                optimization={optimization} 
                onClick={() => setSelectedOptimizationId(optimization.optimization_id)}
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
    <div className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors">
      <h3 className="font-semibold text-lg mb-2">{type.name}</h3>
      <p className="text-sm text-gray-600 mb-3">{type.description}</p>
      <div className="flex gap-2">
        <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">
          {type.algorithm}
        </span>
      </div>
    </div>
  )
}

function OptimizationCard({ optimization, onClick }: { optimization: any; onClick?: () => void }) {
  const costSavings = optimization.result?.cost_savings || 0
  const energySavings = optimization.result?.energy_savings || 0
  
  return (
    <div 
      className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 hover:shadow-md transition-all cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold">{optimization.type_name}</h3>
          <p className="text-sm text-gray-600">Asset: {optimization.asset_id}</p>
        </div>
        <span className={`px-2 py-1 text-xs rounded ${
          optimization.status === 'completed' ? 'bg-green-100 text-green-800' : 
          optimization.status === 'failed' ? 'bg-red-100 text-red-800' : 
          'bg-blue-100 text-blue-800'
        }`}>
          {optimization.status}
        </span>
      </div>
      <div className="flex gap-4 text-sm text-gray-600 mb-3">
        <div className="flex items-center gap-1">
          <Clock className="h-4 w-4" />
          <span>{new Date(optimization.created_at).toLocaleString()}</span>
        </div>
        {optimization.horizon && (
          <div className="flex items-center gap-1">
            <span>{optimization.horizon}h horizon</span>
          </div>
        )}
      </div>
      {optimization.status === 'completed' && (
        <div className="flex gap-4 text-sm">
          <div className="flex items-center gap-1 text-green-600">
            <TrendingDown className="h-4 w-4" />
            <span className="font-semibold">${costSavings.toFixed(2)} saved</span>
          </div>
          {energySavings > 0 && (
            <div className="flex items-center gap-1 text-blue-600">
              <Zap className="h-4 w-4" />
              <span className="font-semibold">{energySavings.toFixed(2)} kWh saved</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function OptimizationDetailModal({ optimizationId, onClose }: { optimizationId: string; onClose: () => void }) {
  const [optimization, setOptimization] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const fetchOptimization = async () => {
      try {
        setIsLoading(true)
        const data = await api.optimization.getOptimization(optimizationId)
        setOptimization(data)
      } catch (error) {
        console.error('Failed to load optimization details:', error)
        setOptimization(null)
      } finally {
        setIsLoading(false)
      }
    }
    
    if (optimizationId) {
      fetchOptimization()
    }
  }, [optimizationId])

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
          <div className="text-center py-8">Loading optimization details...</div>
        </div>
      </div>
    )
  }

  if (!optimization) {
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

  // The API returns the optimization data directly, not nested in a 'result' object
  const schedule = optimization.schedule || []
  const scheduleData = schedule.map((point: any) => ({
    timestamp: new Date(point.timestamp).toLocaleString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit' 
    }),
    power: point.battery_charge_kw || point.battery_discharge_kw || 0,
    soc: (point.battery_soc || 0) * 100 // Convert to percentage
  }))

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-6xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold">{optimization.optimization_type}</h2>
            <p className="text-gray-600">ID: {optimization.optimization_id}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Status and Info */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className={`p-3 rounded ${
            optimization.status === 'completed' ? 'bg-green-50' :
            optimization.status === 'failed' ? 'bg-red-50' :
            optimization.status === 'pending' ? 'bg-yellow-50' :
            'bg-gray-50'
          }`}>
            <div className="text-sm text-gray-600">Status</div>
            <div className="font-semibold capitalize">{optimization.status}</div>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm text-gray-600">Type</div>
            <div className="font-semibold text-sm">{optimization.optimization_type}</div>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm text-gray-600">Created</div>
            <div className="font-semibold text-sm">{new Date(optimization.created_at).toLocaleString()}</div>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm text-gray-600">Completed</div>
            <div className="font-semibold text-sm">
              {optimization.completed_at ? new Date(optimization.completed_at).toLocaleString() : 'N/A'}
            </div>
          </div>
        </div>

        {/* Error Display */}
        {optimization.error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <h3 className="font-semibold text-red-900 mb-2">Error</h3>
            <p className="text-red-800 text-sm">{optimization.error}</p>
          </div>
        )}

        {/* Cost Information */}
        {optimization.status === 'completed' && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {optimization.total_cost !== null && (
              <div className="bg-blue-50 p-4 rounded-lg">
                <h3 className="font-semibold mb-2 text-blue-800">Total Cost</h3>
                <div className="text-2xl font-bold text-blue-600">
                  ${optimization.total_cost.toFixed(2)}
                </div>
              </div>
            )}
            {optimization.energy_cost !== null && (
              <div className="bg-green-50 p-4 rounded-lg">
                <h3 className="font-semibold mb-2 text-green-800">Energy Cost</h3>
                <div className="text-2xl font-bold text-green-600">
                  ${optimization.energy_cost.toFixed(2)}
                </div>
              </div>
            )}
            {optimization.grid_cost !== null && (
              <div className="bg-purple-50 p-4 rounded-lg">
                <h3 className="font-semibold mb-2 text-purple-800">Grid Cost</h3>
                <div className="text-2xl font-bold text-purple-600">
                  ${optimization.grid_cost.toFixed(2)}
                </div>
              </div>
            )}
            {optimization.objective_value !== null && (
              <div className="bg-orange-50 p-4 rounded-lg">
                <h3 className="font-semibold mb-2 text-orange-800">Objective Value</h3>
                <div className="text-2xl font-bold text-orange-600">
                  {optimization.objective_value.toFixed(2)}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Solver Info */}
        {optimization.solver_info && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6">
            <h3 className="font-semibold mb-2">Solver Information</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
              {optimization.solver_info.status && (
                <div>
                  <span className="text-gray-600">Status:</span>{' '}
                  <span className="font-semibold">{optimization.solver_info.status}</span>
                </div>
              )}
              {optimization.solver_info.solve_time_seconds && (
                <div>
                  <span className="text-gray-600">Solve Time:</span>{' '}
                  <span className="font-semibold">{optimization.solver_info.solve_time_seconds.toFixed(2)}s</span>
                </div>
              )}
              {optimization.solver_info.solver_name && (
                <div>
                  <span className="text-gray-600">Solver:</span>{' '}
                  <span className="font-semibold">{optimization.solver_info.solver_name}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Schedule Chart */}
        {scheduleData.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h3 className="font-semibold mb-4">Optimized Schedule</h3>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={scheduleData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="timestamp" 
                  fontSize={12}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis yAxisId="left" fontSize={12} />
                <YAxis yAxisId="right" orientation="right" fontSize={12} />
                <Tooltip />
                <Legend />
                <Line 
                  yAxisId="left"
                  type="monotone" 
                  dataKey="power" 
                  stroke="#2563eb" 
                  strokeWidth={2}
                  name="Power (kW)"
                  dot={false}
                />
                <Line 
                  yAxisId="right"
                  type="monotone" 
                  dataKey="soc" 
                  stroke="#16a34a" 
                  strokeWidth={2}
                  name="SOC (%)"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  )
}
