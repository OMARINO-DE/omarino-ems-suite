import Link from 'next/link'
import { Battery, Zap, Activity, RefreshCw } from 'lucide-react'
import { getBatteries, getGenerators } from '@/lib/server-api'
import { AssetsClient } from '@/components/assets/AssetsClient'

export const dynamic = 'force-dynamic' // Disable static generation
export const revalidate = 0 // Disable caching

export default async function AssetsPage() {
  // Fetch data on the server using internal Docker network
  let batteries: any[] = []
  let generators: any[] = []
  let error: string | null = null

  try {
    const [batteriesData, generatorsData] = await Promise.all([
      getBatteries({ limit: 100 }),
      getGenerators({ limit: 100 }),
    ])
    batteries = batteriesData.items
    generators = generatorsData.items
  } catch (err) {
    error = err instanceof Error ? err.message : 'Failed to load assets'
    console.error('Error loading assets:', err)
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Asset Management</h1>
          <p className="text-gray-600 mt-2">
            Manage and monitor your energy assets
          </p>
        </div>
        <Link
          href="/assets"
          className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Link>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Assets</p>
              <p className="text-2xl font-bold text-gray-900">{batteries.length + generators.length}</p>
            </div>
            <Activity className="h-8 w-8 text-primary-600" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Batteries</p>
              <p className="text-2xl font-bold text-gray-900">{batteries.length}</p>
            </div>
            <Battery className="h-8 w-8 text-blue-600" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Generators</p>
              <p className="text-2xl font-bold text-gray-900">{generators.length}</p>
            </div>
            <Zap className="h-8 w-8 text-amber-600" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Active</p>
              <p className="text-2xl font-bold text-gray-900">
                {[...batteries, ...generators].filter((a) => a.status === 'active').length}
              </p>
            </div>
            <div className="h-3 w-3 bg-green-500 rounded-full" />
          </div>
        </div>
      </div>

      {/* Client-side tabs and asset lists */}
      <AssetsClient 
        initialBatteries={batteries}
        initialGenerators={generators}
        initialError={error}
      />
    </div>
  )
}
