'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import useSWR from 'swr'
import { api } from '@/lib/api'
import { assetService, BatteryAsset } from '@/services/assetService'
import { ArrowLeft, Loader2, Download, CheckCircle, XCircle, Clock, Battery } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

export default function NewOptimizationPage() {
  const router = useRouter()
  const { data: types, isLoading: typesLoading } = useSWR('/api/optimize/types', () => api.optimization.listTypes())
  
  const [selectedType, setSelectedType] = useState('')
  const [timeHorizon, setTimeHorizon] = useState('24')
  const [interval, setInterval] = useState('1H')
  const [objectiveFunction, setObjectiveFunction] = useState('minimize_cost')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [optimizationJob, setOptimizationJob] = useState<any>(null)
  const [optimizationResult, setOptimizationResult] = useState<any>(null)
  
  // Asset selection states
  const [batteries, setBatteries] = useState<BatteryAsset[]>([])
  const [selectedBatteryId, setSelectedBatteryId] = useState<string>('')
  const [loadingAssets, setLoadingAssets] = useState(false)
  const [assetsError, setAssetsError] = useState('')

  // Load batteries when optimization type requires them
  useEffect(() => {
    const loadBatteries = async () => {
      if (!selectedType) return
      
      const batteryOptTypes = ['battery_dispatch', 'self_consumption', 'peak_shaving']
      if (!batteryOptTypes.includes(selectedType)) {
        setBatteries([])
        setSelectedBatteryId('')
        return
      }

      setLoadingAssets(true)
      setAssetsError('')
      try {
        const data = await assetService.listBatteries({ status: 'active', limit: 100 })
        setBatteries(data.items)
        // Auto-select first battery if available
        if (data.items.length > 0 && !selectedBatteryId) {
          setSelectedBatteryId(data.items[0].asset_id)
        }
      } catch (err) {
        setAssetsError(err instanceof Error ? err.message : 'Failed to load batteries')
      } finally {
        setLoadingAssets(false)
      }
    }

    loadBatteries()
  }, [selectedType])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    
    if (!selectedType) {
      setError('Please select an optimization type')
      return
    }

    setIsSubmitting(true)
    try {
      // Build a proper optimization request
      const now = new Date()
      const startTime = new Date(now.getTime())
      const endTime = new Date(now.getTime() + parseInt(timeHorizon) * 60 * 60 * 1000)
      
      // Convert interval to minutes
      const intervalMinutes: Record<string, number> = {
        '15min': 15,
        '30min': 30,
        '1H': 60,
        '1D': 1440,
      }
      
      // Create assets based on optimization type
      const assets: any[] = []
      
      // Battery-based optimizations - use real battery if selected
      if (['battery_dispatch', 'self_consumption', 'peak_shaving'].includes(selectedType)) {
        if (selectedBatteryId) {
          // Use real battery from asset service
          const selectedBattery = batteries.find(b => b.asset_id === selectedBatteryId)
          if (selectedBattery) {
            assets.push({
              asset_id: selectedBattery.asset_id,
              asset_type: 'battery',
              name: selectedBattery.name,
              battery: {
                capacity_kwh: selectedBattery.battery.capacity_kwh,
                max_charge_kw: selectedBattery.battery.max_charge_kw,
                max_discharge_kw: selectedBattery.battery.max_discharge_kw,
                efficiency: selectedBattery.battery.round_trip_efficiency,
                initial_soc: selectedBattery.battery.initial_soc / 100, // Convert percent to decimal
                min_soc: selectedBattery.battery.min_soc / 100, // Convert percent to decimal
                max_soc: selectedBattery.battery.max_soc / 100, // Convert percent to decimal
                degradation_cost_per_kwh: selectedBattery.battery.degradation_cost_per_kwh || 0.01
              }
            })
          }
        } else {
          // Fallback to demo battery if no real battery selected
          assets.push({
            asset_id: 'battery-demo-001',
            asset_type: 'battery',
            name: 'Demo Battery',
            battery: {
              capacity_kwh: 100,
              max_charge_kw: 50,
              max_discharge_kw: 50,
              efficiency: 0.95,
              initial_soc: 0.5,
              min_soc: 0.1,
              max_soc: 0.9,
              degradation_cost_per_kwh: 0.01
            }
          })
        }
      }
      
      // Unit commitment needs generators
      if (selectedType === 'unit_commitment') {
        assets.push({
          asset_id: 'gen-demo-001',
          asset_type: 'generator',
          name: 'Demo Generator',
          generator: {
            capacity_kw: 100,
            min_output_kw: 20,
            fuel_cost_per_kwh: 0.08,
            startup_cost: 50,
            shutdown_cost: 10,
            min_uptime_hours: 1,
            min_downtime_hours: 1,
            emissions_kg_co2_per_kwh: 0.5
          }
        })
      }
      
      // Grid connection for procurement and other types
      if (['procurement', 'self_consumption'].includes(selectedType) || assets.length === 0) {
        assets.push({
          asset_id: 'grid-demo-001',
          asset_type: 'grid_connection',
          name: 'Grid Connection',
          grid: {
            max_import_kw: 200,
            max_export_kw: 100,
            import_enabled: true,
            export_enabled: true
          }
        })
      }
      
      // Generate sample price and load data
      const numSteps = Math.ceil((endTime.getTime() - startTime.getTime()) / (intervalMinutes[interval] * 60 * 1000))
      const timestamps = Array.from({ length: numSteps }, (_, i) => 
        new Date(startTime.getTime() + i * intervalMinutes[interval] * 60 * 1000).toISOString()
      )
      
      // Simple price pattern (higher during day, lower at night)
      const prices = timestamps.map((ts, i) => {
        const hour = new Date(ts).getHours()
        return hour >= 8 && hour <= 20 ? 0.15 : 0.08 // Peak vs off-peak
      })
      
      // Simple load pattern (higher during day)
      const loads = timestamps.map((ts) => {
        const hour = new Date(ts).getHours()
        return 30 + (hour >= 8 && hour <= 20 ? 40 : 0) + Math.random() * 10
      })
      
      const request = {
        optimization_type: selectedType,
        objective: objectiveFunction.toLowerCase().replace(/_/g, '_'),
        start_time: startTime.toISOString(),
        end_time: endTime.toISOString(),
        time_step_minutes: intervalMinutes[interval] || 60,
        assets: assets,
        import_prices: {
          timestamps: timestamps,
          values: prices
        },
        load_forecast: {
          timestamps: timestamps,
          values: loads
        }
      }
      
      const result = await api.optimization.createOptimization(request)
      
      // Store job info and start polling
      setOptimizationJob(result)
      setIsSubmitting(false)
    } catch (err: any) {
      console.error('Optimization creation error:', err)
      const errorDetail = err.response?.data?.detail
      if (Array.isArray(errorDetail)) {
        // Validation errors from FastAPI
        const errors = errorDetail.map((e: any) => `${e.loc.join('.')}: ${e.msg}`).join(', ')
        setError(`Validation error: ${errors}`)
      } else {
        setError(errorDetail || 'Failed to create optimization. Please try again.')
      }
      setIsSubmitting(false)
    }
  }

  // Poll for optimization results
  useEffect(() => {
    if (!optimizationJob || optimizationResult) return

    let cancelled = false
    
    const poll = async () => {
      if (cancelled) return
      
      try {
        const result = await api.optimization.getOptimization(optimizationJob.optimization_id)
        
        if (!cancelled && (result.status === 'completed' || result.status === 'failed')) {
          setOptimizationResult(result)
          cancelled = true
        } else if (!cancelled) {
          setTimeout(poll, 2000)
        }
      } catch (err) {
        console.error('Error polling optimization:', err)
        if (!cancelled) {
          setTimeout(poll, 2000)
        }
      }
    }

    poll()

    return () => {
      cancelled = true
    }
  }, [optimizationJob, optimizationResult])

  if (typesLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.back()}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Create New Optimization</h1>
          <p className="text-gray-600 mt-1">Configure and run an optimization scenario</p>
        </div>
      </div>

      {/* Form */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          {/* Optimization Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Optimization Type *
            </label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              required
            >
              <option value="">Select an optimization type...</option>
              {types?.map((type: any) => (
                <option key={type.name} value={type.name}>
                  {type.name} - {type.description}
                </option>
              ))}
            </select>
            <p className="mt-1 text-sm text-gray-500">
              Choose the type of optimization to perform
            </p>
          </div>

          {/* Battery Asset Selection */}
          {selectedType && ['battery_dispatch', 'self_consumption', 'peak_shaving'].includes(selectedType) && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Battery Asset
              </label>
              {loadingAssets ? (
                <div className="flex items-center gap-2 px-4 py-3 border border-gray-300 rounded-lg bg-gray-50">
                  <Loader2 className="h-4 w-4 animate-spin text-gray-500" />
                  <span className="text-sm text-gray-600">Loading batteries...</span>
                </div>
              ) : assetsError ? (
                <div className="px-4 py-3 border border-red-300 rounded-lg bg-red-50 text-red-800 text-sm">
                  {assetsError}
                </div>
              ) : batteries.length === 0 ? (
                <div className="px-4 py-3 border border-yellow-300 rounded-lg bg-yellow-50">
                  <div className="flex items-center gap-2 text-yellow-800 mb-2">
                    <Battery className="h-4 w-4" />
                    <span className="text-sm font-medium">No batteries found</span>
                  </div>
                  <p className="text-sm text-yellow-700 mb-2">
                    You don't have any active battery assets configured. A demo battery will be used for this optimization.
                  </p>
                  <button
                    type="button"
                    onClick={() => router.push('/assets/batteries/new')}
                    className="text-sm text-yellow-900 underline hover:text-yellow-950"
                  >
                    Add a battery asset →
                  </button>
                </div>
              ) : (
                <>
                  <select
                    value={selectedBatteryId}
                    onChange={(e) => setSelectedBatteryId(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    {batteries.map((battery) => (
                      <option key={battery.asset_id} value={battery.asset_id}>
                        {battery.name} - {battery.battery.capacity_kwh} kWh ({battery.battery.max_charge_kw}/{battery.battery.max_discharge_kw} kW)
                      </option>
                    ))}
                  </select>
                  {selectedBatteryId && (() => {
                    const battery = batteries.find(b => b.asset_id === selectedBatteryId)
                    return battery ? (
                      <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <Battery className="h-4 w-4 text-blue-600" />
                          <span className="text-sm font-medium text-blue-900">Selected Battery Details</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-sm text-blue-800">
                          <div>Capacity: <strong>{battery.battery.capacity_kwh} kWh</strong></div>
                          <div>Chemistry: <strong>{battery.battery.chemistry || 'N/A'}</strong></div>
                          <div>Max Charge: <strong>{battery.battery.max_charge_kw} kW</strong></div>
                          <div>Max Discharge: <strong>{battery.battery.max_discharge_kw} kW</strong></div>
                          <div>Efficiency: <strong>{(battery.battery.round_trip_efficiency * 100).toFixed(1)}%</strong></div>
                          <div>SOC Range: <strong>{battery.battery.min_soc}-{battery.battery.max_soc}%</strong></div>
                        </div>
                      </div>
                    ) : null
                  })()}
                  <p className="mt-1 text-sm text-gray-500">
                    Select the battery asset to use for this optimization
                  </p>
                </>
              )}
            </div>
          )}

          {/* Time Horizon */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Time Horizon
            </label>
            <div className="flex gap-4">
              <input
                type="number"
                value={timeHorizon}
                onChange={(e) => setTimeHorizon(e.target.value)}
                min="1"
                max="168"
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
              <select
                value={interval}
                onChange={(e) => setInterval(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="15min">15 minutes</option>
                <option value="30min">30 minutes</option>
                <option value="1H">1 hour</option>
                <option value="1D">1 day</option>
              </select>
            </div>
            <p className="mt-1 text-sm text-gray-500">
              Optimization time window and resolution
            </p>
          </div>

          {/* Objective Function */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Objective Function
            </label>
            <select
              value={objectiveFunction}
              onChange={(e) => setObjectiveFunction(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="minimize_cost">Minimize Cost</option>
              <option value="maximize_revenue">Maximize Revenue</option>
              <option value="maximize_self_consumption">Maximize Self-Consumption</option>
              <option value="minimize_peak_demand">Minimize Peak Demand</option>
            </select>
            <p className="mt-1 text-sm text-gray-500">
              What should the optimization prioritize?
            </p>
          </div>

          {/* Type Info */}
          {selectedType && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-semibold text-blue-900 mb-2">Optimization Information</h3>
              {(() => {
                const type = types?.find((t: any) => t.name === selectedType)
                return (
                  <div className="space-y-1 text-sm text-blue-800">
                    <p><strong>Description:</strong> {type?.description}</p>
                    {type?.requires && (
                      <div>
                        <strong>Requires:</strong>
                        <ul className="list-disc list-inside ml-2">
                          {type.requires.map((req: string, i: number) => (
                            <li key={i}>{req}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )
              })()}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={() => router.back()}
              className="flex-1 px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !selectedType}
              className="flex-1 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Optimization'
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Optimization Job Status */}
      {optimizationJob && !optimizationResult && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            <div>
              <h2 className="text-xl font-bold text-gray-900">Optimization Running...</h2>
              <p className="text-gray-600 mt-1">
                Job ID: {optimizationJob.optimization_id}
              </p>
              <p className="text-sm text-gray-500 mt-1">
                This may take a few moments. Results will appear automatically when complete.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Optimization Results */}
      {optimizationResult && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              {optimizationResult.status === 'completed' ? (
                <CheckCircle className="h-8 w-8 text-green-600" />
              ) : (
                <XCircle className="h-8 w-8 text-red-600" />
              )}
              <div>
                <h2 className="text-2xl font-bold text-gray-900">
                  {optimizationResult.status === 'completed' ? 'Optimization Completed' : 'Optimization Failed'}
                </h2>
                <p className="text-sm text-gray-500">Job ID: {optimizationResult.optimization_id}</p>
              </div>
            </div>
          </div>

          {optimizationResult.status === 'completed' ? (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="text-sm text-green-600 font-medium">Objective Value</div>
                  <div className="text-2xl font-bold text-green-900 mt-1">
                    {optimizationResult.objective_value?.toFixed(2) || 'N/A'}
                  </div>
                </div>
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="text-sm text-blue-600 font-medium">Total Cost</div>
                  <div className="text-2xl font-bold text-blue-900 mt-1">
                    ${optimizationResult.total_cost?.toFixed(2) || 'N/A'}
                  </div>
                </div>
                <div className="bg-purple-50 rounded-lg p-4">
                  <div className="text-sm text-purple-600 font-medium">Solve Time</div>
                  <div className="text-2xl font-bold text-purple-900 mt-1">
                    {optimizationResult.solver_info?.solve_time_seconds?.toFixed(2)}s
                  </div>
                </div>
                <div className="bg-orange-50 rounded-lg p-4">
                  <div className="text-sm text-orange-600 font-medium">Status</div>
                  <div className="text-2xl font-bold text-orange-900 mt-1">
                    {optimizationResult.solver_info?.status || 'Unknown'}
                  </div>
                </div>
              </div>

              {/* Cost Breakdown */}
              {(optimizationResult.energy_cost || optimizationResult.grid_cost) && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-3">Cost Breakdown</h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {optimizationResult.energy_cost && (
                      <div className="bg-gray-50 rounded p-3">
                        <div className="text-sm text-gray-600">Energy Cost</div>
                        <div className="text-lg font-bold text-gray-900">${optimizationResult.energy_cost.toFixed(2)}</div>
                      </div>
                    )}
                    {optimizationResult.grid_cost && (
                      <div className="bg-gray-50 rounded p-3">
                        <div className="text-sm text-gray-600">Grid Cost</div>
                        <div className="text-lg font-bold text-gray-900">${optimizationResult.grid_cost.toFixed(2)}</div>
                      </div>
                    )}
                    {optimizationResult.fuel_cost && (
                      <div className="bg-gray-50 rounded p-3">
                        <div className="text-sm text-gray-600">Fuel Cost</div>
                        <div className="text-lg font-bold text-gray-900">${optimizationResult.fuel_cost.toFixed(2)}</div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Schedule Chart */}
              {optimizationResult.schedule && optimizationResult.schedule.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-4">Optimization Schedule</h3>
                  <div className="h-96">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={optimizationResult.schedule}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          dataKey="timestamp" 
                          tickFormatter={(ts) => new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          tick={{ fontSize: 12 }}
                          angle={-45}
                          textAnchor="end"
                          height={80}
                        />
                        <YAxis tick={{ fontSize: 12 }} />
                        <Tooltip 
                          labelFormatter={(ts) => new Date(ts).toLocaleString()}
                        />
                        <Legend />
                        {optimizationResult.schedule[0]?.battery_soc !== undefined && (
                          <Line type="monotone" dataKey="battery_soc" stroke="#10b981" name="Battery SOC" strokeWidth={2} />
                        )}
                        {optimizationResult.schedule[0]?.battery_charge_kw !== undefined && (
                          <Line type="monotone" dataKey="battery_charge_kw" stroke="#3b82f6" name="Charge (kW)" strokeWidth={2} />
                        )}
                        {optimizationResult.schedule[0]?.battery_discharge_kw !== undefined && (
                          <Line type="monotone" dataKey="battery_discharge_kw" stroke="#f59e0b" name="Discharge (kW)" strokeWidth={2} />
                        )}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Schedule Table */}
              {optimizationResult.schedule && optimizationResult.schedule.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-4">Schedule Details</h3>
                  <div className="overflow-x-auto max-h-96 overflow-y-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50 sticky top-0">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                          {optimizationResult.schedule[0]?.battery_soc !== undefined && (
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">SOC</th>
                          )}
                          {optimizationResult.schedule[0]?.battery_charge_kw !== undefined && (
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Charge (kW)</th>
                          )}
                          {optimizationResult.schedule[0]?.battery_discharge_kw !== undefined && (
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Discharge (kW)</th>
                          )}
                          {optimizationResult.schedule[0]?.cost !== undefined && (
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cost ($)</th>
                          )}
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {optimizationResult.schedule.map((point: any, idx: number) => (
                          <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                              {new Date(point.timestamp).toLocaleString()}
                            </td>
                            {point.battery_soc != null && (
                              <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                                {(point.battery_soc * 100).toFixed(1)}%
                              </td>
                            )}
                            {point.battery_charge_kw != null && (
                              <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                                {point.battery_charge_kw.toFixed(2)}
                              </td>
                            )}
                            {point.battery_discharge_kw != null && (
                              <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                                {point.battery_discharge_kw.toFixed(2)}
                              </td>
                            )}
                            {point.cost != null && (
                              <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                                ${point.cost.toFixed(2)}
                              </td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          ) : (
            /* Error Display */
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-red-900 mb-2">Error Details</h3>
              <p className="text-red-800">{optimizationResult.error || 'Unknown error occurred'}</p>
            </div>
          )}

          {/* Actions */}
          <div className="mt-6 flex gap-3">
            <button
              onClick={() => {
                setOptimizationJob(null)
                setOptimizationResult(null)
                setError('')
              }}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
            >
              Create Another Optimization
            </button>
            <button
              onClick={() => router.push('/optimization')}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Back to Optimizations
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
