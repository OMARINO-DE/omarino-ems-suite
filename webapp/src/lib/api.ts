import axios, { AxiosInstance, AxiosRequestConfig } from 'axios'

// Use internal Docker network URL for server-side requests, external URL for client-side
const isServer = typeof window === 'undefined'

// For client-side, always use the public API URL
// For server-side, use the internal Docker network URL
const API_BASE_URL = isServer 
  ? (process.env.INTERNAL_API_URL || 'http://omarino-gateway:8080')
  : 'https://ems-back.omarino.net'

console.log('[API Client] Initializing with baseURL:', API_BASE_URL, 'isServer:', isServer)

// Server-side fetch utility (doesn't use axios or localStorage)
async function serverFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const baseUrl = process.env.INTERNAL_API_URL || process.env.API_URL || 'http://omarino-gateway:8080'
  const fullUrl = url.startsWith('http') ? url : `${baseUrl}${url}`
  
  const response = await fetch(fullUrl, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    next: { revalidate: 10 }, // Cache for 10 seconds
  })

  if (!response.ok) {
    // Return empty data for 404s on list endpoints
    if (response.status === 404 && (url.includes('/meters') || url.includes('/forecasts') || url.includes('/optimizations') || url.includes('/workflows'))) {
      return (url.includes('/forecasts') ? { forecasts: [] } : 
              url.includes('/optimizations') ? { optimizations: [] } :
              url.includes('/workflows') ? [] :
              url.includes('/models') ? { models: [] } :
              url.includes('/types') ? { types: [] } :
              []) as T
    }
    throw new Error(`API Error: ${response.status} ${response.statusText}`)
  }

  return response.json()
}

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    })

    // Request interceptor for adding auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor for handling errors
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Handle unauthorized access
          localStorage.removeItem('auth_token')
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config)
    return response.data
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config)
    return response.data
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config)
    return response.data
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config)
    return response.data
  }
}

export const apiClient = new ApiClient()

// API endpoints
export const api = {
  // Authentication
  auth: {
    login: (credentials: { username: string; password: string }) =>
      apiClient.post<{ token: string; expiresAt: string }>('/api/auth/login', credentials),
    validate: () => apiClient.get<{ valid: boolean }>('/api/auth/validate'),
  },

  // Time Series
  timeseries: {
    getMeters: () => apiClient.get<any[]>('/api/meters'),
    getMeter: (id: string) => apiClient.get<any>(`/api/meters/${id}`),
    getSeries: (meterId?: string) => 
      apiClient.get<any[]>('/api/series', { params: meterId ? { meterId } : undefined }),
    getSeriesData: (seriesId: string, params?: { from?: string; to?: string; agg?: string; interval?: string }) =>
      apiClient.get<any>(`/api/series/${seriesId}/range`, { params }),
    ingestData: (data: any) => apiClient.post('/api/ingest', data),
  },

  // Forecasts
  forecasts: {
    listModels: async () => {
      const response = await apiClient.get<{ models: any[] }>('/api/forecast/models')
      return response.models || []
    },
    runForecast: (model: string, params: any) =>
      apiClient.post<any>('/api/forecast/forecast', { ...params, model }),
    getForecasts: async (params?: { limit?: number }) => {
      try {
        const response = await apiClient.get<{ forecasts: any[] }>('/api/forecast/forecasts', { params })
        return response.forecasts || []
      } catch (error: any) {
        // Return empty array if 404 (no forecasts yet)
        if (error.response?.status === 404) {
          return []
        }
        throw error
      }
    },
    getForecast: (id: string) => apiClient.get<any>(`/api/forecast/forecasts/${id}`),
  },

  // Optimization
  optimization: {
    listTypes: async () => {
      const response = await apiClient.get<{ types: any[] }>('/api/optimize/types')
      return response.types || []
    },
    createOptimization: (params: any) => apiClient.post<any>('/api/optimize/optimize', params),
    getOptimization: (id: string) => apiClient.get<any>(`/api/optimize/optimizations/${id}`),
    listOptimizations: async (params?: { status?: string; type?: string; limit?: number }) => {
      try {
        const response = await apiClient.get<{ optimizations: any[] }>('/api/optimize/optimizations', { params })
        return response.optimizations || []
      } catch (error: any) {
        // Return empty array if 404 (no optimizations yet)
        if (error.response?.status === 404) {
          return []
        }
        throw error
      }
    },
    cancelOptimization: (id: string) => apiClient.delete(`/api/optimize/optimizations/${id}`),
  },

  // Scheduler
  scheduler: {
    getWorkflows: () => apiClient.get<any[]>('/api/scheduler/workflows'),
    getWorkflow: (id: string) => apiClient.get<any>(`/api/scheduler/workflows/${id}`),
    createWorkflow: (workflow: any) => apiClient.post<any>('/api/scheduler/workflows', workflow),
    updateWorkflow: (id: string, workflow: any) => apiClient.put<any>(`/api/scheduler/workflows/${id}`, workflow),
    deleteWorkflow: (id: string) => apiClient.delete(`/api/scheduler/workflows/${id}`),
    validateWorkflow: (workflow: any) => apiClient.post<any>('/api/scheduler/workflows/validate', workflow),
    triggerWorkflow: (id: string) => apiClient.post<any>(`/api/scheduler/workflows/${id}/trigger`),
    getExecutions: (params?: { workflowId?: string; limit?: number }) =>
      apiClient.get<any[]>('/api/scheduler/executions', { params }),
    getExecution: (id: string) => apiClient.get<any>(`/api/scheduler/executions/${id}`),
    cancelExecution: (id: string) => apiClient.post(`/api/scheduler/executions/${id}/cancel`),
    getScheduledJobs: () => apiClient.get<any[]>('/api/scheduler/jobs'),
  },

  // Assets
  assets: {
    listBatteries: async (params?: { limit?: number; offset?: number; status?: string; site_id?: string; search?: string; chemistry?: string }) => {
      try {
        const response = await apiClient.get<any>('/api/assets/batteries', { params })
        return response
      } catch (error: any) {
        if (error.response?.status === 404) {
          return { items: [], total: 0, limit: params?.limit || 50, offset: params?.offset || 0 }
        }
        throw error
      }
    },
    getBattery: (id: string) => apiClient.get<any>(`/api/assets/batteries/${id}`),
    createBattery: (data: any) => apiClient.post<any>('/api/assets/batteries', data),
    updateBattery: (id: string, data: any) => apiClient.put<any>(`/api/assets/batteries/${id}`, data),
    deleteBattery: (id: string) => apiClient.delete(`/api/assets/batteries/${id}`),
    
    listGenerators: async (params?: { limit?: number; offset?: number; status?: string; site_id?: string; search?: string; generator_type?: string }) => {
      try {
        const response = await apiClient.get<any>('/api/assets/generators', { params })
        return response
      } catch (error: any) {
        if (error.response?.status === 404) {
          return { items: [], total: 0, limit: params?.limit || 50, offset: params?.offset || 0 }
        }
        throw error
      }
    },
    getGenerator: (id: string) => apiClient.get<any>(`/api/assets/generators/${id}`),
    createGenerator: (data: any) => apiClient.post<any>('/api/assets/generators', data),
    updateGenerator: (id: string, data: any) => apiClient.put<any>(`/api/assets/generators/${id}`, data),
    deleteGenerator: (id: string) => apiClient.delete(`/api/assets/generators/${id}`),
  },

  // Health
  health: {
    getGatewayHealth: () => apiClient.get<any>('/health'),
    getServicesHealth: () => apiClient.get<any>('/api/health/services'),
  },
}

// Server-side only API functions (for SSR)
export const serverApi = {
  timeseries: {
    getMeters: () => serverFetch<any[]>('/api/meters'),
  },
  forecasts: {
    listModels: async () => {
      const response = await serverFetch<{ models: any[] }>('/api/forecast/models')
      return response.models || []
    },
    getForecasts: async (params?: { limit?: number }) => {
      const queryString = params ? `?${new URLSearchParams(params as any).toString()}` : ''
      const response = await serverFetch<{ forecasts: any[] }>(`/api/forecast/forecasts${queryString}`)
      return response.forecasts || []
    },
  },
  optimization: {
    listTypes: async () => {
      const response = await serverFetch<{ types: any[] }>('/api/optimize/types')
      return response.types || []
    },
    listOptimizations: async (params?: { status?: string; type?: string; limit?: number }) => {
      const queryString = params ? `?${new URLSearchParams(params as any).toString()}` : ''
      const response = await serverFetch<{ optimizations: any[] }>(`/api/optimize/optimizations${queryString}`)
      return response.optimizations || []
    },
  },
  scheduler: {
    getWorkflows: () => serverFetch<any[]>('/api/scheduler/workflows'),
    getExecutions: async (params?: { workflowId?: string; limit?: number }) => {
      const queryString = params ? `?${new URLSearchParams(params as any).toString()}` : ''
      return serverFetch<any[]>(`/api/scheduler/executions${queryString}`)
    },
  },
}
