'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Zap, Save, X, AlertCircle } from 'lucide-react'
import { assetService, GeneratorAssetCreate } from '@/services/assetService'

export default function NewGeneratorPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState<GeneratorAssetCreate>({
    name: '',
    manufacturer: '',
    model: '',
    serial_number: '',
    status: 'active',
    generator: {
      rated_capacity_kw: 0,
      max_output_kw: 0,
      min_output_kw: 0,
      fuel_cost_per_kwh: 0,
    },
  })

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleGeneratorChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      generator: {
        ...prev.generator,
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
      if (!formData.name || !formData.generator.rated_capacity_kw || !formData.generator.max_output_kw || !formData.generator.fuel_cost_per_kwh) {
        throw new Error('Please fill in all required fields')
      }

      // Validate ranges
      if (formData.generator.min_output_kw && formData.generator.min_output_kw > formData.generator.max_output_kw) {
        throw new Error('Min output must be less than max output')
      }

      await assetService.createGenerator(formData)
      router.push('/assets/generators')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create generator')
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
          <Link href="/assets/generators" className="text-gray-600 hover:text-gray-900">
            Generators
          </Link>
          <span className="text-gray-400">/</span>
          <span className="text-gray-900 font-semibold">New</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="p-3 bg-amber-100 rounded-lg">
            <Zap className="h-8 w-8 text-amber-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Add Generator Asset</h1>
            <p className="text-gray-600 mt-1">Configure a new backup generator system</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
          <div>
            <p className="text-red-800 font-medium">Error creating generator</p>
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
                placeholder="e.g., Cummins C250 D5"
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
                placeholder="e.g., Cummins"
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
                placeholder="e.g., C250 D5"
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
                placeholder="e.g., C250D5-001-2024"
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
              placeholder="Additional notes about this generator..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Generator Specifications */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Generator Specifications</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Rated Capacity (kW) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                name="rated_capacity_kw"
                value={formData.generator.rated_capacity_kw || ''}
                onChange={handleGeneratorChange}
                required
                step="0.1"
                min="0"
                placeholder="e.g., 250"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Generator Type</label>
              <select
                name="generator_type"
                value={formData.generator.generator_type || ''}
                onChange={handleGeneratorChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="">Select type...</option>
                <option value="diesel">Diesel</option>
                <option value="natural_gas">Natural Gas</option>
                <option value="biogas">Biogas</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max Output (kW) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                name="max_output_kw"
                value={formData.generator.max_output_kw || ''}
                onChange={handleGeneratorChange}
                required
                step="0.1"
                min="0"
                placeholder="e.g., 275"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Min Output (kW)
              </label>
              <input
                type="number"
                name="min_output_kw"
                value={formData.generator.min_output_kw || ''}
                onChange={handleGeneratorChange}
                step="0.1"
                min="0"
                placeholder="e.g., 50"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Fuel Cost ($/kWh) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                name="fuel_cost_per_kwh"
                value={formData.generator.fuel_cost_per_kwh || ''}
                onChange={handleGeneratorChange}
                required
                step="0.001"
                min="0"
                placeholder="e.g., 0.15"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Startup Cost ($)
              </label>
              <input
                type="number"
                name="startup_cost"
                value={formData.generator.startup_cost || ''}
                onChange={handleGeneratorChange}
                step="0.01"
                min="0"
                placeholder="e.g., 50"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Shutdown Cost ($)
              </label>
              <input
                type="number"
                name="shutdown_cost"
                value={formData.generator.shutdown_cost || ''}
                onChange={handleGeneratorChange}
                step="0.01"
                min="0"
                placeholder="e.g., 25"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Min Uptime (hours)
              </label>
              <input
                type="number"
                name="min_uptime_hours"
                value={formData.generator.min_uptime_hours || ''}
                onChange={handleGeneratorChange}
                step="0.1"
                min="0"
                placeholder="e.g., 2"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Min Downtime (hours)
              </label>
              <input
                type="number"
                name="min_downtime_hours"
                value={formData.generator.min_downtime_hours || ''}
                onChange={handleGeneratorChange}
                step="0.1"
                min="0"
                placeholder="e.g., 1"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                CO₂ Emissions (kg/kWh)
              </label>
              <input
                type="number"
                name="co2_emissions_kg_per_kwh"
                value={formData.generator.co2_emissions_kg_per_kwh || ''}
                onChange={handleGeneratorChange}
                step="0.001"
                min="0"
                placeholder="e.g., 0.7"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 mt-1">Typical diesel: ~0.7 kg/kWh</p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-3">
          <Link
            href="/assets/generators"
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
            {loading ? 'Creating...' : 'Create Generator'}
          </button>
        </div>
      </form>
    </div>
  )
}
