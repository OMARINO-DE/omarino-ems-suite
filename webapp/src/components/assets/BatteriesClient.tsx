'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Battery, Plus, Search } from 'lucide-react'
import type { BatteryAsset } from '@/lib/server-api'

interface BatteriesClientProps {
  batteries: BatteryAsset[]
}

export function BatteriesClient({ batteries: initialBatteries }: BatteriesClientProps) {
  const router = useRouter()
  const [batteries, setBatteries] = useState<BatteryAsset[]>(initialBatteries)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [chemistryFilter, setChemistryFilter] = useState<string>('all')

  // Filter batteries client-side
  const filteredBatteries = batteries.filter((battery) => {
    if (statusFilter !== 'all' && battery.status !== statusFilter) return false
    if (chemistryFilter !== 'all' && battery.battery.chemistry !== chemistryFilter) return false
    if (searchTerm) {
      const search = searchTerm.toLowerCase()
      return (
        battery.name.toLowerCase().includes(search) ||
        battery.serial_number?.toLowerCase().includes(search) ||
        battery.manufacturer?.toLowerCase().includes(search)
      )
    }
    return true
  })

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
      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex gap-2">
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
          </div>

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

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Chemistry</label>
            <select
              value={chemistryFilter}
              onChange={(e) => setChemistryFilter(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="all">All Chemistries</option>
              <option value="lithium_ion">Li-ion</option>
              <option value="lithium_iron_phosphate">LiFePO4</option>
              <option value="lead_acid">Lead Acid</option>
              <option value="nickel_metal_hydride">NiMH</option>
              <option value="sodium_sulfur">NaS</option>
              <option value="flow_battery">Flow Battery</option>
            </select>
          </div>
        </div>
      </div>

      {/* Battery List */}
      {filteredBatteries.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <Battery className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 mb-2">No batteries found</p>
          {(searchTerm || statusFilter !== 'all' || chemistryFilter !== 'all') && (
            <p className="text-sm text-gray-500 mb-4">Try adjusting your filters</p>
          )}
          <Link
            href="/assets/batteries/new"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <Plus className="h-4 w-4" />
            Add your first battery
          </Link>
        </div>
      ) : (
        <div>
          <div className="mb-4 text-sm text-gray-600">
            Showing {filteredBatteries.length} {filteredBatteries.length === 1 ? 'battery' : 'batteries'}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredBatteries.map((battery) => (
              <div
                key={battery.asset_id}
                onClick={() => router.push(`/assets/batteries/${battery.asset_id}`)}
                className="bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow cursor-pointer"
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
                      <span className="text-gray-600">Max Charge:</span>
                      <span className="font-medium text-gray-900">{battery.battery.max_charge_kw} kW</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Max Discharge:</span>
                      <span className="font-medium text-gray-900">{battery.battery.max_discharge_kw} kW</span>
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

                  <div className="mt-4 pt-4 border-t border-gray-100 space-y-1">
                    {battery.model && <p className="text-xs text-gray-500">Model: {battery.model}</p>}
                    {battery.serial_number && <p className="text-xs text-gray-500">S/N: {battery.serial_number}</p>}
                    {battery.installation_date && (
                      <p className="text-xs text-gray-500">
                        Installed: {new Date(battery.installation_date).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  )
}
