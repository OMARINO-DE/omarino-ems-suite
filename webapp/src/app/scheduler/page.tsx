import { Metadata } from 'next'
import { SchedulerClient } from '@/components/scheduler/SchedulerClient'
import { serverApi } from '@/lib/api'

export const metadata: Metadata = {
  title: 'Scheduler | OMARINO EMS',
  description: 'Automated workflows and task scheduling',
}

export default async function SchedulerPage() {
  let workflows = []
  let executions = []
  
  try {
    const results = await Promise.all([
      serverApi.scheduler.getWorkflows(),
      serverApi.scheduler.getExecutions({ limit: 20 })
    ])
    workflows = results[0]
    executions = results[1]
  } catch (error) {
    console.error('Failed to load scheduler data:', error)
  }
  
  return <SchedulerClient initialWorkflows={workflows} initialExecutions={executions} />
}
