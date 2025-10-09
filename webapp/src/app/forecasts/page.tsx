import { Metadata } from 'next'
import { ForecastsClient } from '@/components/forecasts/ForecastsClient'
import { serverApi } from '@/lib/api'

export const metadata: Metadata = {
  title: 'Forecasts | OMARINO EMS',
  description: 'Energy demand predictions and model results',
}

export default async function ForecastsPage() {
  let forecasts = []
  let models = []
  
  try {
    const results = await Promise.all([
      serverApi.forecasts.getForecasts({ limit: 20 }),
      serverApi.forecasts.listModels()
    ])
    forecasts = results[0]
    models = results[1]
  } catch (error) {
    console.error('Failed to load forecasts data:', error)
  }
  
  return <ForecastsClient initialForecasts={forecasts} initialModels={models} />
}
