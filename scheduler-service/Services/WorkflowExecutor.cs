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
                TaskType.Forecast => await ExecuteForecastAsync(task, cts.Token),
                TaskType.Optimization => await ExecuteOptimizationAsync(task, cts.Token),
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

    private async Task<object?> ExecuteForecastAsync(WorkflowTask task, CancellationToken cancellationToken)
    {
        var seriesId = task.Config.GetValueOrDefault("series_id", "").ToString();
        var horizon = Convert.ToInt32(task.Config.GetValueOrDefault("horizon", 24));
        var model = task.Config.GetValueOrDefault("model", "auto").ToString();
        var granularity = task.Config.GetValueOrDefault("granularity", "hourly").ToString();

        if (string.IsNullOrEmpty(seriesId))
        {
            throw new InvalidOperationException("series_id is required for Forecast task");
        }

        var client = _httpClientFactory.CreateClient();
        var request = new HttpRequestMessage(HttpMethod.Post, "http://forecast-service:8001/api/forecast/forecast");
        
        var requestBody = new
        {
            series_id = seriesId,
            horizon,
            model,
            granularity
        };

        request.Content = new StringContent(
            JsonSerializer.Serialize(requestBody),
            System.Text.Encoding.UTF8,
            "application/json");

        _logger.LogInformation("Generating forecast for series {SeriesId} with model {Model}, horizon {Horizon}",
            seriesId, model, horizon);

        var response = await client.SendAsync(request, cancellationToken);
        response.EnsureSuccessStatusCode();

        var content = await response.Content.ReadAsStringAsync(cancellationToken);
        var result = JsonSerializer.Deserialize<JsonElement>(content);

        return new
        {
            statusCode = (int)response.StatusCode,
            forecast_id = result.GetProperty("forecast_id").GetString(),
            series_id = seriesId,
            model = model,
            horizon = horizon
        };
    }

    private async Task<object?> ExecuteOptimizationAsync(WorkflowTask task, CancellationToken cancellationToken)
    {
        var optimizationType = task.Config.GetValueOrDefault("optimization_type", "battery_dispatch").ToString();
        
        if (string.IsNullOrEmpty(optimizationType))
        {
            throw new InvalidOperationException("optimization_type is required for Optimization task");
        }

        // Build optimization request from config
        var requestBody = new Dictionary<string, object>
        {
            ["optimization_type"] = optimizationType,
            ["objective"] = task.Config.GetValueOrDefault("objective", "minimize_cost"),
            ["start_time"] = task.Config.GetValueOrDefault("start_time", DateTime.UtcNow.ToString("o"))!,
            ["end_time"] = task.Config.GetValueOrDefault("end_time", DateTime.UtcNow.AddHours(24).ToString("o"))!,
            ["time_step_minutes"] = Convert.ToInt32(task.Config.GetValueOrDefault("time_step_minutes", 15)),
            ["solver"] = task.Config.GetValueOrDefault("solver", "cbc"),
            ["time_limit_seconds"] = Convert.ToInt32(task.Config.GetValueOrDefault("time_limit_seconds", 300)),
            ["mip_gap"] = Convert.ToDouble(task.Config.GetValueOrDefault("mip_gap", 0.01))
        };

        // Add assets if provided
        if (task.Config.ContainsKey("assets"))
        {
            requestBody["assets"] = task.Config["assets"];
        }

        // Add prices if provided
        if (task.Config.ContainsKey("import_prices"))
        {
            requestBody["import_prices"] = task.Config["import_prices"];
        }
        if (task.Config.ContainsKey("export_prices"))
        {
            requestBody["export_prices"] = task.Config["export_prices"];
        }

        // Add forecasts if provided
        if (task.Config.ContainsKey("load_forecast"))
        {
            requestBody["load_forecast"] = task.Config["load_forecast"];
        }
        if (task.Config.ContainsKey("solar_forecast"))
        {
            requestBody["solar_forecast"] = task.Config["solar_forecast"];
        }
        if (task.Config.ContainsKey("wind_forecast"))
        {
            requestBody["wind_forecast"] = task.Config["wind_forecast"];
        }

        // Add constraints if provided
        if (task.Config.ContainsKey("constraints"))
        {
            requestBody["constraints"] = task.Config["constraints"];
        }

        var client = _httpClientFactory.CreateClient();
        var request = new HttpRequestMessage(HttpMethod.Post, "http://optimize-service:8002/api/optimize/optimize");

        request.Content = new StringContent(
            JsonSerializer.Serialize(requestBody),
            System.Text.Encoding.UTF8,
            "application/json");

        _logger.LogInformation("Running {OptimizationType} optimization", optimizationType);

        var response = await client.SendAsync(request, cancellationToken);
        response.EnsureSuccessStatusCode();

        var content = await response.Content.ReadAsStringAsync(cancellationToken);
        var result = JsonSerializer.Deserialize<JsonElement>(content);

        return new
        {
            statusCode = (int)response.StatusCode,
            optimization_id = result.GetProperty("optimization_id").GetString(),
            optimization_type = optimizationType,
            status = result.GetProperty("status").GetString()
        };
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
