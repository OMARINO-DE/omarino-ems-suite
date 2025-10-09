'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Battery, Zap, Activity, AlertCircle, CheckCircle, Clock, RefreshCw, TrendingUp, TrendingDown } from 'lucide-react'
import { assetService, BatteryAsset, GeneratorAsset } from '@/services/assetService'

export default function AssetStatusPage() {
  const [batteries, setBatteries] = useState<BatteryAsset[]>([])
  const [generators, setGenerators] = useState<GeneratorAsset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const [autoRefresh, setAutoRefresh] = useState(true)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [batteriesData, generatorsData] = await Promise.all([
        assetService.listBatteries({ limit: 100 }),
        assetService.listGenerators({ limit: 100 }),
      ])
      setBatteries(batteriesData.items)
      setGenerators(generatorsData.items)
      setLastUpdate(new Date())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load asset status')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  // Auto-refresh every 30 seconds
  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      loadData()
    }, 30000)

    return () => clearInterval(interval)
  }, [autoRefresh])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-300' }
      case 'inactive':
        return { bg: 'bg-gray-100', text: 'text-gray-800', border: 'border-gray-300' }
      case 'maintenance':
        return { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-300' }
      case 'decommissioned':
        return { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-300' }
      default:
        return { bg: 'bg-gray-100', text: 'text-gray-800', border: 'border-gray-300' }
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-5 w-5 text-green-600" />
      case 'inactive':
        return <Clock className="h-5 w-5 text-gray-600" />
      case 'maintenance':
        return <AlertCircle className="h-5 w-5 text-yellow-600" />
      case 'decommissioned':
        return <AlertCircle className="h-5 w-5 text-red-600" />
      default:
        return <Activity className="h-5 w-5 text-gray-600" />
    }
  }

  const getHealthColor = (health?: number) => {
    if (health === undefined) return 'text-gray-500'
    if (health >= 90) return 'text-green-600'
    if (health >= 70) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getHealthIcon = (health?: number) => {
    if (health === undefined) return null
    if (health >= 90) return <TrendingUp className="h-4 w-4 text-green-600" />
    if (health >= 70) return <TrendingUp className="h-4 w-4 text-yellow-600" />
    return <TrendingDown className="h-4 w-4 text-red-600" />
  }

  const activeCount = [...batteries, ...generators].filter(a => a.status === 'active').length
  const maintenanceCount = [...batteries, ...generators].filter(a => a.status === 'maintenance').length
  const inactiveCount = [...batteries, ...generators].filter(a => a.status === 'inactive').length

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Link href="/assets" className="text-gray-600 hover:text-gray-900">
              Assets
            </Link>
            <span className="text-gray-400">/</span>
            <span className="text-gray-900 font-semibold">Status Dashboard</span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900">Asset Status Dashboard</h1>
          <p className="text-gray-600 mt-2">Real-time monitoring of asset health and operational status</p>
        </div>
        <div className="flex gap-3 items-center">
          <div className="text-sm text-gray-600">
            Last update: {lastUpdate.toLocaleTimeString()}
          </div>
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-2 text-sm rounded-lg border transition-colors ${
              autoRefresh 
                ? 'bg-primary-50 text-primary-700 border-primary-300' 
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
          </button>
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-red-600" />
          <div>
            <p className="text-red-800 font-medium">Error loading asset status</p>
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Assets</p>
              <p className="text-3xl font-bold text-gray-900">{batteries.length + generators.length}</p>
            </div>
            <Activity className="h-10 w-10 text-gray-400" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-green-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-green-600">Active</p>
              <p className="text-3xl font-bold text-green-900">{activeCount}</p>
            </div>
            <CheckCircle className="h-10 w-10 text-green-500" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-yellow-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-yellow-600">Maintenance</p>
              <p className="text-3xl font-bold text-yellow-900">{maintenanceCount}</p>
            </div>
            <AlertCircle className="h-10 w-10 text-yellow-500" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Inactive</p>
              <p className="text-3xl font-bold text-gray-900">{inactiveCount}</p>
            </div>
            <Clock className="h-10 w-10 text-gray-400" />
          </div>
        </div>
      </div>

      {/* Battery Status */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Battery className="h-6 w-6 text-blue-600" />
            Battery Status
          </h2>
          <span className="text-sm text-gray-600">{batteries.length} batteries</span>
        </div>

        {loading && batteries.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
            <RefreshCw className="h-8 w-8 animate-spin text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">Loading battery status...</p>
          </div>
        ) : batteries.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
            <Battery className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">No batteries configured</p>
            <Link
              href="/assets/batteries/new"
              className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Add Battery
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {batteries.map((battery) => {
              const statusStyle = getStatusColor(battery.status)
              return (
                <div
                  key={battery.asset_id}
                  className={`bg-white rounded-lg shadow-sm border ${statusStyle.border} p-6`}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className={`p-3 rounded-lg ${statusStyle.bg}`}>
                        <Battery className="h-6 w-6 text-blue-600" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900 text-lg">{battery.name}</h3>
                        {battery.manufacturer && (
                          <p className="text-sm text-gray-600">{battery.manufacturer} {battery.model}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(battery.status)}
                      <span className={`px-3 py-1 text-xs font-medium rounded-full ${statusStyle.bg} ${statusStyle.text}`}>
                        {battery.status}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-600 mb-1">Capacity</p>
                      <p className="text-lg font-bold text-gray-900">{battery.battery.capacity_kwh} kWh</p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-600 mb-1">Max Power</p>
                      <p className="text-lg font-bold text-gray-900">
                        {Math.min(battery.battery.max_charge_kw, battery.battery.max_discharge_kw)} kW
                      </p>
                    </div>
                  </div>

                  {/* SOC Indicator */}
                  {battery.battery.initial_soc !== undefined && (
                    <div className="mb-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm text-gray-600">State of Charge</span>
                        <span className="text-sm font-semibold text-gray-900">{battery.battery.initial_soc}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div
                          className={`h-3 rounded-full transition-all ${
                            battery.battery.initial_soc > 70 
                              ? 'bg-green-500' 
                              : battery.battery.initial_soc > 30 
                              ? 'bg-yellow-500' 
                              : 'bg-red-500'
                          }`}
                          style={{ width: `${battery.battery.initial_soc}%` }}
                        />
                      </div>
                      <div className="flex justify-between text-xs text-gray-500 mt-1">
                        <span>Min: {battery.battery.min_soc}%</span>
                        <span>Max: {battery.battery.max_soc}%</span>
                      </div>
                    </div>
                  )}

                  {/* Health Status */}
                  {battery.battery.current_health_percentage !== undefined && (
                    <div className="mb-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm text-gray-600 flex items-center gap-1">
                          Battery Health
                          {getHealthIcon(battery.battery.current_health_percentage)}
                        </span>
                        <span className={`text-sm font-semibold ${getHealthColor(battery.battery.current_health_percentage)}`}>
                          {battery.battery.current_health_percentage.toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all ${
                            battery.battery.current_health_percentage >= 90 
                              ? 'bg-green-500' 
                              : battery.battery.current_health_percentage >= 70 
                              ? 'bg-yellow-500' 
                              : 'bg-red-500'
                          }`}
                          style={{ width: `${battery.battery.current_health_percentage}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Additional Info */}
                  <div className="grid grid-cols-2 gap-3 text-sm border-t border-gray-100 pt-4">
                    <div>
                      <span className="text-gray-600">Efficiency:</span>
                      <span className="font-medium text-gray-900 ml-2">
                        {(battery.battery.round_trip_efficiency * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">Chemistry:</span>
                      <span className="font-medium text-gray-900 ml-2">
                        {battery.battery.chemistry || 'N/A'}
                      </span>
                    </div>
                    {battery.battery.current_cycle_count !== undefined && (
                      <div>
                        <span className="text-gray-600">Cycles:</span>
                        <span className="font-medium text-gray-900 ml-2">
                          {battery.battery.current_cycle_count}
                          {battery.battery.cycle_life && ` / ${battery.battery.cycle_life}`}
                        </span>
                      </div>
                    )}
                    {battery.installation_date && (
                      <div>
                        <span className="text-gray-600">Installed:</span>
                        <span className="font-medium text-gray-900 ml-2">
                          {new Date(battery.installation_date).toLocaleDateString()}
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="mt-4">
                    <Link
                      href={`/assets/batteries/${battery.asset_id}`}
                      className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                    >
                      View Details →
                    </Link>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Generator Status */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Zap className="h-6 w-6 text-amber-600" />
            Generator Status
          </h2>
          <span className="text-sm text-gray-600">{generators.length} generators</span>
        </div>

        {loading && generators.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
            <RefreshCw className="h-8 w-8 animate-spin text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">Loading generator status...</p>
          </div>
        ) : generators.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
            <Zap className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">No generators configured</p>
            <Link
              href="/assets/generators/new"
              className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Add Generator
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {generators.map((generator) => {
              const statusStyle = getStatusColor(generator.status)
              return (
                <div
                  key={generator.asset_id}
                  className={`bg-white rounded-lg shadow-sm border ${statusStyle.border} p-6`}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className={`p-3 rounded-lg ${statusStyle.bg}`}>
                        <Zap className="h-6 w-6 text-amber-600" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900 text-lg">{generator.name}</h3>
                        {generator.manufacturer && (
                          <p className="text-sm text-gray-600">{generator.manufacturer} {generator.model}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(generator.status)}
                      <span className={`px-3 py-1 text-xs font-medium rounded-full ${statusStyle.bg} ${statusStyle.text}`}>
                        {generator.status}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-600 mb-1">Rated Capacity</p>
                      <p className="text-lg font-bold text-gray-900">{generator.generator.rated_capacity_kw} kW</p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-600 mb-1">Output Range</p>
                      <p className="text-lg font-bold text-gray-900">
                        {generator.generator.min_output_kw || 0}-{generator.generator.max_output_kw} kW
                      </p>
                    </div>
                  </div>

                  {/* Operating Info */}
                  <div className="grid grid-cols-2 gap-3 text-sm border-t border-gray-100 pt-4 mb-4">
                    <div>
                      <span className="text-gray-600">Fuel Cost:</span>
                      <span className="font-medium text-gray-900 ml-2">
                        ${generator.generator.fuel_cost_per_kwh.toFixed(3)}/kWh
                      </span>
                    </div>
                    {generator.generator.generator_type && (
                      <div>
                        <span className="text-gray-600">Type:</span>
                        <span className="font-medium text-gray-900 ml-2 capitalize">
                          {generator.generator.generator_type.replace('_', ' ')}
                        </span>
                      </div>
                    )}
                    {generator.generator.co2_emissions_kg_per_kwh !== undefined && (
                      <div>
                        <span className="text-gray-600">CO₂:</span>
                        <span className="font-medium text-gray-900 ml-2">
                          {generator.generator.co2_emissions_kg_per_kwh.toFixed(3)} kg/kWh
                        </span>
                      </div>
                    )}
                    {generator.generator.operating_hours !== undefined && (
                      <div>
                        <span className="text-gray-600">Hours:</span>
                        <span className="font-medium text-gray-900 ml-2">
                          {generator.generator.operating_hours.toLocaleString()} h
                        </span>
                      </div>
                    )}
                    {generator.installation_date && (
                      <div>
                        <span className="text-gray-600">Installed:</span>
                        <span className="font-medium text-gray-900 ml-2">
                          {new Date(generator.installation_date).toLocaleDateString()}
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="mt-4">
                    <Link
                      href={`/assets/generators/${generator.asset_id}`}
                      className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                    >
                      View Details →
                    </Link>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
