using Microsoft.EntityFrameworkCore;
using NodaTime;
using OmarinoEms.SchedulerService.Data;
using OmarinoEms.SchedulerService.Models;

namespace OmarinoEms.SchedulerService.Services;

/// <summary>
/// Workflow engine for executing workflows.
/// </summary>
public class WorkflowEngine : IWorkflowEngine
{
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly ILogger<WorkflowEngine> _logger;
    private readonly Dictionary<Guid, CancellationTokenSource> _runningExecutions = new();

    public WorkflowEngine(
        IServiceScopeFactory scopeFactory,
        ILogger<WorkflowEngine> logger)
    {
        _scopeFactory = scopeFactory;
        _logger = logger;
    }

    public async Task<WorkflowExecution> ExecuteWorkflowAsync(
        Guid workflowId,
        TriggerType triggerType,
        string? triggeredBy = null)
    {
        using var scope = _scopeFactory.CreateScope();
        var context = scope.ServiceProvider.GetRequiredService<SchedulerDbContext>();
        
        var workflow = await context.WorkflowDefinitions
            .FirstOrDefaultAsync(w => w.Id == workflowId);

        if (workflow == null)
        {
            throw new InvalidOperationException($"Workflow {workflowId} not found");
        }

        if (!workflow.IsEnabled)
        {
            throw new InvalidOperationException($"Workflow {workflow.Name} is disabled");
        }

        // Validate workflow
        var validation = await ValidateWorkflowAsync(workflow);
        if (!validation.IsValid)
        {
            throw new InvalidOperationException(
                $"Workflow validation failed: {string.Join(", ", validation.Errors)}");
        }

        // Create execution record
        var execution = new WorkflowExecution
        {
            WorkflowId = workflowId,
            Status = ExecutionStatus.Running,
            TriggerType = triggerType,
            TriggeredBy = triggeredBy,
            StartedAt = SystemClock.Instance.GetCurrentInstant()
        };

        context.WorkflowExecutions.Add(execution);
        await context.SaveChangesAsync();

        var executionId = execution.Id;

        _logger.LogInformation(
            "Starting workflow execution {ExecutionId} for workflow {WorkflowName}",
            executionId, workflow.Name);

        // Execute workflow in background with its own scope
        var cts = new CancellationTokenSource();
        _runningExecutions[executionId] = cts;

        _ = Task.Run(async () =>
        {
            using var bgScope = _scopeFactory.CreateScope();
            var bgContext = bgScope.ServiceProvider.GetRequiredService<SchedulerDbContext>();
            var executor = bgScope.ServiceProvider.GetRequiredService<IWorkflowExecutor>();
            
            // Reload workflow and execution in this scope
            var bgWorkflow = await bgContext.WorkflowDefinitions
                .FirstOrDefaultAsync(w => w.Id == workflowId);
            var bgExecution = await bgContext.WorkflowExecutions
                .FirstOrDefaultAsync(e => e.Id == executionId);
            
            if (bgWorkflow == null || bgExecution == null)
            {
                _logger.LogError("Could not reload workflow or execution for background task");
                return;
            }

            try
            {
                await executor.ExecuteAsync(bgWorkflow, bgExecution, cts.Token);
                
                bgExecution.Status = ExecutionStatus.Completed;
                bgExecution.CompletedAt = SystemClock.Instance.GetCurrentInstant();
                
                _logger.LogInformation(
                    "Workflow execution {ExecutionId} completed successfully in {Duration}",
                    executionId, bgExecution.Duration);
            }
            catch (OperationCanceledException)
            {
                bgExecution.Status = ExecutionStatus.Cancelled;
                bgExecution.CompletedAt = SystemClock.Instance.GetCurrentInstant();
                
                _logger.LogWarning("Workflow execution {ExecutionId} was cancelled", executionId);
            }
            catch (Exception ex)
            {
                bgExecution.Status = ExecutionStatus.Failed;
                bgExecution.ErrorMessage = ex.Message;
                bgExecution.CompletedAt = SystemClock.Instance.GetCurrentInstant();
                
                _logger.LogError(ex, "Workflow execution {ExecutionId} failed", executionId);
            }
            finally
            {
                await bgContext.SaveChangesAsync();
                _runningExecutions.Remove(executionId);
            }
        }, cts.Token);

        return execution;
    }

    public async Task CancelExecutionAsync(Guid executionId)
    {
        using var scope = _scopeFactory.CreateScope();
        var context = scope.ServiceProvider.GetRequiredService<SchedulerDbContext>();
        
        var execution = await context.WorkflowExecutions
            .FirstOrDefaultAsync(e => e.Id == executionId);

        if (execution == null)
        {
            throw new InvalidOperationException($"Execution {executionId} not found");
        }

        if (execution.Status != ExecutionStatus.Running)
        {
            throw new InvalidOperationException(
                $"Cannot cancel execution in status {execution.Status}");
        }

        if (_runningExecutions.TryGetValue(executionId, out var cts))
        {
            cts.Cancel();
            _logger.LogInformation("Cancellation requested for execution {ExecutionId}", executionId);
        }
    }

    public async Task<WorkflowExecution?> GetExecutionStatusAsync(Guid executionId)
    {
        using var scope = _scopeFactory.CreateScope();
        var context = scope.ServiceProvider.GetRequiredService<SchedulerDbContext>();
        
        return await context.WorkflowExecutions
            .Include(e => e.TaskExecutions)
            .Include(e => e.Workflow)
            .FirstOrDefaultAsync(e => e.Id == executionId);
    }

    public Task<ValidationResult> ValidateWorkflowAsync(WorkflowDefinition workflow)
    {
        var result = new ValidationResult { IsValid = true };

        if (workflow.Tasks.Count == 0)
        {
            result.IsValid = false;
            result.Errors.Add("Workflow must contain at least one task");
            return Task.FromResult(result);
        }

        // Check for duplicate task IDs
        var taskIds = workflow.Tasks.Select(t => t.Id).ToList();
        if (taskIds.Count != taskIds.Distinct().Count())
        {
            result.IsValid = false;
            result.Errors.Add("Workflow contains duplicate task IDs");
        }

        // Check for invalid dependencies
        foreach (var task in workflow.Tasks)
        {
            foreach (var dep in task.DependsOn)
            {
                if (!taskIds.Contains(dep))
                {
                    result.IsValid = false;
                    result.Errors.Add($"Task {task.Name} depends on non-existent task {dep}");
                }
            }
        }

        // Check for cycles using DFS
        if (HasCycle(workflow.Tasks))
        {
            result.IsValid = false;
            result.Errors.Add("Workflow contains a cycle (circular dependency)");
        }

        // Validate task configurations
        foreach (var task in workflow.Tasks)
        {
            switch (task.Type)
            {
                case TaskType.HttpCall:
                    if (!task.Config.ContainsKey("url"))
                    {
                        result.IsValid = false;
                        result.Errors.Add($"Task {task.Name}: HttpCall requires 'url' in config");
                    }
                    break;
                case TaskType.Delay:
                    if (!task.Config.ContainsKey("duration"))
                    {
                        result.IsValid = false;
                        result.Errors.Add($"Task {task.Name}: Delay requires 'duration' in config");
                    }
                    break;
            }
        }

        return Task.FromResult(result);
    }

    private bool HasCycle(List<WorkflowTask> tasks)
    {
        var visited = new HashSet<Guid>();
        var recursionStack = new HashSet<Guid>();

        foreach (var task in tasks)
        {
            if (HasCycleDFS(task, tasks, visited, recursionStack))
            {
                return true;
            }
        }

        return false;
    }

    private bool HasCycleDFS(
        WorkflowTask task,
        List<WorkflowTask> allTasks,
        HashSet<Guid> visited,
        HashSet<Guid> recursionStack)
    {
        if (recursionStack.Contains(task.Id))
        {
            return true;
        }

        if (visited.Contains(task.Id))
        {
            return false;
        }

        visited.Add(task.Id);
        recursionStack.Add(task.Id);

        foreach (var depId in task.DependsOn)
        {
            var depTask = allTasks.FirstOrDefault(t => t.Id == depId);
            if (depTask != null && HasCycleDFS(depTask, allTasks, visited, recursionStack))
            {
                return true;
            }
        }

        recursionStack.Remove(task.Id);
        return false;
    }
}
