import { Metadata } from 'next'
import { OptimizationClient } from '@/components/optimization/OptimizationClient'
import { serverApi } from '@/lib/api'

export const metadata: Metadata = {
  title: 'Optimization | OMARINO EMS',
  description: 'Energy cost optimization and scheduling',
}

export default async function OptimizationPage() {
  let optimizations = []
  let types = []
  
  try {
    const results = await Promise.all([
      serverApi.optimization.listOptimizations({ limit: 20 }),
      serverApi.optimization.listTypes()
    ])
    optimizations = results[0]
    types = results[1]
  } catch (error) {
    console.error('Failed to load optimization data:', error)
  }
  
  return <OptimizationClient initialOptimizations={optimizations} initialTypes={types} />
}
