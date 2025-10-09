import { serverApi } from '@/lib/api'
import { TimeSeriesClient } from '@/components/timeseries/TimeSeriesClient'

export const metadata = {
  title: 'Time Series Data | OMARINO EMS',
  description: 'Historical energy data and measurements',
}

export default async function TimeSeriesPage() {
  let meters = []
  
  try {
    meters = await serverApi.timeseries.getMeters()
  } catch (error) {
    console.error('Failed to load meters:', error)
    // Continue with empty array
  }

  return (
    <div className="space-y-6">
      <TimeSeriesClient initialMeters={meters} />
    </div>
  )
}
