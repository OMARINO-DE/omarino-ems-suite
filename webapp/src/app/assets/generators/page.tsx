'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Zap, Plus, RefreshCw, Search, AlertCircle } from 'lucide-react'
import { assetService, GeneratorAsset } from '@/services/assetService'

export default function GeneratorsPage() {
  const router = useRouter()
  const [generators, setGenerators] = useState<GeneratorAsset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const loadGenerators = async () => {
    setLoading(true)
    setError(null)
    try {
      const params: any = { limit: 100 }
      if (searchTerm) params.search = searchTerm
      if (statusFilter !== 'all') params.status = statusFilter

      const data = await assetService.listGenerators(params)
      setGenerators(data.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load generators')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadGenerators()
  }, [statusFilter])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    loadGenerators()
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800'
      case 'inactive':
        return 'bg-gray-100 text-gray-800'
      case 'maintenance':
        return 'bg-yellow-100 text-yellow-800'
      case 'decommissioned':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getGeneratorTypeLabel = (type?: string) => {
    const labels: Record<string, string> = {
      diesel: 'Diesel',
      natural_gas: 'Natural Gas',
      propane: 'Propane',
      biogas: 'Biogas',
      gasoline: 'Gasoline',
      dual_fuel: 'Dual Fuel',
    }
    return type ? labels[type] || type : 'N/A'
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Link href="/assets" className="text-gray-600 hover:text-gray-900">
              Assets
            </Link>
            <span className="text-gray-400">/</span>
            <span className="text-gray-900 font-semibold">Generators</span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900">Generator Assets</h1>
          <p className="text-gray-600 mt-2">Manage and monitor backup generator systems</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={loadGenerators}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <Link
            href="/assets/generators/new"
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <Plus className="h-4 w-4" />
            Add Generator
          </Link>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-red-600" />
          <div>
            <p className="text-red-800 font-medium">Error loading generators</p>
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by name or serial..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Search
            </button>
          </form>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="all">All Statuses</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="maintenance">Maintenance</option>
              <option value="decommissioned">Decommissioned</option>
            </select>
          </div>
        </div>
      </div>

      {/* Generator List */}
      {loading ? (
        <div className="text-center py-12">
          <RefreshCw className="h-8 w-8 animate-spin text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600">Loading generators...</p>
        </div>
      ) : generators.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <Zap className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 mb-2">No generators found</p>
          {(searchTerm || statusFilter !== 'all') && (
            <p className="text-sm text-gray-500 mb-4">Try adjusting your filters</p>
          )}
          <Link
            href="/assets/generators/new"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <Plus className="h-4 w-4" />
            Add your first generator
          </Link>
        </div>
      ) : (
        <div>
          <div className="mb-4 text-sm text-gray-600">
            Showing {generators.length} {generators.length === 1 ? 'generator' : 'generators'}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {generators.map((generator) => (
              <div
                key={generator.asset_id}
                onClick={() => router.push(`/assets/generators/${generator.asset_id}`)}
                className="bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow cursor-pointer"
              >
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-amber-100 rounded-lg">
                        <Zap className="h-6 w-6 text-amber-600" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">{generator.name}</h3>
                        {generator.manufacturer && (
                          <p className="text-sm text-gray-600">{generator.manufacturer}</p>
                        )}
                      </div>
                    </div>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(generator.status)}`}>
                      {generator.status}
                    </span>
                  </div>

                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Rated Capacity:</span>
                      <span className="font-medium text-gray-900">{generator.generator.rated_capacity_kw} kW</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Max Output:</span>
                      <span className="font-medium text-gray-900">{generator.generator.max_output_kw} kW</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Min Output:</span>
                      <span className="font-medium text-gray-900">{generator.generator.min_output_kw} kW</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Fuel Cost:</span>
                      <span className="font-medium text-gray-900">
                        ${generator.generator.fuel_cost_per_kwh.toFixed(3)}/kWh
                      </span>
                    </div>
                    {generator.generator.generator_type && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">Type:</span>
                        <span className="font-medium text-gray-900">
                          {getGeneratorTypeLabel(generator.generator.generator_type)}
                        </span>
                      </div>
                    )}
                    {generator.generator.efficiency_at_rated_load !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">Efficiency:</span>
                        <span className="font-medium text-gray-900">
                          {(generator.generator.efficiency_at_rated_load * 100).toFixed(1)}%
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="mt-4 pt-4 border-t border-gray-100 space-y-1">
                    {generator.model && <p className="text-xs text-gray-500">Model: {generator.model}</p>}
                    {generator.serial_number && <p className="text-xs text-gray-500">S/N: {generator.serial_number}</p>}
                    {generator.installation_date && (
                      <p className="text-xs text-gray-500">
                        Installed: {new Date(generator.installation_date).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
