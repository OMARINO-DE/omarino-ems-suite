import Link from 'next/link'
import { Plus, RefreshCw, AlertCircle } from 'lucide-react'
import { getBatteries } from '@/lib/server-api'
import { BatteriesClient } from '@/components/assets/BatteriesClient'

export const dynamic = 'force-dynamic' // Disable static generation
export const revalidate = 0 // Disable caching

export default async function BatteriesPage() {
  // Fetch data on the server using internal Docker network
  let batteries: any[] = []
  let error: string | null = null

  try {
    const data = await getBatteries({ limit: 100 })
    batteries = data.items
  } catch (err) {
    error = err instanceof Error ? err.message : 'Failed to load batteries'
    console.error('Error loading batteries:', err)
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Link href="/assets" className="text-gray-600 hover:text-gray-900">
              Assets
            </Link>
            <span className="text-gray-400">/</span>
            <span className="text-gray-900 font-semibold">Batteries</span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900">Battery Assets</h1>
          <p className="text-gray-600 mt-2">Manage and monitor battery storage systems</p>
        </div>
        <div className="flex gap-3">
          <Link
            href="/assets/batteries"
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Link>
          <Link
            href="/assets/batteries/new"
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <Plus className="h-4 w-4" />
            Add Battery
          </Link>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-red-600" />
          <div>
            <p className="text-red-800 font-medium">Error loading batteries</p>
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Client-side filtering and list */}
      <BatteriesClient batteries={batteries} />
    </div>
  )
}
