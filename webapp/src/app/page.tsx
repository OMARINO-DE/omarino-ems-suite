import Link from 'next/link'
import { Activity, BarChart3, Zap, Clock } from 'lucide-react'

export default function Home() {
  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Welcome to OMARINO EMS
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          Comprehensive energy management and optimization platform for renewable energy systems
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <DashboardCard
          title="Dashboard"
          description="Real-time monitoring and analytics"
          icon={<Activity className="h-8 w-8" />}
          href="/dashboard"
          color="bg-blue-500"
        />
        <DashboardCard
          title="Time Series"
          description="Historical data and trends"
          icon={<BarChart3 className="h-8 w-8" />}
          href="/timeseries"
          color="bg-green-500"
        />
        <DashboardCard
          title="Forecasts"
          description="Energy demand predictions"
          icon={<Zap className="h-8 w-8" />}
          href="/forecasts"
          color="bg-purple-500"
        />
        <DashboardCard
          title="Optimization"
          description="Battery and asset optimization"
          icon={<Zap className="h-8 w-8" />}
          href="/optimization"
          color="bg-orange-500"
        />
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-semibold mb-4">System Overview</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard label="Active Meters" value="24" change="+2" />
          <StatCard label="Total Series" value="156" change="+12" />
          <StatCard label="Active Workflows" value="8" change="+1" />
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-semibold mb-4">Quick Actions</h2>
        <div className="space-y-2">
          <QuickAction
            title="Run Forecast"
            description="Generate new energy demand forecast"
            href="/forecasts/new"
          />
          <QuickAction
            title="Start Optimization"
            description="Optimize battery dispatch schedule"
            href="/optimization/new"
          />
          <QuickAction
            title="Create Workflow"
            description="Set up automated workflow"
            href="/scheduler/workflows/new"
          />
        </div>
      </div>
    </div>
  )
}

interface DashboardCardProps {
  title: string
  description: string
  icon: React.ReactNode
  href: string
  color: string
}

function DashboardCard({ title, description, icon, href, color }: DashboardCardProps) {
  return (
    <Link href={href}>
      <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow cursor-pointer">
        <div className={`${color} text-white w-12 h-12 rounded-lg flex items-center justify-center mb-4`}>
          {icon}
        </div>
        <h3 className="text-lg font-semibold mb-2">{title}</h3>
        <p className="text-gray-600 text-sm">{description}</p>
      </div>
    </Link>
  )
}

interface StatCardProps {
  label: string
  value: string
  change: string
}

function StatCard({ label, value, change }: StatCardProps) {
  const isPositive = change.startsWith('+')
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <p className="text-sm text-gray-600 mb-1">{label}</p>
      <div className="flex items-baseline gap-2">
        <p className="text-3xl font-bold">{value}</p>
        <span className={`text-sm ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
          {change}
        </span>
      </div>
    </div>
  )
}

interface QuickActionProps {
  title: string
  description: string
  href: string
}

function QuickAction({ title, description, href }: QuickActionProps) {
  return (
    <Link href={href}>
      <div className="flex items-center justify-between p-4 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer border border-gray-200">
        <div>
          <h4 className="font-medium">{title}</h4>
          <p className="text-sm text-gray-600">{description}</p>
        </div>
        <Clock className="h-5 w-5 text-gray-400" />
      </div>
    </Link>
  )
}
