using System.ComponentModel.DataAnnotations;
using NodaTime;

namespace OmarinoEms.SchedulerService.Models;

/// <summary>
/// Represents a workflow execution instance.
/// </summary>
public class WorkflowExecution
{
    [Key]
    public Guid Id { get; set; } = Guid.NewGuid();

    /// <summary>
    /// ID of the workflow definition.
    /// </summary>
    public Guid WorkflowId { get; set; }

    /// <summary>
    /// Workflow definition.
    /// </summary>
    public WorkflowDefinition? Workflow { get; set; }

    /// <summary>
    /// Execution status.
    /// </summary>
    public ExecutionStatus Status { get; set; } = ExecutionStatus.Pending;

    /// <summary>
    /// Task execution results.
    /// </summary>
    public List<TaskExecution> TaskExecutions { get; set; } = new();

    /// <summary>
    /// Overall execution result.
    /// </summary>
    public string? Result { get; set; }

    /// <summary>
    /// Error message if execution failed.
    /// </summary>
    public string? ErrorMessage { get; set; }

    /// <summary>
    /// How the execution was triggered.
    /// </summary>
    public TriggerType TriggerType { get; set; }

    /// <summary>
    /// User or system that triggered the execution.
    /// </summary>
    public string? TriggeredBy { get; set; }

    public Instant CreatedAt { get; set; } = SystemClock.Instance.GetCurrentInstant();
    public Instant? StartedAt { get; set; }
    public Instant? CompletedAt { get; set; }

    /// <summary>
    /// Total execution duration.
    /// </summary>
    public Duration? Duration => StartedAt.HasValue && CompletedAt.HasValue
        ? CompletedAt.Value - StartedAt.Value
        : null;
}

/// <summary>
/// Represents a task execution within a workflow execution.
/// </summary>
public class TaskExecution
{
    [Key]
    public Guid Id { get; set; } = Guid.NewGuid();

    /// <summary>
    /// ID of the workflow execution.
    /// </summary>
    public Guid ExecutionId { get; set; }

    /// <summary>
    /// ID of the task definition.
    /// </summary>
    public Guid TaskId { get; set; }

    /// <summary>
    /// Task name (denormalized for convenience).
    /// </summary>
    public string TaskName { get; set; } = string.Empty;

    /// <summary>
    /// Task execution status.
    /// </summary>
    public ExecutionStatus Status { get; set; } = ExecutionStatus.Pending;

    /// <summary>
    /// Task result (JSON).
    /// </summary>
    public string? Result { get; set; }

    /// <summary>
    /// Error message if task failed.
    /// </summary>
    public string? ErrorMessage { get; set; }

    /// <summary>
    /// Number of times this task has been retried.
    /// </summary>
    public int RetryCount { get; set; } = 0;

    public Instant CreatedAt { get; set; } = SystemClock.Instance.GetCurrentInstant();
    public Instant? StartedAt { get; set; }
    public Instant? CompletedAt { get; set; }

    /// <summary>
    /// Task execution duration.
    /// </summary>
    public Duration? Duration => StartedAt.HasValue && CompletedAt.HasValue
        ? CompletedAt.Value - StartedAt.Value
        : null;
}

/// <summary>
/// Execution status.
/// </summary>
public enum ExecutionStatus
{
    Pending,    // Not yet started
    Running,    // Currently executing
    Completed,  // Successfully completed
    Failed,     // Failed with error
    Cancelled,  // Cancelled by user
    TimedOut    // Exceeded maximum execution time
}

/// <summary>
/// How a workflow execution was triggered.
/// </summary>
public enum TriggerType
{
    Scheduled,  // Triggered by scheduler (cron/interval)
    Manual,     // Manually triggered by user
    Webhook,    // Triggered by webhook
    Api         // Triggered via API
}
