/**
 * Asset Management Service
 * API client for OMARINO EMS Asset Service
 */

const API_URL = typeof window !== 'undefined' 
  ? (window as any).ENV?.API_URL || 'https://ems-back.omarino.net'
  : 'https://ems-back.omarino.net'

const ASSET_API_BASE = `${API_URL}/api/assets`

export interface BatterySpec {
  capacity_kwh: number
  usable_capacity_kwh?: number
  max_charge_kw: number
  max_discharge_kw: number
  round_trip_efficiency: number
  min_soc: number
  max_soc: number
  initial_soc: number
  chemistry?: 'lithium_ion' | 'lithium_iron_phosphate' | 'lead_acid' | 'nickel_metal_hydride' | 'sodium_sulfur' | 'flow_battery' | 'other'
  degradation_cost_per_kwh?: number
  current_health_percentage?: number
  continuous_charge_kw?: number
  continuous_discharge_kw?: number
  charge_efficiency?: number
  discharge_efficiency?: number
  target_soc?: number
  cycle_life?: number
  current_cycle_count?: number
  ramp_up_rate_kw_per_sec?: number
  ramp_down_rate_kw_per_sec?: number
  updated_at?: string
  asset_id?: string
}

export interface BatteryAsset {
  asset_id: string
  asset_type: 'battery'
  name: string
  description?: string
  location?: string
  site_id?: string
  manufacturer?: string
  model?: string
  serial_number?: string
  installation_date?: string
  status: 'active' | 'inactive' | 'maintenance' | 'decommissioned'
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
  battery: BatterySpec
  site_name?: string
  capacity_rating?: number
  online?: boolean
}

export interface BatteryAssetCreate {
  name: string
  description?: string
  location?: string
  site_id?: string
  manufacturer?: string
  model?: string
  serial_number?: string
  installation_date?: string
  status?: 'active' | 'inactive' | 'maintenance' | 'decommissioned'
  metadata?: Record<string, any>
  battery: {
    capacity_kwh: number
    usable_capacity_kwh?: number
    max_charge_kw: number
    max_discharge_kw: number
    round_trip_efficiency?: number
    min_soc?: number
    max_soc?: number
    initial_soc?: number
    chemistry?: 'lithium_ion' | 'lithium_iron_phosphate' | 'lead_acid' | 'nickel_metal_hydride' | 'sodium_sulfur' | 'flow_battery' | 'other'
    degradation_cost_per_kwh?: number
    current_health_percentage?: number
  }
}

export interface GeneratorSpec {
  rated_capacity_kw: number
  max_output_kw: number
  min_output_kw?: number
  generator_type?: 'diesel' | 'natural_gas' | 'biogas' | 'other'
  fuel_cost_per_kwh: number
  startup_cost?: number
  shutdown_cost?: number
  min_uptime_hours?: number
  min_downtime_hours?: number
  co2_emissions_kg_per_kwh?: number
  fuel_type?: string
  efficiency_at_rated_load?: number
  ramp_up_rate_kw_per_min?: number
  ramp_down_rate_kw_per_min?: number
  operating_hours?: number
  updated_at?: string
  asset_id?: string
}

export interface GeneratorAsset {
  asset_id: string
  asset_type: 'generator'
  name: string
  description?: string
  location?: string
  site_id?: string
  manufacturer?: string
  model?: string
  serial_number?: string
  installation_date?: string
  status: 'active' | 'inactive' | 'maintenance' | 'decommissioned'
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
  generator: GeneratorSpec
  site_name?: string
  capacity_rating?: number
  online?: boolean
}

export interface GeneratorAssetCreate {
  name: string
  description?: string
  location?: string
  site_id?: string
  manufacturer?: string
  model?: string
  serial_number?: string
  installation_date?: string
  status?: 'active' | 'inactive' | 'maintenance' | 'decommissioned'
  metadata?: Record<string, any>
  generator: {
    rated_capacity_kw: number
    max_output_kw: number
    min_output_kw?: number
    generator_type?: 'diesel' | 'natural_gas' | 'biogas' | 'other'
    fuel_cost_per_kwh: number
    startup_cost?: number
    shutdown_cost?: number
    min_uptime_hours?: number
    min_downtime_hours?: number
    co2_emissions_kg_per_kwh?: number
  }
}

export interface AssetListResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface HealthStatus {
  status: 'healthy' | 'unhealthy' | 'degraded'
  version: string
  database: 'connected' | 'disconnected' | 'unknown'
}

class AssetService {
  /**
   * Check asset service health
   */
  async getHealth(): Promise<HealthStatus> {
    const response = await fetch(`${ASSET_API_BASE}/health`)
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * List all batteries
   */
  async listBatteries(params?: {
    status?: string
    site_id?: string
    chemistry?: string
    search?: string
    limit?: number
    offset?: number
  }): Promise<AssetListResponse<BatteryAsset>> {
    const queryParams = new URLSearchParams()
    if (params?.status) queryParams.append('status', params.status)
    if (params?.site_id) queryParams.append('site_id', params.site_id)
    if (params?.chemistry) queryParams.append('chemistry', params.chemistry)
    if (params?.search) queryParams.append('search', params.search)
    if (params?.limit) queryParams.append('limit', params.limit.toString())
    if (params?.offset) queryParams.append('offset', params.offset.toString())

    const url = `${ASSET_API_BASE}/batteries${queryParams.toString() ? '?' + queryParams.toString() : ''}`
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`Failed to list batteries: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * Get battery by ID
   */
  async getBattery(assetId: string): Promise<BatteryAsset> {
    const response = await fetch(`${ASSET_API_BASE}/batteries/${assetId}`)
    if (!response.ok) {
      throw new Error(`Failed to get battery: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * Create new battery
   */
  async createBattery(battery: BatteryAssetCreate): Promise<BatteryAsset> {
    const response = await fetch(`${ASSET_API_BASE}/batteries`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(battery),
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(`Failed to create battery: ${error.detail || response.statusText}`)
    }
    return response.json()
  }

  /**
   * Update battery
   */
  async updateBattery(assetId: string, battery: Partial<BatteryAssetCreate>): Promise<BatteryAsset> {
    const response = await fetch(`${ASSET_API_BASE}/batteries/${assetId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(battery),
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(`Failed to update battery: ${error.detail || response.statusText}`)
    }
    return response.json()
  }

  /**
   * Delete battery
   */
  async deleteBattery(assetId: string): Promise<void> {
    const response = await fetch(`${ASSET_API_BASE}/batteries/${assetId}`, {
      method: 'DELETE',
    })
    if (!response.ok) {
      throw new Error(`Failed to delete battery: ${response.statusText}`)
    }
  }

  /**
   * List all generators
   */
  async listGenerators(params?: {
    status?: string
    site_id?: string
    generator_type?: string
    search?: string
    limit?: number
    offset?: number
  }): Promise<AssetListResponse<GeneratorAsset>> {
    const queryParams = new URLSearchParams()
    if (params?.status) queryParams.append('status', params.status)
    if (params?.site_id) queryParams.append('site_id', params.site_id)
    if (params?.generator_type) queryParams.append('generator_type', params.generator_type)
    if (params?.search) queryParams.append('search', params.search)
    if (params?.limit) queryParams.append('limit', params.limit.toString())
    if (params?.offset) queryParams.append('offset', params.offset.toString())

    const url = `${ASSET_API_BASE}/generators${queryParams.toString() ? '?' + queryParams.toString() : ''}`
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`Failed to list generators: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * Get generator by ID
   */
  async getGenerator(assetId: string): Promise<GeneratorAsset> {
    const response = await fetch(`${ASSET_API_BASE}/generators/${assetId}`)
    if (!response.ok) {
      throw new Error(`Failed to get generator: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * Create new generator
   */
  async createGenerator(generator: GeneratorAssetCreate): Promise<GeneratorAsset> {
    const response = await fetch(`${ASSET_API_BASE}/generators`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(generator),
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(`Failed to create generator: ${error.detail || response.statusText}`)
    }
    return response.json()
  }

  /**
   * Update generator
   */
  async updateGenerator(assetId: string, generator: Partial<GeneratorAssetCreate>): Promise<GeneratorAsset> {
    const response = await fetch(`${ASSET_API_BASE}/generators/${assetId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(generator),
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(`Failed to update generator: ${error.detail || response.statusText}`)
    }
    return response.json()
  }

  /**
   * Delete generator
   */
  async deleteGenerator(assetId: string): Promise<void> {
    const response = await fetch(`${ASSET_API_BASE}/generators/${assetId}`, {
      method: 'DELETE',
    })
    if (!response.ok) {
      throw new Error(`Failed to delete generator: ${response.statusText}`)
    }
  }
}

export const assetService = new AssetService()
