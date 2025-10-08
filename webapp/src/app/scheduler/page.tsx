'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { api } from '@/lib/api'
import { Clock, Play, Pause, Trash2, Plus, X, Edit } from 'lucide-react'

export default function SchedulerPage() {
  const { data: workflows, mutate } = useSWR('/api/workflows', async () => {
    try {
      return await api.scheduler.getWorkflows()
    } catch (e) {
      return []
    }
  }, {
    revalidateOnFocus: false,
    shouldRetryOnError: false
  })
  const { data: executions } = useSWR('/api/executions', async () => {
    try {
      return await api.scheduler.getExecutions({ limit: 20 })
    } catch (e) {
      return []
    }
  }, {
    revalidateOnFocus: false,
    shouldRetryOnError: false
  })
  const [showNewWorkflowModal, setShowNewWorkflowModal] = useState(false)
  const [editingWorkflow, setEditingWorkflow] = useState<any | null>(null)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Scheduler</h1>
          <p className="text-gray-600 mt-2">Workflow automation and scheduling</p>
        </div>
        <button 
          onClick={() => setShowNewWorkflowModal(true)}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          New Workflow
        </button>
      </div>

      {showNewWorkflowModal && (
        <NewWorkflowModal 
          onClose={() => setShowNewWorkflowModal(false)}
          onSuccess={() => {
            mutate()
            setShowNewWorkflowModal(false)
          }}
        />
      )}

      {editingWorkflow && (
        <EditWorkflowModal 
          workflow={editingWorkflow}
          onClose={() => setEditingWorkflow(null)}
          onSuccess={() => {
            mutate()
            setEditingWorkflow(null)
          }}
        />
      )}

      {/* Workflows */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Active Workflows</h2>
        <div className="space-y-4">
          {workflows?.map((workflow: any) => (
            <WorkflowCard 
              key={workflow.id} 
              workflow={workflow} 
              onEdit={() => setEditingWorkflow(workflow)}
            />
          ))}
        </div>
      </div>

      {/* Recent Executions */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Recent Executions</h2>
        <div className="space-y-4">
          {executions?.map((execution: any) => (
            <ExecutionCard key={execution.id} execution={execution} />
          ))}
        </div>
      </div>
    </div>
  )
}

function WorkflowCard({ workflow, onEdit }: { workflow: any; onEdit: () => void }) {
  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-lg">{workflow.name}</h3>
          <p className="text-sm text-gray-600">{workflow.description}</p>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={onEdit}
            className="p-2 text-blue-600 hover:bg-blue-50 rounded"
            title="Edit workflow"
          >
            <Edit className="h-4 w-4" />
          </button>
          <button className="p-2 text-primary-600 hover:bg-primary-50 rounded">
            <Play className="h-4 w-4" />
          </button>
          <button className="p-2 text-red-600 hover:bg-red-50 rounded">
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
      <div className="flex items-center gap-4 text-sm text-gray-600">
        <div className="flex items-center gap-1">
          <Clock className="h-4 w-4" />
          <span>{workflow.schedule?.type || 'Manual'}</span>
        </div>
        <span className="text-gray-400">•</span>
        <span>{workflow.tasks?.length || 0} tasks</span>
      </div>
    </div>
  )
}

function ExecutionCard({ execution }: { execution: any }) {
  const statusColors = {
    pending: 'bg-gray-100 text-gray-800',
    running: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    cancelled: 'bg-orange-100 text-orange-800',
  }

  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold">Workflow Execution</h3>
          <p className="text-sm text-gray-600">{execution.workflowId}</p>
        </div>
        <span className={`px-2 py-1 text-xs rounded ${statusColors[execution.status as keyof typeof statusColors]}`}>
          {execution.status}
        </span>
      </div>
      {execution.startedAt && (
        <p className="text-sm text-gray-500 mt-2">
          Started: {new Date(execution.startedAt).toLocaleString()}
        </p>
      )}
    </div>
  )
}

function NewWorkflowModal({ 
  onClose, 
  onSuccess 
}: { 
  onClose: () => void
  onSuccess: () => void
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [scheduleType, setScheduleType] = useState<'manual' | 'cron'>('manual')
  const [cronExpression, setCronExpression] = useState('0 0 * * *')
  const [timezone, setTimezone] = useState('UTC')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!name.trim()) {
      alert('Please enter a workflow name')
      return
    }

    setIsSubmitting(true)
    try {
      const workflow = {
        name: name.trim(),
        description: description.trim(),
        isEnabled: true,
        tasks: [
          {
            id: crypto.randomUUID(),
            name: 'Example Task',
            type: 0,  // TaskType.HttpCall = 0
            dependsOn: [],
            config: {
              method: 'GET',
              url: 'http://example.com/api/health',
              headers: {}
            }
          }
        ],
        schedule: scheduleType === 'cron' ? {
          type: 0,  // ScheduleType.Cron = 0
          cronExpression: cronExpression,
          timeZone: timezone
        } : null
      }

      try {
        await api.scheduler.createWorkflow(workflow)
        alert('Workflow created successfully!')
        onSuccess()
      } catch (error: any) {
        const errorMessage = error.response?.data?.message || error.message || 'Unknown error'
        alert(`Failed to create workflow: ${errorMessage}`)
        console.error('Workflow creation error:', error)
      }
    } catch (error) {
      console.error('Workflow creation error:', error)
      alert('Failed to create workflow. Please check the console for details.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Create New Workflow</h2>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder="My Workflow"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder="What does this workflow do?"
              rows={3}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Schedule Type *
            </label>
            <select
              value={scheduleType}
              onChange={(e) => setScheduleType(e.target.value as 'manual' | 'cron')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="manual">Manual (No schedule)</option>
              <option value="cron">Cron Expression</option>
            </select>
          </div>

          {scheduleType === 'cron' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Cron Expression *
                </label>
                <input
                  type="text"
                  value={cronExpression}
                  onChange={(e) => setCronExpression(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm"
                  placeholder="0 0 * * *"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">
                  Example: "0 0 * * *" = Daily at midnight
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Timezone *
                </label>
                <input
                  type="text"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="UTC"
                  required
                />
              </div>
            </>
          )}

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-sm text-blue-800">
              <strong>Note:</strong> This will create a basic workflow with one example task. 
              You can edit and add more tasks after creation.
            </p>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Creating...' : 'Create Workflow'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function EditWorkflowModal({ 
  workflow,
  onClose, 
  onSuccess 
}: { 
  workflow: any
  onClose: () => void
  onSuccess: () => void
}) {
  const [name, setName] = useState(workflow.name || '')
  const [description, setDescription] = useState(workflow.description || '')
  const [isEnabled, setIsEnabled] = useState(workflow.isEnabled !== false)
  const [scheduleType, setScheduleType] = useState<'manual' | 'cron'>(
    workflow.schedule?.cronExpression ? 'cron' : 'manual'
  )
  const [cronExpression, setCronExpression] = useState(workflow.schedule?.cronExpression || '0 0 * * *')
  const [timezone, setTimezone] = useState(workflow.schedule?.timeZone || 'UTC')
  const [tasks, setTasks] = useState(workflow.tasks || [])
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleAddTask = () => {
    const newTask = {
      id: crypto.randomUUID(),
      name: 'New Task',
      type: 0,  // HttpCall
      dependsOn: [],
      config: {
        method: 'GET',
        url: 'http://example.com',
        headers: {}
      },
      timeout: '00:05:00',
      continueOnError: false
    }
    setTasks([...tasks, newTask])
  }

  const handleRemoveTask = (index: number) => {
    setTasks(tasks.filter((_: any, i: number) => i !== index))
  }

  const handleUpdateTask = (index: number, field: string, value: any) => {
    const updated = [...tasks]
    if (field === 'config.url' || field === 'config.method') {
      const configField = field.split('.')[1]
      updated[index] = {
        ...updated[index],
        config: { ...updated[index].config, [configField]: value }
      }
    } else {
      updated[index] = { ...updated[index], [field]: value }
    }
    setTasks(updated)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!name.trim()) {
      alert('Please enter a workflow name')
      return
    }

    if (tasks.length === 0) {
      alert('Please add at least one task')
      return
    }

    setIsSubmitting(true)
    try {
      const updatedWorkflow = {
        name: name.trim(),
        description: description.trim(),
        isEnabled: isEnabled,
        tasks: tasks,
        schedule: scheduleType === 'cron' ? {
          type: 0,  // ScheduleType.Cron = 0
          cronExpression: cronExpression,
          timeZone: timezone
        } : null,
        maxExecutionTime: workflow.maxExecutionTime || '01:00:00',
        maxRetries: workflow.maxRetries || 3,
        tags: workflow.tags || []
      }

      try {
        await api.scheduler.updateWorkflow(workflow.id, updatedWorkflow)
        alert('Workflow updated successfully!')
        onSuccess()
      } catch (error: any) {
        const errorMessage = error.response?.data?.message || error.message || 'Unknown error'
        alert(`Failed to update workflow: ${errorMessage}`)
        console.error('Workflow update error:', error)
      }
    } catch (error) {
      console.error('Workflow update error:', error)
      alert('Failed to update workflow. Please check the console for details.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Edit Workflow</h2>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <select
                value={isEnabled ? 'enabled' : 'disabled'}
                onChange={(e) => setIsEnabled(e.target.value === 'enabled')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="enabled">Enabled</option>
                <option value="disabled">Disabled</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              rows={2}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Schedule Type *
            </label>
            <select
              value={scheduleType}
              onChange={(e) => setScheduleType(e.target.value as 'manual' | 'cron')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="manual">Manual (No schedule)</option>
              <option value="cron">Cron Expression</option>
            </select>
          </div>

          {scheduleType === 'cron' && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Cron Expression *
                </label>
                <input
                  type="text"
                  value={cronExpression}
                  onChange={(e) => setCronExpression(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">
                  Example: "0 0 * * *" = Daily at midnight
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Timezone *
                </label>
                <input
                  type="text"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  required
                />
              </div>
            </div>
          )}

          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="block text-sm font-medium text-gray-700">
                Tasks ({tasks.length})
              </label>
              <button
                type="button"
                onClick={handleAddTask}
                className="px-3 py-1 text-sm bg-primary-600 text-white rounded hover:bg-primary-700 flex items-center gap-1"
              >
                <Plus className="h-3 w-3" />
                Add Task
              </button>
            </div>

            <div className="space-y-3 max-h-96 overflow-y-auto">
              {tasks.map((task: any, index: number) => (
                <div key={task.id} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1 grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Task Name
                        </label>
                        <input
                          type="text"
                          value={task.name}
                          onChange={(e) => handleUpdateTask(index, 'name', e.target.value)}
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Type
                        </label>
                        <select
                          value={task.type}
                          onChange={(e) => handleUpdateTask(index, 'type', parseInt(e.target.value))}
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        >
                          <option value="0">HTTP Call</option>
                          <option value="1">Delay</option>
                          <option value="2">Condition</option>
                          <option value="3">Transform</option>
                          <option value="4">Notification</option>
                        </select>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveTask(index)}
                      className="ml-2 p-1 text-red-600 hover:bg-red-50 rounded"
                      title="Remove task"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>

                  {task.type === 0 && (
                    <div className="grid grid-cols-3 gap-2">
                      <div className="col-span-2">
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          URL
                        </label>
                        <input
                          type="text"
                          value={task.config?.url || ''}
                          onChange={(e) => handleUpdateTask(index, 'config.url', e.target.value)}
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                          placeholder="http://example.com/api/endpoint"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Method
                        </label>
                        <select
                          value={task.config?.method || 'GET'}
                          onChange={(e) => handleUpdateTask(index, 'config.method', e.target.value)}
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        >
                          <option value="GET">GET</option>
                          <option value="POST">POST</option>
                          <option value="PUT">PUT</option>
                          <option value="DELETE">DELETE</option>
                        </select>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="flex gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
