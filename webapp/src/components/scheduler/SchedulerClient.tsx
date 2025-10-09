'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { api } from '@/lib/api'
import { Calendar, Clock, CheckCircle, XCircle, AlertCircle, Play, Plus, Edit, X } from 'lucide-react'

interface SchedulerClientProps {
  initialWorkflows: any[]
  initialExecutions: any[]
}

export function SchedulerClient({ initialWorkflows, initialExecutions }: SchedulerClientProps) {
  // Use server-side rendered data, with manual refresh capability
  const [workflows, setWorkflows] = useState(initialWorkflows)
  const [executions, setExecutions] = useState(initialExecutions)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [showNewWorkflow, setShowNewWorkflow] = useState(false)
  const [editingWorkflow, setEditingWorkflow] = useState<any>(null)
  const router = useRouter()

  const handleRefresh = () => {
    setIsRefreshing(true)
    router.refresh()
    setTimeout(() => setIsRefreshing(false), 1000)
  }

  useEffect(() => {
    setWorkflows(initialWorkflows)
    setExecutions(initialExecutions)
  }, [initialWorkflows, initialExecutions])

  const handleTriggerWorkflow = async (workflowId: string) => {
    try {
      await api.scheduler.triggerWorkflow(workflowId)
      // After triggering, refresh to see updates
      handleRefresh()
    } catch (error) {
      console.error('Failed to trigger workflow:', error)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Scheduler</h1>
          <p className="text-gray-600 mt-2">Automated workflows and task scheduling</p>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:bg-gray-400 flex items-center gap-2"
          >
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </button>
          <button 
            onClick={() => setShowNewWorkflow(true)}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            New Workflow
          </button>
        </div>
      </div>

      {/* Workflows */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Workflows</h2>
        {!workflows || workflows.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Calendar className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No workflows yet. Create your first workflow to get started!</p>
          </div>
        ) : (
          <div className="space-y-4">
            {workflows.map((workflow: any) => (
              <WorkflowCard 
                key={workflow.workflow_id} 
                workflow={workflow}
                onEdit={() => setEditingWorkflow(workflow)}
                onTrigger={() => handleTriggerWorkflow(workflow.workflow_id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Recent Executions */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Recent Executions</h2>
        {!executions || executions.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Clock className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No executions yet.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {executions.map((execution: any) => (
              <ExecutionCard key={execution.execution_id} execution={execution} />
            ))}
          </div>
        )}
      </div>

      {/* Modals */}
      {showNewWorkflow && (
        <WorkflowModal 
          onClose={() => setShowNewWorkflow(false)}
          onSave={() => {
            setShowNewWorkflow(false)
            // Refresh page to see new workflow
            window.location.reload()
          }}
        />
      )}
      {editingWorkflow && (
        <WorkflowModal 
          workflow={editingWorkflow}
          onClose={() => setEditingWorkflow(null)}
          onSave={() => {
            setEditingWorkflow(null)
            // Refresh page to see updated workflow
            window.location.reload()
          }}
        />
      )}
    </div>
  )
}

function WorkflowCard({ workflow, onEdit, onTrigger }: { workflow: any; onEdit: () => void; onTrigger: () => void }) {
  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-lg">{workflow.name}</h3>
          {workflow.description && (
            <p className="text-sm text-gray-600 mt-1">{workflow.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          <button 
            onClick={onEdit}
            className="p-2 hover:bg-gray-100 rounded"
            title="Edit workflow"
          >
            <Edit className="h-4 w-4 text-gray-600" />
          </button>
          <button 
            onClick={onTrigger}
            className="p-2 hover:bg-green-100 rounded"
            title="Trigger workflow"
          >
            <Play className="h-4 w-4 text-green-600" />
          </button>
        </div>
      </div>
      <div className="flex gap-4 text-sm text-gray-600">
        {workflow.schedule && (
          <div className="flex items-center gap-1">
            <Calendar className="h-4 w-4" />
            <span>{workflow.schedule}</span>
          </div>
        )}
        <div className="flex items-center gap-1">
          <span className={`px-2 py-0.5 rounded text-xs ${
            workflow.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
          }`}>
            {workflow.enabled ? 'Enabled' : 'Disabled'}
          </span>
        </div>
        {workflow.tasks && (
          <span>{workflow.tasks.length} task{workflow.tasks.length !== 1 ? 's' : ''}</span>
        )}
      </div>
    </div>
  )
}

function ExecutionCard({ execution }: { execution: any }) {
  const statusIcons = {
    completed: <CheckCircle className="h-5 w-5 text-green-600" />,
    failed: <XCircle className="h-5 w-5 text-red-600" />,
    running: <AlertCircle className="h-5 w-5 text-blue-600" />,
  }

  const statusColors = {
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    running: 'bg-blue-100 text-blue-800',
  }

  return (
    <div className="border border-gray-200 rounded-lg p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {statusIcons[execution.status as keyof typeof statusIcons]}
          <div>
            <div className="font-medium">{execution.workflow_name}</div>
            <div className="text-sm text-gray-600">
              {new Date(execution.started_at).toLocaleString()}
            </div>
          </div>
        </div>
        <span className={`px-2 py-1 text-xs rounded ${statusColors[execution.status as keyof typeof statusColors]}`}>
          {execution.status}
        </span>
      </div>
      {execution.error && (
        <div className="mt-2 text-sm text-red-600 bg-red-50 p-2 rounded">
          {execution.error}
        </div>
      )}
    </div>
  )
}

function WorkflowModal({ workflow, onClose, onSave }: { workflow?: any; onClose: () => void; onSave: () => void }) {
  const [formData, setFormData] = useState({
    name: workflow?.name || '',
    description: workflow?.description || '',
    schedule: workflow?.schedule || '',
    enabled: workflow?.enabled ?? true,
    tasks: workflow?.tasks || []
  })

  const [newTask, setNewTask] = useState({ type: 'forecast', config: {} })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (workflow) {
        await api.scheduler.updateWorkflow(workflow.workflow_id, formData)
      } else {
        await api.scheduler.createWorkflow(formData)
      }
      onSave()
    } catch (error) {
      console.error('Failed to save workflow:', error)
    }
  }

  const addTask = () => {
    setFormData({
      ...formData,
      tasks: [...formData.tasks, { ...newTask, order: formData.tasks.length }]
    })
    setNewTask({ type: 'forecast', config: {} })
  }

  const removeTask = (index: number) => {
    setFormData({
      ...formData,
      tasks: formData.tasks.filter((_: any, i: number) => i !== index)
    })
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">{workflow ? 'Edit' : 'New'} Workflow</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              rows={2}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Schedule (Cron Expression)</label>
            <input
              type="text"
              value={formData.schedule}
              onChange={(e) => setFormData({ ...formData, schedule: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              placeholder="0 * * * *"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={formData.enabled}
              onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
              className="rounded"
            />
            <label className="text-sm font-medium">Enabled</label>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Tasks</label>
            <div className="space-y-2 mb-3">
              {formData.tasks.map((task: any, index: number) => (
                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <div className="font-medium">{task.type}</div>
                    <div className="text-xs text-gray-600">Order: {task.order}</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeTask(index)}
                    className="p-1 hover:bg-gray-200 rounded"
                  >
                    <X className="h-4 w-4 text-red-600" />
                  </button>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <select
                value={newTask.type}
                onChange={(e) => setNewTask({ ...newTask, type: e.target.value })}
                className="px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="forecast">Forecast</option>
                <option value="optimization">Optimization</option>
                <option value="analysis">Analysis</option>
              </select>
              <button
                type="button"
                onClick={addTask}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
              >
                Add Task
              </button>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              {workflow ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
