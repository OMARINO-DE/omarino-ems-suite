import axios, { AxiosInstance, AxiosRequestConfig } from 'axios'

// Use internal Docker network URL for server-side requests, external URL for client-side
const isServer = typeof window === 'undefined'
const API_BASE_URL = isServer 
  ? (process.env.API_URL || 'http://omarino-gateway:8080')
  : ((typeof window !== 'undefined' && (window as any).ENV?.API_URL) || process.env.NEXT_PUBLIC_API_URL || 'https://ems-back.omarino.net')

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

  // Health
  health: {
    getGatewayHealth: () => apiClient.get<any>('/health'),
    getServicesHealth: () => apiClient.get<any>('/api/health/services'),
  },
}
