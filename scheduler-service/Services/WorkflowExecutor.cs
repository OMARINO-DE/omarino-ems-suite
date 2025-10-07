using System.Text.Json;
using NodaTime;
using OmarinoEms.SchedulerService.Data;
using OmarinoEms.SchedulerService.Models;

namespace OmarinoEms.SchedulerService.Services;

/// <summary>
/// Executes workflow tasks in topologically sorted order.
/// </summary>
public class WorkflowExecutor : IWorkflowExecutor
{
    private readonly SchedulerDbContext _context;
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly ILogger<WorkflowExecutor> _logger;

    public WorkflowExecutor(
        SchedulerDbContext context,
        IHttpClientFactory httpClientFactory,
        ILogger<WorkflowExecutor> logger)
    {
        _context = context;
        _httpClientFactory = httpClientFactory;
        _logger = logger;
    }

    public async Task ExecuteAsync(
        WorkflowDefinition workflow,
        WorkflowExecution execution,
        CancellationToken cancellationToken)
    {
        _logger.LogInformation("Executing workflow {WorkflowName} (execution {ExecutionId})",
            workflow.Name, execution.Id);

        // Topologically sort tasks based on dependencies
        var sortedTasks = TopologicalSort(workflow.Tasks);

        var completedTasks = new HashSet<Guid>();
        var taskResults = new Dictionary<Guid, object?>();

        foreach (var task in sortedTasks)
        {
            cancellationToken.ThrowIfCancellationRequested();

            // Check if dependencies are satisfied
            var depsFailed = task.DependsOn.Any(depId => !completedTasks.Contains(depId));
            if (depsFailed)
            {
                _logger.LogWarning("Task {TaskName} skipped due to failed dependencies", task.Name);
                continue;
            }

            // Execute task
            var taskExecution = new TaskExecution
            {
                ExecutionId = execution.Id,
                TaskId = task.Id,
                TaskName = task.Name,
                Status = ExecutionStatus.Running,
                StartedAt = SystemClock.Instance.GetCurrentInstant()
            };

            execution.TaskExecutions.Add(taskExecution);
            await _context.SaveChangesAsync(cancellationToken);

            try
            {
                var result = await ExecuteTaskAsync(task, taskResults, cancellationToken);
                
                taskExecution.Status = ExecutionStatus.Completed;
                taskExecution.Result = JsonSerializer.Serialize(result);
                taskExecution.CompletedAt = SystemClock.Instance.GetCurrentInstant();
                
                completedTasks.Add(task.Id);
                taskResults[task.Id] = result;
                
                _logger.LogInformation("Task {TaskName} completed in {Duration}ms",
                    task.Name, taskExecution.Duration?.TotalMilliseconds);
            }
            catch (Exception ex)
            {
                taskExecution.Status = ExecutionStatus.Failed;
                taskExecution.ErrorMessage = ex.Message;
                taskExecution.CompletedAt = SystemClock.Instance.GetCurrentInstant();
                
                _logger.LogError(ex, "Task {TaskName} failed", task.Name);

                // Retry logic
                if (taskExecution.RetryCount < workflow.MaxRetries)
                {
                    taskExecution.RetryCount++;
                    _logger.LogInformation("Retrying task {TaskName} (attempt {RetryCount}/{MaxRetries})",
                        task.Name, taskExecution.RetryCount, workflow.MaxRetries);
                    
                    await Task.Delay(TimeSpan.FromSeconds(30), cancellationToken);
                    // TODO: Implement retry
                }

                if (!task.ContinueOnError)
                {
                    throw;
                }
            }
            finally
            {
                await _context.SaveChangesAsync(cancellationToken);
            }
        }

        execution.Result = JsonSerializer.Serialize(new
        {
            completedTasks = completedTasks.Count,
            totalTasks = workflow.Tasks.Count,
            results = taskResults
        });
    }

    private async Task<object?> ExecuteTaskAsync(
        WorkflowTask task,
        Dictionary<Guid, object?> previousResults,
        CancellationToken cancellationToken)
    {
        _logger.LogDebug("Executing task {TaskName} of type {TaskType}", task.Name, task.Type);

        using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        cts.CancelAfter(task.Timeout);

        try
        {
            return task.Type switch
            {
                TaskType.HttpCall => await ExecuteHttpCallAsync(task, cts.Token),
                TaskType.Delay => await ExecuteDelayAsync(task, cts.Token),
                TaskType.Condition => ExecuteCondition(task, previousResults),
                TaskType.Transform => ExecuteTransform(task, previousResults),
                TaskType.Notification => await ExecuteNotificationAsync(task, cts.Token),
                _ => throw new NotImplementedException($"Task type {task.Type} not implemented")
            };
        }
        catch (OperationCanceledException) when (cts.IsCancellationRequested && !cancellationToken.IsCancellationRequested)
        {
            throw new TimeoutException($"Task {task.Name} timed out after {task.Timeout}");
        }
    }

    private async Task<object?> ExecuteHttpCallAsync(WorkflowTask task, CancellationToken cancellationToken)
    {
        var url = task.Config["url"].ToString();
        var method = task.Config.GetValueOrDefault("method", "GET").ToString();
        var headers = task.Config.GetValueOrDefault("headers", new Dictionary<string, string>()) as Dictionary<string, string>;
        var body = task.Config.GetValueOrDefault("body", null);

        if (string.IsNullOrEmpty(url))
        {
            throw new InvalidOperationException("URL is required for HttpCall task");
        }

        var client = _httpClientFactory.CreateClient();
        var request = new HttpRequestMessage(new HttpMethod(method!), url);

        if (headers != null)
        {
            foreach (var header in headers)
            {
                request.Headers.Add(header.Key, header.Value);
            }
        }

        if (body != null)
        {
            request.Content = new StringContent(
                JsonSerializer.Serialize(body),
                System.Text.Encoding.UTF8,
                "application/json");
        }

        _logger.LogDebug("Sending {Method} request to {Url}", method, url);
        
        var response = await client.SendAsync(request, cancellationToken);
        response.EnsureSuccessStatusCode();

        var content = await response.Content.ReadAsStringAsync(cancellationToken);
        
        return new
        {
            statusCode = (int)response.StatusCode,
            body = content,
            headers = response.Headers.ToDictionary(h => h.Key, h => string.Join(", ", h.Value))
        };
    }

    private async Task<object?> ExecuteDelayAsync(WorkflowTask task, CancellationToken cancellationToken)
    {
        var durationSeconds = Convert.ToInt32(task.Config["duration"]);
        
        _logger.LogDebug("Delaying for {Seconds} seconds", durationSeconds);
        
        await Task.Delay(TimeSpan.FromSeconds(durationSeconds), cancellationToken);
        
        return new { delayed = durationSeconds };
    }

    private object? ExecuteCondition(WorkflowTask task, Dictionary<Guid, object?> previousResults)
    {
        // Simple condition evaluation
        var condition = task.Config["condition"].ToString();
        
        _logger.LogDebug("Evaluating condition: {Condition}", condition);
        
        // TODO: Implement proper expression evaluation
        return new { condition, result = true };
    }

    private object? ExecuteTransform(WorkflowTask task, Dictionary<Guid, object?> previousResults)
    {
        // Data transformation
        var transform = task.Config["transform"].ToString();
        
        _logger.LogDebug("Applying transform: {Transform}", transform);
        
        // TODO: Implement data transformation logic
        return new { transform, result = "transformed" };
    }

    private async Task<object?> ExecuteNotificationAsync(WorkflowTask task, CancellationToken cancellationToken)
    {
        var type = task.Config.GetValueOrDefault("type", "log").ToString();
        var message = task.Config["message"].ToString();
        
        _logger.LogInformation("Notification ({Type}): {Message}", type, message);
        
        // TODO: Implement actual notification sending (email, webhook, etc.)
        await Task.CompletedTask;
        
        return new { type, message, sent = true };
    }

    private List<WorkflowTask> TopologicalSort(List<WorkflowTask> tasks)
    {
        var sorted = new List<WorkflowTask>();
        var visited = new HashSet<Guid>();

        void Visit(WorkflowTask task)
        {
            if (visited.Contains(task.Id))
                return;

            visited.Add(task.Id);

            foreach (var depId in task.DependsOn)
            {
                var depTask = tasks.FirstOrDefault(t => t.Id == depId);
                if (depTask != null)
                {
                    Visit(depTask);
                }
            }

            sorted.Add(task);
        }

        foreach (var task in tasks)
        {
            Visit(task);
        }

        return sorted;
    }
}
