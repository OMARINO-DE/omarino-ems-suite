'use client'

import { useEffect, useState } from 'react'
import useSWR from 'swr'
import { api } from '@/lib/api'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Activity, TrendingUp, Zap, Battery } from 'lucide-react'

export default function DashboardPage() {
  const { data: servicesHealth } = useSWR('/api/health/services', () => api.health.getServicesHealth())
  const { data: meters } = useSWR('/api/timeseries/meters', () => api.timeseries.getMeters())

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-2">Real-time overview of your energy management system</p>
      </div>

      {/* System Health */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {servicesHealth?.services?.map((service: any) => (
          <ServiceHealthCard key={service.name} service={service} />
        ))}
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard
          title="Total Energy"
          value="1,234 kWh"
          change="+12.5%"
          icon={<Zap className="h-6 w-6" />}
          color="text-yellow-600"
        />
        <MetricCard
          title="Peak Demand"
          value="245 kW"
          change="+5.2%"
          icon={<TrendingUp className="h-6 w-6" />}
          color="text-red-600"
        />
        <MetricCard
          title="Battery SOC"
          value="78%"
          change="-3.1%"
          icon={<Battery className="h-6 w-6" />}
          color="text-green-600"
        />
        <MetricCard
          title="Active Meters"
          value={meters?.length || 0}
          change="+2"
          icon={<Activity className="h-6 w-6" />}
          color="text-blue-600"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Energy Consumption (24h)</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={generateMockData(24)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="consumption" stroke="#0ea5e9" strokeWidth={2} />
              <Line type="monotone" dataKey="forecast" stroke="#8b5cf6" strokeWidth={2} strokeDasharray="5 5" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Battery Dispatch</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={generateMockBatteryData(24)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="charge" fill="#10b981" />
              <Bar dataKey="discharge" fill="#ef4444" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Recent Activity</h2>
        <div className="space-y-3">
          <ActivityItem
            title="Forecast completed"
            description="ARIMA model forecast for meter-001-load"
            time="5 minutes ago"
            status="success"
          />
          <ActivityItem
            title="Optimization started"
            description="Battery dispatch optimization for next 24 hours"
            time="12 minutes ago"
            status="running"
          />
          <ActivityItem
            title="Workflow triggered"
            description="Daily forecast and optimization workflow"
            time="1 hour ago"
            status="success"
          />
        </div>
      </div>
    </div>
  )
}

interface ServiceHealthCardProps {
  service: {
    name: string
    status: string
    responseTime: number
  }
}

function ServiceHealthCard({ service }: ServiceHealthCardProps) {
  const isHealthy = service.status === 'Healthy'
  return (
    <div className="bg-white rounded-lg shadow-md p-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-medium text-gray-900">{service.name}</h3>
        <span className={`w-3 h-3 rounded-full ${isHealthy ? 'bg-green-500' : 'bg-red-500'}`} />
      </div>
      <p className="text-sm text-gray-600">
        {service.responseTime}ms
      </p>
    </div>
  )
}

interface MetricCardProps {
  title: string
  value: string | number
  change: string
  icon: React.ReactNode
  color: string
}

function MetricCard({ title, value, change, icon, color }: MetricCardProps) {
  const isPositive = change.startsWith('+')
  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <div className={color}>{icon}</div>
        <span className={`text-sm font-medium ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
          {change}
        </span>
      </div>
      <h3 className="text-sm text-gray-600 mb-1">{title}</h3>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  )
}

interface ActivityItemProps {
  title: string
  description: string
  time: string
  status: 'success' | 'running' | 'failed'
}

function ActivityItem({ title, description, time, status }: ActivityItemProps) {
  const statusColors = {
    success: 'bg-green-100 text-green-800',
    running: 'bg-blue-100 text-blue-800',
    failed: 'bg-red-100 text-red-800',
  }

  return (
    <div className="flex items-start gap-4 p-3 rounded-lg hover:bg-gray-50">
      <div className={`px-2 py-1 rounded text-xs font-medium ${statusColors[status]}`}>
        {status}
      </div>
      <div className="flex-1">
        <h4 className="font-medium text-gray-900">{title}</h4>
        <p className="text-sm text-gray-600">{description}</p>
      </div>
      <span className="text-sm text-gray-500">{time}</span>
    </div>
  )
}

function generateMockData(hours: number) {
  return Array.from({ length: hours }, (_, i) => ({
    hour: `${i}:00`,
    consumption: Math.floor(Math.random() * 100 + 150),
    forecast: Math.floor(Math.random() * 100 + 140),
  }))
}

function generateMockBatteryData(hours: number) {
  return Array.from({ length: hours }, (_, i) => ({
    hour: `${i}:00`,
    charge: i % 3 === 0 ? Math.floor(Math.random() * 50 + 20) : 0,
    discharge: i % 3 === 1 ? Math.floor(Math.random() * 50 + 20) : 0,
  }))
}
