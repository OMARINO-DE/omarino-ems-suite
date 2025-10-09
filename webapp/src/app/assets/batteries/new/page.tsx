'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Battery, Save, X, AlertCircle } from 'lucide-react'
import { assetService, BatteryAssetCreate } from '@/services/assetService'

export default function NewBatteryPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState<BatteryAssetCreate>({
    name: '',
    manufacturer: '',
    model: '',
    serial_number: '',
    status: 'active',
    battery: {
      capacity_kwh: 0,
      max_charge_kw: 0,
      max_discharge_kw: 0,
      round_trip_efficiency: 0.95,
      min_soc: 10,
      max_soc: 100,
      initial_soc: 50,
      current_health_percentage: 100,
    },
  })

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleBatteryChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      battery: {
        ...prev.battery,
        [name]: e.target.type === 'number' ? parseFloat(value) : value,
      },
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      // Validate required fields
      if (!formData.name || !formData.battery.capacity_kwh || !formData.battery.max_charge_kw || !formData.battery.max_discharge_kw) {
        throw new Error('Please fill in all required fields')
      }

      // Validate ranges
      if (formData.battery.min_soc !== undefined && formData.battery.max_soc !== undefined && formData.battery.min_soc >= formData.battery.max_soc) {
        throw new Error('Min SOC must be less than Max SOC')
      }

      await assetService.createBattery(formData)
      router.push('/assets/batteries')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create battery')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2 text-sm">
          <Link href="/assets" className="text-gray-600 hover:text-gray-900">
            Assets
          </Link>
          <span className="text-gray-400">/</span>
          <Link href="/assets/batteries" className="text-gray-600 hover:text-gray-900">
            Batteries
          </Link>
          <span className="text-gray-400">/</span>
          <span className="text-gray-900 font-semibold">New</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="p-3 bg-blue-100 rounded-lg">
            <Battery className="h-8 w-8 text-blue-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Add Battery Asset</h1>
            <p className="text-gray-600 mt-1">Configure a new battery storage system</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
          <div>
            <p className="text-red-800 font-medium">Error creating battery</p>
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Basic Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                required
                placeholder="e.g., Tesla Powerwall 3"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select
                name="status"
                value={formData.status}
                onChange={handleInputChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="maintenance">Maintenance</option>
                <option value="decommissioned">Decommissioned</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Manufacturer</label>
              <input
                type="text"
                name="manufacturer"
                value={formData.manufacturer}
                onChange={handleInputChange}
                placeholder="e.g., Tesla"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
              <input
                type="text"
                name="model"
                value={formData.model}
                onChange={handleInputChange}
                placeholder="e.g., Powerwall 3"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Serial Number</label>
              <input
                type="text"
                name="serial_number"
                value={formData.serial_number}
                onChange={handleInputChange}
                placeholder="e.g., TPW3-001-2024"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Installation Date</label>
              <input
                type="date"
                name="installation_date"
                value={formData.installation_date || ''}
                onChange={handleInputChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              name="description"
              value={formData.description || ''}
              onChange={handleInputChange}
              rows={3}
              placeholder="Additional notes about this battery..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Battery Specifications */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Battery Specifications</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Capacity (kWh) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                name="capacity_kwh"
                value={formData.battery.capacity_kwh || ''}
                onChange={handleBatteryChange}
                required
                step="0.1"
                min="0"
                placeholder="e.g., 13.5"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Chemistry</label>
              <select
                name="chemistry"
                value={formData.battery.chemistry || ''}
                onChange={handleBatteryChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="">Select chemistry...</option>
                <option value="lithium_ion">Lithium-ion (Li-ion)</option>
                <option value="lithium_iron_phosphate">Lithium Iron Phosphate (LiFePO4)</option>
                <option value="lead_acid">Lead Acid</option>
                <option value="nickel_metal_hydride">Nickel Metal Hydride (NiMH)</option>
                <option value="sodium_sulfur">Sodium Sulfur (NaS)</option>
                <option value="flow_battery">Flow Battery</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max Charge Power (kW) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                name="max_charge_kw"
                value={formData.battery.max_charge_kw || ''}
                onChange={handleBatteryChange}
                required
                step="0.1"
                min="0"
                placeholder="e.g., 11.5"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max Discharge Power (kW) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                name="max_discharge_kw"
                value={formData.battery.max_discharge_kw || ''}
                onChange={handleBatteryChange}
                required
                step="0.1"
                min="0"
                placeholder="e.g., 11.5"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Round-Trip Efficiency (0-1)
              </label>
              <input
                type="number"
                name="round_trip_efficiency"
                value={formData.battery.round_trip_efficiency}
                onChange={handleBatteryChange}
                step="0.01"
                min="0"
                max="1"
                placeholder="e.g., 0.95"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 mt-1">Default: 0.95 (95%)</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Current Health (%)
              </label>
              <input
                type="number"
                name="current_health_percentage"
                value={formData.battery.current_health_percentage}
                onChange={handleBatteryChange}
                step="0.1"
                min="0"
                max="100"
                placeholder="e.g., 100"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Min SOC (%)
              </label>
              <input
                type="number"
                name="min_soc"
                value={formData.battery.min_soc}
                onChange={handleBatteryChange}
                step="0.1"
                min="0"
                max="100"
                placeholder="e.g., 10"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max SOC (%)
              </label>
              <input
                type="number"
                name="max_soc"
                value={formData.battery.max_soc}
                onChange={handleBatteryChange}
                step="0.1"
                min="0"
                max="100"
                placeholder="e.g., 100"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Initial SOC (%)
              </label>
              <input
                type="number"
                name="initial_soc"
                value={formData.battery.initial_soc}
                onChange={handleBatteryChange}
                step="0.1"
                min="0"
                max="100"
                placeholder="e.g., 50"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-3">
          <Link
            href="/assets/batteries"
            className="flex items-center gap-2 px-6 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
          >
            <X className="h-4 w-4" />
            Cancel
          </Link>
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {loading ? 'Creating...' : 'Create Battery'}
          </button>
        </div>
      </form>
    </div>
  )
}
