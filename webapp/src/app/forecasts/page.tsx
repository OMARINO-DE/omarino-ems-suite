'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import useSWR from 'swr'
import { api } from '@/lib/api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { TrendingUp, Calendar, Clock, Plus, X } from 'lucide-react'

export default function ForecastsPage() {
  const router = useRouter()
  const { data: forecasts, isLoading, error, mutate } = useSWR('/api/forecast/forecasts', async () => {
    try {
      return await api.forecasts.getForecasts({ limit: 20 })
    } catch (e) {
      console.error('Failed to load forecasts:', e)
      // Return empty array if endpoint doesn't exist
      return []
    }
  }, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
    refreshInterval: 10000 // Refresh every 10 seconds to show new forecasts
  })
  const { data: models } = useSWR('/api/forecast/models', () => api.forecasts.listModels())
  const [showNewForecastModal, setShowNewForecastModal] = useState(false)
  const [selectedForecastId, setSelectedForecastId] = useState<string | null>(null)

  if (isLoading) {
    return <div className="flex items-center justify-center min-h-screen">
      <div className="text-gray-600">Loading...</div>
    </div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Forecasts</h1>
          <p className="text-gray-600 mt-2">Energy demand predictions and model results</p>
        </div>
        <button 
          onClick={() => router.push('/forecasts/new')}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          New Forecast
        </button>
      </div>

      {showNewForecastModal && (
        <NewForecastModal 
          models={models || []}
          onClose={() => setShowNewForecastModal(false)}
          onSuccess={() => {
            mutate()
            setShowNewForecastModal(false)
          }}
        />
      )}

      {/* Available Models */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Available Models</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {models?.map((model: any) => (
            <ModelCard key={model.name} model={model} />
          ))}
        </div>
      </div>

      {/* Recent Forecasts */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Recent Forecasts</h2>
        {!forecasts || forecasts.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <TrendingUp className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No forecasts yet. Create your first forecast to get started!</p>
          </div>
        ) : (
          <div className="space-y-4">
            {forecasts.map((forecast: any) => (
              <ForecastCard 
                key={forecast.forecast_id} 
                forecast={forecast} 
                onClick={() => setSelectedForecastId(forecast.forecast_id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Forecast Detail Modal */}
      {selectedForecastId && (
        <ForecastDetailModal 
          forecastId={selectedForecastId}
          onClose={() => setSelectedForecastId(null)}
        />
      )}
    </div>
  )
}

function ModelCard({ model }: { model: any }) {
  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors">
      <h3 className="font-semibold text-lg mb-2">{model.name}</h3>
      <p className="text-sm text-gray-600 mb-3">{model.description}</p>
      <div className="flex gap-2">
        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
          {model.type}
        </span>
      </div>
    </div>
  )
}

function ForecastCard({ forecast, onClick }: { forecast: any; onClick?: () => void }) {
  return (
    <div 
      className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 hover:shadow-md transition-all cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold">{forecast.model_name}</h3>
          <p className="text-sm text-gray-600">Series: {forecast.series_id}</p>
        </div>
        <span className={`px-2 py-1 text-xs rounded ${
          forecast.status === 'completed' ? 'bg-green-100 text-green-800' : 
          forecast.status === 'failed' ? 'bg-red-100 text-red-800' : 
          'bg-blue-100 text-blue-800'
        }`}>
          {forecast.status}
        </span>
      </div>
      <div className="flex gap-4 text-sm text-gray-600">
        <div className="flex items-center gap-1">
          <Calendar className="h-4 w-4" />
          <span>{forecast.horizon} steps ({forecast.granularity})</span>
        </div>
        <div className="flex items-center gap-1">
          <Clock className="h-4 w-4" />
          <span>{new Date(forecast.created_at).toLocaleString()}</span>
        </div>
        {forecast.result_count > 0 && (
          <div className="flex items-center gap-1">
            <TrendingUp className="h-4 w-4" />
            <span>{forecast.result_count} points</span>
          </div>
        )}
      </div>
      {forecast.metrics && (
        <div className="mt-3 flex gap-3 text-xs text-gray-500">
          {forecast.metrics.mae && <span>MAE: {forecast.metrics.mae.toFixed(2)}</span>}
          {forecast.metrics.rmse && <span>RMSE: {forecast.metrics.rmse.toFixed(2)}</span>}
          {forecast.metrics.mape && <span>MAPE: {forecast.metrics.mape.toFixed(2)}%</span>}
        </div>
      )}
    </div>
  )
}

function ForecastDetailModal({ forecastId, onClose }: { forecastId: string; onClose: () => void }) {
  const { data: forecast, isLoading } = useSWR(
    forecastId ? `/api/forecast/forecasts/${forecastId}` : null,
    () => api.forecasts.getForecast(forecastId)
  )

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
          <div className="text-center py-8">Loading forecast details...</div>
        </div>
      </div>
    )
  }

  if (!forecast || !forecast.results) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl p-6 max-w-4xl w-full mx-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold">Forecast Not Found</h2>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded">
              <X className="h-5 w-5" />
            </button>
          </div>
          <p>No forecast data available.</p>
        </div>
      </div>
    )
  }

  // Prepare chart data
  const chartData = forecast.results.map((point: any) => ({
    timestamp: new Date(point.timestamp).toLocaleString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit' 
    }),
    value: point.value,
    lower: point.lower_bound,
    upper: point.upper_bound
  }))

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-6xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold">{forecast.model_name} Forecast</h2>
            <p className="text-gray-600">Series: {forecast.series_id}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Metadata */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm text-gray-600">Status</div>
            <div className="font-semibold">{forecast.status}</div>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm text-gray-600">Horizon</div>
            <div className="font-semibold">{forecast.horizon} {forecast.granularity}</div>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm text-gray-600">Created</div>
            <div className="font-semibold text-sm">{new Date(forecast.created_at).toLocaleString()}</div>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm text-gray-600">Data Points</div>
            <div className="font-semibold">{forecast.results.length}</div>
          </div>
        </div>

        {/* Metrics */}
        {forecast.metrics && (
          <div className="bg-blue-50 p-4 rounded-lg mb-6">
            <h3 className="font-semibold mb-2">Model Metrics</h3>
            <div className="grid grid-cols-3 gap-4">
              {forecast.metrics.mae && (
                <div>
                  <div className="text-sm text-gray-600">MAE</div>
                  <div className="text-lg font-semibold">{forecast.metrics.mae.toFixed(2)}</div>
                </div>
              )}
              {forecast.metrics.rmse && (
                <div>
                  <div className="text-sm text-gray-600">RMSE</div>
                  <div className="text-lg font-semibold">{forecast.metrics.rmse.toFixed(2)}</div>
                </div>
              )}
              {forecast.metrics.mape && (
                <div>
                  <div className="text-sm text-gray-600">MAPE</div>
                  <div className="text-lg font-semibold">{forecast.metrics.mape.toFixed(2)}%</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Chart */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="font-semibold mb-4">Forecast Results</h3>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="timestamp" 
                fontSize={12}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis fontSize={12} />
              <Tooltip />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="value" 
                stroke="#2563eb" 
                strokeWidth={2}
                name="Forecast"
                dot={false}
              />
              {chartData[0]?.lower !== null && (
                <>
                  <Line 
                    type="monotone" 
                    dataKey="lower" 
                    stroke="#93c5fd" 
                    strokeWidth={1}
                    strokeDasharray="3 3"
                    name="Lower Bound (5%)"
                    dot={false}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="upper" 
                    stroke="#93c5fd" 
                    strokeWidth={1}
                    strokeDasharray="3 3"
                    name="Upper Bound (95%)"
                    dot={false}
                  />
                </>
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

function NewForecastModal({ 
  models, 
  onClose, 
  onSuccess 
}: { 
  models: any[]
  onClose: () => void
  onSuccess: () => void
}) {
  const [selectedModel, setSelectedModel] = useState('')
  const [seriesId, setSeriesId] = useState('')
  const [horizon, setHorizon] = useState('24')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!selectedModel || !seriesId) {
      alert('Please fill in all required fields')
      return
    }

    setIsSubmitting(true)
    try {
      await api.forecasts.runForecast(selectedModel, {
        seriesId,
        horizon: parseInt(horizon),
      })
      
      alert('Forecast created successfully!')
      onSuccess()
    } catch (error) {
      console.error('Forecast creation error:', error)
      alert('Failed to create forecast. Please check the console for details.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Create New Forecast</h2>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Model *
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              required
            >
              <option value="">Select a model...</option>
              {models.map((model) => (
                <option key={model.name} value={model.name}>
                  {model.name} - {model.description}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Series ID *
            </label>
            <input
              type="text"
              value={seriesId}
              onChange={(e) => setSeriesId(e.target.value)}
              placeholder="e.g., meter-001-demand"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Forecast Horizon (hours)
            </label>
            <input
              type="number"
              value={horizon}
              onChange={(e) => setHorizon(e.target.value)}
              min="1"
              max="168"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Creating...' : 'Create Forecast'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
