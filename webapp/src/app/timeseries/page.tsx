'use client'

import { useState, useRef } from 'react'
import useSWR from 'swr'
import { api } from '@/lib/api'
import { BarChart3, Download, Upload } from 'lucide-react'

export default function TimeSeriesPage() {
  const { data: meters, mutate } = useSWR('/api/meters', () => api.timeseries.getMeters())
  const [isImporting, setIsImporting] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8081'

  const handleImportClick = () => {
    fileInputRef.current?.click()
  }

    const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setIsImporting(true)
    try {
      const text = await file.text()
      
      // Parse CSV
      const lines = text.trim().split('\n')
      const headers = lines[0].split(',').map(h => h.trim())
      
      // Group data by meter_id
      const meterDataMap: { [key: string]: any[] } = {}
      
      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',')
        const row: any = {}
        headers.forEach((header, index) => {
          row[header] = values[index]?.trim()
        })
        
        const meterId = row.meter_id || 'unknown'
        if (!meterDataMap[meterId]) {
          meterDataMap[meterId] = []
        }
        meterDataMap[meterId].push(row)
      }
      
      // Step 1: Create or find meters and their series
      const seriesIdMap: { [meterId: string]: string } = {}
      
      for (const [meterName, dataPoints] of Object.entries(meterDataMap)) {
        // Create meter if it doesn't exist
        const createMeterResponse = await fetch(`${API_URL}/api/meters`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: meterName,
            type: 'Electricity',
            timezone: 'America/New_York',
            tags: {}
          })
        })
        
        let meterId: string
        if (createMeterResponse.ok) {
          const meterData = await createMeterResponse.json()
          meterId = meterData.id
        } else if (createMeterResponse.status === 400) {
          // Meter might already exist, try to find it
          const getMetersResponse = await fetch(`${API_URL}/api/meters`)
          const meters = await getMetersResponse.json()
          const existingMeter = meters.find((m: any) => m.name === meterName)
          if (!existingMeter) {
            throw new Error(`Failed to create or find meter ${meterName}`)
          }
          meterId = existingMeter.id
        } else {
          const errorText = await createMeterResponse.text()
          let errorDetail = errorText
          try {
            const errorJson = JSON.parse(errorText)
            errorDetail = errorJson.title || errorJson.message || JSON.stringify(errorJson)
          } catch {
            // Keep errorText as is
          }
          throw new Error(`Failed to create meter ${meterName} (${createMeterResponse.status}): ${errorDetail}`)
        }
        
        // Create series for this meter
        const unit = dataPoints[0]?.unit || 'kWh'
        const createSeriesResponse = await fetch(`${API_URL}/api/series`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            meterId: meterId,
            name: `${meterName} Consumption`,
            description: 'Energy consumption data',
            unit: unit,
            aggregation: 'Sum',
            dataType: 'Consumption',
            timezone: 'America/New_York'
          })
        })
        
        if (createSeriesResponse.ok) {
          const seriesData = await createSeriesResponse.json()
          seriesIdMap[meterName] = seriesData.id
        } else if (createSeriesResponse.status === 400) {
          // Series might already exist, try to find it
          const getSeriesResponse = await fetch(`${API_URL}/api/series?meterId=${meterId}`)
          const series = await getSeriesResponse.json()
          if (series.length === 0) {
            throw new Error(`Failed to create or find series for meter ${meterName}`)
          }
          seriesIdMap[meterName] = series[0].id
        } else {
          throw new Error(`Failed to create series for ${meterName}: ${await createSeriesResponse.text()}`)
        }
      }
      
      // Step 2: Build points array with proper seriesIds
      const allPoints: any[] = []
      for (const [meterName, dataPoints] of Object.entries(meterDataMap)) {
        const seriesId = seriesIdMap[meterName]
        if (!seriesId) continue
        
        for (const row of dataPoints) {
          allPoints.push({
            seriesId: seriesId,
            timestamp: row.timestamp,
            value: parseFloat(row.value),
            quality: 100
          })
        }
      }
      
      // Step 3: Ingest all points
      const ingestResponse = await fetch(`${API_URL}/api/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: file.name,
          points: allPoints
        })
      })

      if (ingestResponse.ok) {
        const result = await ingestResponse.json()
        alert(`Data imported successfully!\nPoints imported: ${result.pointsImported || allPoints.length}\nPoints failed: ${result.pointsFailed || 0}`)
        mutate() // Refresh the meter list
      } else {
        const errorText = await ingestResponse.text()
        let errorMessage = 'Unknown error'
        try {
          const errorJson = JSON.parse(errorText)
          errorMessage = errorJson.message || errorJson.title || JSON.stringify(errorJson)
        } catch {
          errorMessage = errorText
        }
        alert(`Import failed: ${errorMessage}`)
      }
    } catch (error) {
      console.error('Import error:', error)
      alert(`Failed to import data: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsImporting(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Time Series Data</h1>
          <p className="text-gray-600 mt-2">Historical energy data and measurements</p>
        </div>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.json"
            onChange={handleFileUpload}
            className="hidden"
          />
          <button 
            onClick={handleImportClick}
            disabled={isImporting}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Upload className="h-4 w-4" />
            {isImporting ? 'Importing...' : 'Import Data'}
          </button>
        </div>
      </div>

      {/* Meters Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {meters?.map((meter: any) => (
          <MeterCard key={meter.id} meter={meter} />
        ))}
      </div>
    </div>
  )
}

function MeterCard({ meter }: { meter: any }) {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8081'
  
  const handleDownload = async () => {
    try {
      const response = await fetch(`${API_URL}/api/meters/${meter.id}/export`)
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${meter.id}_data.csv`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      } else {
        alert('Failed to download meter data')
      }
    } catch (error) {
      console.error('Download error:', error)
      alert('Failed to download data. Please check the console for details.')
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <BarChart3 className="h-6 w-6 text-primary-600" />
          </div>
          <div>
            <h3 className="font-semibold">{meter.name}</h3>
            <p className="text-sm text-gray-600">{meter.id}</p>
          </div>
        </div>
        <button 
          onClick={handleDownload}
          className="p-2 text-gray-600 hover:bg-gray-100 rounded"
          title="Download meter data"
        >
          <Download className="h-4 w-4" />
        </button>
      </div>
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Location</span>
          <span className="font-medium">{meter.location || 'N/A'}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Type</span>
          <span className="font-medium">{meter.type || 'Electric'}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Unit</span>
          <span className="font-medium">{meter.unit || 'kWh'}</span>
        </div>
      </div>
    </div>
  )
}
