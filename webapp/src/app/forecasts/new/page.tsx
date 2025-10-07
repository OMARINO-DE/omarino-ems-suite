'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import useSWR from 'swr'
import { api } from '@/lib/api'
import { ArrowLeft, TrendingUp, Download, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

export default function NewForecastPage() {
  const router = useRouter()
  const { data: models, isLoading: modelsLoading } = useSWR('/api/forecast/models', () => 
    api.forecasts.listModels()
  )
  const { data: series, isLoading: seriesLoading } = useSWR('/api/timeseries/series', () =>
    api.timeseries.getSeries()
  )

  const [selectedModel, setSelectedModel] = useState('')
  const [seriesId, setSeriesId] = useState('')
  const [horizon, setHorizon] = useState('24')
  const [interval, setInterval] = useState('1H')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [forecastResult, setForecastResult] = useState<any>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setForecastResult(null)
    
    if (!selectedModel || !seriesId) {
      setError('Please fill in all required fields')
      return
    }

    setIsSubmitting(true)
    try {
      // Convert interval to ISO 8601 granularity format
      const granularityMap: Record<string, string> = {
        '15min': 'PT15M',
        '30min': 'PT30M',
        '1H': 'PT1H',
        '1D': 'P1D',
      }
      
      const result = await api.forecasts.runForecast(selectedModel, {
        series_id: seriesId,
        horizon: parseInt(horizon),
        granularity: granularityMap[interval] || 'PT1H',
      })
      
      setForecastResult(result)
    } catch (err: any) {
      console.error('Forecast creation error:', err)
      setError(err.response?.data?.detail || 'Failed to create forecast. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (modelsLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.back()}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Create New Forecast</h1>
          <p className="text-gray-600 mt-1">Run a forecast on your time series data</p>
        </div>
      </div>

      {/* Form */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          {/* Model Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Forecast Model *
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              required
            >
              <option value="">Select a model...</option>
              {models?.map((model: any) => (
                <option key={model.name} value={model.name}>
                  {model.name} - {model.description}
                </option>
              ))}
            </select>
            <p className="mt-1 text-sm text-gray-500">
              Choose the forecasting algorithm to use
            </p>
          </div>

          {/* Series Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Time Series *
            </label>
            <select
              value={seriesId}
              onChange={(e) => setSeriesId(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              required
            >
              <option value="">Select a series...</option>
              {series?.map((s: any) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.meterId})
                </option>
              ))}
            </select>
            <p className="mt-1 text-sm text-gray-500">
              Select the time series to forecast
            </p>
          </div>

          {/* Forecast Horizon */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Forecast Horizon
            </label>
            <div className="flex gap-4">
              <input
                type="number"
                value={horizon}
                onChange={(e) => setHorizon(e.target.value)}
                min="1"
                max="168"
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
              <select
                value={interval}
                onChange={(e) => setInterval(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="15min">15 minutes</option>
                <option value="30min">30 minutes</option>
                <option value="1H">1 hour</option>
                <option value="1D">1 day</option>
              </select>
            </div>
            <p className="mt-1 text-sm text-gray-500">
              Number of time steps to forecast into the future
            </p>
          </div>

          {/* Model Info */}
          {selectedModel && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-semibold text-blue-900 mb-2">Model Information</h3>
              {(() => {
                const model = models?.find((m: any) => m.name === selectedModel)
                return (
                  <div className="space-y-1 text-sm text-blue-800">
                    <p><strong>Type:</strong> {model?.type}</p>
                    <p><strong>Description:</strong> {model?.description}</p>
                    <p><strong>Quantile Support:</strong> {model?.supports_quantiles ? 'Yes' : 'No'}</p>
                  </div>
                )
              })()}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={() => router.back()}
              className="flex-1 px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !selectedModel || !seriesId}
              className="flex-1 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Forecast'
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Forecast Results */}
      {forecastResult && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">Forecast Results</h2>
            <button
              onClick={() => {
                const csvContent = generateCSV(forecastResult)
                downloadCSV(csvContent, `forecast_${forecastResult.forecast_id}.csv`)
              }}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center gap-2"
            >
              <Download className="h-4 w-4" />
              Download CSV
            </button>
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="text-sm text-blue-600 font-medium">Model Used</div>
              <div className="text-2xl font-bold text-blue-900 mt-1">{forecastResult.model_used}</div>
            </div>
            <div className="bg-green-50 rounded-lg p-4">
              <div className="text-sm text-green-600 font-medium">Forecast Points</div>
              <div className="text-2xl font-bold text-green-900 mt-1">{forecastResult.point_forecast.length}</div>
            </div>
            <div className="bg-purple-50 rounded-lg p-4">
              <div className="text-sm text-purple-600 font-medium">Training Samples</div>
              <div className="text-2xl font-bold text-purple-900 mt-1">{forecastResult.metadata?.training_samples || 'N/A'}</div>
            </div>
            <div className="bg-orange-50 rounded-lg p-4">
              <div className="text-sm text-orange-600 font-medium">Training Time</div>
              <div className="text-2xl font-bold text-orange-900 mt-1">
                {forecastResult.metadata?.training_time_seconds ? 
                  `${forecastResult.metadata.training_time_seconds.toFixed(2)}s` : 'N/A'}
              </div>
            </div>
          </div>

          {/* Forecast Chart */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-4">Forecast Visualization</h3>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={prepareChartData(forecastResult)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="timestamp" 
                    tick={{ fontSize: 12 }}
                    angle={-45}
                    textAnchor="end"
                    height={80}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="value" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    name="Forecast Value"
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Forecast Table */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Forecast Data</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Step
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Timestamp
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Forecast Value
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {forecastResult.timestamps.map((timestamp: string, idx: number) => (
                    <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {idx + 1}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(timestamp).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {forecastResult.point_forecast[idx].toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Actions */}
          <div className="mt-6 flex gap-3">
            <button
              onClick={() => setForecastResult(null)}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
            >
              Create Another Forecast
            </button>
            <button
              onClick={() => router.push('/forecasts')}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              Back to Forecasts
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// Helper functions
function prepareChartData(forecastResult: any) {
  return forecastResult.timestamps.map((timestamp: string, idx: number) => ({
    timestamp: new Date(timestamp).toLocaleTimeString([], { 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit' 
    }),
    value: forecastResult.point_forecast[idx]
  }))
}

function generateCSV(forecastResult: any): string {
  const headers = ['Step', 'Timestamp', 'Forecast Value']
  const rows = forecastResult.timestamps.map((timestamp: string, idx: number) => [
    idx + 1,
    timestamp,
    forecastResult.point_forecast[idx]
  ])
  
  return [
    headers.join(','),
    ...rows.map((row: any[]) => row.join(','))
  ].join('\n')
}

function downloadCSV(content: string, filename: string) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  if (link.download !== undefined) {
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', filename)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }
}
