'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Battery, Zap, Plus, AlertCircle } from 'lucide-react'
import type { BatteryAsset, GeneratorAsset } from '@/lib/server-api'

interface AssetsClientProps {
  initialBatteries: BatteryAsset[]
  initialGenerators: GeneratorAsset[]
  initialError?: string | null
}

export function AssetsClient({
  initialBatteries,
  initialGenerators,
  initialError,
}: AssetsClientProps) {
  const [activeTab, setActiveTab] = useState<'batteries' | 'generators'>('batteries')
  const batteries = initialBatteries
  const generators = initialGenerators

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

  const getChemistryLabel = (chemistry?: string) => {
    const labels: Record<string, string> = {
      lithium_ion: 'Li-ion',
      lithium_iron_phosphate: 'LiFePO4',
      lead_acid: 'Lead Acid',
      nickel_metal_hydride: 'NiMH',
      sodium_sulfur: 'NaS',
      flow_battery: 'Flow Battery',
    }
    return chemistry ? labels[chemistry] || chemistry : 'N/A'
  }

  return (
    <>
      {initialError && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-red-600" />
          <div>
            <p className="text-red-800 font-medium">Error loading assets</p>
            <p className="text-red-600 text-sm">{initialError}</p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <div className="flex gap-4">
          <button
            onClick={() => setActiveTab('batteries')}
            className={`px-4 py-2 border-b-2 font-medium transition-colors ${
              activeTab === 'batteries'
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <Battery className="inline h-4 w-4 mr-2" />
            Batteries ({batteries.length})
          </button>
          <button
            onClick={() => setActiveTab('generators')}
            className={`px-4 py-2 border-b-2 font-medium transition-colors ${
              activeTab === 'generators'
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <Zap className="inline h-4 w-4 mr-2" />
            Generators ({generators.length})
          </button>
        </div>
      </div>

      {/* Batteries Tab */}
      {activeTab === 'batteries' && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Battery Assets</h2>
            <Link
              href="/assets/batteries/new"
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              <Plus className="h-4 w-4" />
              Add Battery
            </Link>
          </div>

          {batteries.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 rounded-lg">
              <Battery className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No batteries found</p>
              <Link
                href="/assets/batteries/new"
                className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              >
                <Plus className="h-4 w-4" />
                Add your first battery
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {batteries.map((battery) => (
                <Link
                  key={battery.asset_id}
                  href={`/assets/batteries/${battery.asset_id}`}
                  className="block bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow"
                >
                  <div className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-100 rounded-lg">
                          <Battery className="h-6 w-6 text-blue-600" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-gray-900">{battery.name}</h3>
                          {battery.manufacturer && (
                            <p className="text-sm text-gray-600">{battery.manufacturer}</p>
                          )}
                        </div>
                      </div>
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(battery.status)}`}>
                        {battery.status}
                      </span>
                    </div>

                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Capacity:</span>
                        <span className="font-medium text-gray-900">{battery.battery.capacity_kwh} kWh</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Max Power:</span>
                        <span className="font-medium text-gray-900">
                          {Math.min(battery.battery.max_charge_kw, battery.battery.max_discharge_kw)} kW
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Chemistry:</span>
                        <span className="font-medium text-gray-900">
                          {getChemistryLabel(battery.battery.chemistry)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Efficiency:</span>
                        <span className="font-medium text-gray-900">
                          {(battery.battery.round_trip_efficiency * 100).toFixed(1)}%
                        </span>
                      </div>
                      {battery.battery.current_health_percentage !== undefined && (
                        <div className="flex justify-between">
                          <span className="text-gray-600">Health:</span>
                          <span className="font-medium text-gray-900">
                            {battery.battery.current_health_percentage.toFixed(1)}%
                          </span>
                        </div>
                      )}
                    </div>

                    {battery.model && (
                      <div className="mt-4 pt-4 border-t border-gray-100">
                        <p className="text-xs text-gray-500">Model: {battery.model}</p>
                      </div>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Generators Tab */}
      {activeTab === 'generators' && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Generator Assets</h2>
            <Link
              href="/assets/generators/new"
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              <Plus className="h-4 w-4" />
              Add Generator
            </Link>
          </div>

          {generators.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 rounded-lg">
              <Zap className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No generators found</p>
              <Link
                href="/assets/generators/new"
                className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              >
                <Plus className="h-4 w-4" />
                Add your first generator
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {generators.map((generator) => (
                <Link
                  key={generator.asset_id}
                  href={`/assets/generators/${generator.asset_id}`}
                  className="block bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow"
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
                        <span className="text-gray-600">Fuel Cost:</span>
                        <span className="font-medium text-gray-900">
                          ${generator.generator.fuel_cost_per_kwh.toFixed(3)}/kWh
                        </span>
                      </div>
                      {generator.generator.generator_type && (
                        <div className="flex justify-between">
                          <span className="text-gray-600">Type:</span>
                          <span className="font-medium text-gray-900 capitalize">
                            {generator.generator.generator_type.replace('_', ' ')}
                          </span>
                        </div>
                      )}
                    </div>

                    {generator.model && (
                      <div className="mt-4 pt-4 border-t border-gray-100">
                        <p className="text-xs text-gray-500">Model: {generator.model}</p>
                      </div>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  )
}
