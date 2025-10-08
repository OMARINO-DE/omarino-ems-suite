using System.ComponentModel.DataAnnotations;
using NodaTime;

namespace OmarinoEms.SchedulerService.Models;

/// <summary>
/// Represents a workflow definition (DAG).
/// </summary>
public class WorkflowDefinition
{
    [Key]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Required]
    [MaxLength(200)]
    public string Name { get; set; } = string.Empty;

    [MaxLength(1000)]
    public string? Description { get; set; }

    /// <summary>
    /// Workflow tasks (nodes in the DAG).
    /// </summary>
    public List<WorkflowTask> Tasks { get; set; } = new();

    /// <summary>
    /// Workflow schedule configuration.
    /// </summary>
    public WorkflowSchedule? Schedule { get; set; }

    /// <summary>
    /// Whether the workflow is enabled.
    /// </summary>
    public bool IsEnabled { get; set; } = true;

    /// <summary>
    /// Maximum execution time before timeout.
    /// </summary>
    public TimeSpan MaxExecutionTime { get; set; } = TimeSpan.FromHours(1);

    /// <summary>
    /// Number of times to retry failed tasks.
    /// </summary>
    public int MaxRetries { get; set; } = 3;

    /// <summary>
    /// Tags for categorization.
    /// </summary>
    public List<string> Tags { get; set; } = new();

    public Instant CreatedAt { get; set; } = SystemClock.Instance.GetCurrentInstant();
    public Instant UpdatedAt { get; set; } = SystemClock.Instance.GetCurrentInstant();
}

/// <summary>
/// Represents a task in a workflow (node in the DAG).
/// </summary>
public class WorkflowTask
{
    [Key]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Required]
    [MaxLength(200)]
    public string Name { get; set; } = string.Empty;

    /// <summary>
    /// Task type (http_call, delay, condition, etc.).
    /// </summary>
    [Required]
    public TaskType Type { get; set; }

    /// <summary>
    /// Task configuration (JSON).
    /// </summary>
    public Dictionary<string, object> Config { get; set; } = new();

    /// <summary>
    /// IDs of tasks that must complete before this task runs.
    /// </summary>
    public List<Guid> DependsOn { get; set; } = new();

    /// <summary>
    /// Timeout for this specific task.
    /// </summary>
    public TimeSpan Timeout { get; set; } = TimeSpan.FromMinutes(5);

    /// <summary>
    /// Whether to continue workflow if this task fails.
    /// </summary>
    public bool ContinueOnError { get; set; } = false;
}

/// <summary>
/// Types of workflow tasks.
/// </summary>
public enum TaskType
{
    HttpCall,       // Make an HTTP request
    Delay,          // Wait for a specified duration
    Condition,      // Conditional branching
    Transform,      // Data transformation
    Notification,   // Send notification (email, webhook, etc.)
    Forecast,       // Generate a forecast
    Optimization    // Run an optimization
}

/// <summary>
/// Workflow schedule configuration.
/// </summary>
public class WorkflowSchedule
{
    /// <summary>
    /// Schedule type (cron, interval, webhook).
    /// </summary>
    public ScheduleType Type { get; set; }

    /// <summary>
    /// Cron expression (for cron schedules).
    /// </summary>
    public string? CronExpression { get; set; }

    /// <summary>
    /// Interval in seconds (for interval schedules).
    /// </summary>
    public int? IntervalSeconds { get; set; }

    /// <summary>
    /// Timezone for cron schedules.
    /// </summary>
    public string TimeZone { get; set; } = "UTC";

    /// <summary>
    /// Start time for the schedule.
    /// </summary>
    public Instant? StartAt { get; set; }

    /// <summary>
    /// End time for the schedule.
    /// </summary>
    public Instant? EndAt { get; set; }
}

/// <summary>
/// Types of workflow schedules.
/// </summary>
public enum ScheduleType
{
    Cron,       // Cron-based schedule
    Interval,   // Fixed interval
    Webhook,    // Triggered by webhook
    Manual      // Manually triggered
}
