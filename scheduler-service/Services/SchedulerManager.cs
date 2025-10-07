using Quartz;

namespace OmarinoEms.SchedulerService.Services;

/// <summary>
/// Interface for managing Quartz.NET scheduler operations.
/// </summary>
public interface ISchedulerManager
{
    /// <summary>
    /// Schedules a workflow based on its schedule configuration.
    /// </summary>
    Task ScheduleWorkflowAsync(Guid workflowId, string cronExpression, string timeZone);

    /// <summary>
    /// Unschedules a workflow.
    /// </summary>
    Task UnscheduleWorkflowAsync(Guid workflowId);

    /// <summary>
    /// Gets all scheduled jobs.
    /// </summary>
    Task<List<ScheduledJobInfo>> GetScheduledJobsAsync();

    /// <summary>
    /// Triggers a job immediately.
    /// </summary>
    Task TriggerJobAsync(Guid workflowId);
}

/// <summary>
/// Information about a scheduled job.
/// </summary>
public class ScheduledJobInfo
{
    public Guid WorkflowId { get; set; }
    public string JobKey { get; set; } = string.Empty;
    public string? CronExpression { get; set; }
    public DateTimeOffset? NextFireTime { get; set; }
    public DateTimeOffset? PreviousFireTime { get; set; }
}

/// <summary>
/// Manages Quartz.NET scheduler operations.
/// </summary>
public class SchedulerManager : ISchedulerManager
{
    private readonly ISchedulerFactory _schedulerFactory;
    private readonly ILogger<SchedulerManager> _logger;

    public SchedulerManager(ISchedulerFactory schedulerFactory, ILogger<SchedulerManager> logger)
    {
        _schedulerFactory = schedulerFactory;
        _logger = logger;
    }

    public async Task ScheduleWorkflowAsync(Guid workflowId, string cronExpression, string timeZone)
    {
        var scheduler = await _schedulerFactory.GetScheduler();

        var jobKey = new JobKey($"workflow-{workflowId}", "workflows");
        
        // Check if job already exists
        if (await scheduler.CheckExists(jobKey))
        {
            await scheduler.DeleteJob(jobKey);
        }

        var job = JobBuilder.Create<WorkflowJob>()
            .WithIdentity(jobKey)
            .UsingJobData("workflowId", workflowId.ToString())
            .Build();

        var trigger = TriggerBuilder.Create()
            .WithIdentity($"trigger-{workflowId}", "workflows")
            .WithCronSchedule(cronExpression, x => x.InTimeZone(TimeZoneInfo.FindSystemTimeZoneById(timeZone)))
            .Build();

        await scheduler.ScheduleJob(job, trigger);
        
        _logger.LogInformation("Scheduled workflow {WorkflowId} with cron expression: {CronExpression}",
            workflowId, cronExpression);
    }

    public async Task UnscheduleWorkflowAsync(Guid workflowId)
    {
        var scheduler = await _schedulerFactory.GetScheduler();
        var jobKey = new JobKey($"workflow-{workflowId}", "workflows");

        if (await scheduler.CheckExists(jobKey))
        {
            await scheduler.DeleteJob(jobKey);
            _logger.LogInformation("Unscheduled workflow {WorkflowId}", workflowId);
        }
    }

    public async Task<List<ScheduledJobInfo>> GetScheduledJobsAsync()
    {
        var scheduler = await _schedulerFactory.GetScheduler();
        var jobInfos = new List<ScheduledJobInfo>();

        var jobKeys = await scheduler.GetJobKeys(Quartz.Impl.Matchers.GroupMatcher<JobKey>.GroupEquals("workflows"));

        foreach (var jobKey in jobKeys)
        {
            var triggers = await scheduler.GetTriggersOfJob(jobKey);
            var trigger = triggers.FirstOrDefault();

            if (trigger != null)
            {
                var workflowId = Guid.Parse(jobKey.Name.Replace("workflow-", ""));
                
                jobInfos.Add(new ScheduledJobInfo
                {
                    WorkflowId = workflowId,
                    JobKey = jobKey.ToString(),
                    CronExpression = trigger is ICronTrigger cronTrigger ? cronTrigger.CronExpressionString : null,
                    NextFireTime = trigger.GetNextFireTimeUtc(),
                    PreviousFireTime = trigger.GetPreviousFireTimeUtc()
                });
            }
        }

        return jobInfos;
    }

    public async Task TriggerJobAsync(Guid workflowId)
    {
        var scheduler = await _schedulerFactory.GetScheduler();
        var jobKey = new JobKey($"workflow-{workflowId}", "workflows");

        if (await scheduler.CheckExists(jobKey))
        {
            await scheduler.TriggerJob(jobKey);
            _logger.LogInformation("Triggered workflow {WorkflowId} immediately", workflowId);
        }
        else
        {
            throw new InvalidOperationException($"Workflow {workflowId} is not scheduled");
        }
    }
}

/// <summary>
/// Quartz job that executes a workflow.
/// </summary>
public class WorkflowJob : IJob
{
    private readonly IWorkflowEngine _workflowEngine;
    private readonly ILogger<WorkflowJob> _logger;

    public WorkflowJob(IWorkflowEngine workflowEngine, ILogger<WorkflowJob> logger)
    {
        _workflowEngine = workflowEngine;
        _logger = logger;
    }

    public async Task Execute(IJobExecutionContext context)
    {
        var workflowId = Guid.Parse(context.JobDetail.JobDataMap.GetString("workflowId")!);
        
        _logger.LogInformation("Quartz job executing workflow {WorkflowId}", workflowId);

        try
        {
            await _workflowEngine.ExecuteWorkflowAsync(workflowId, Models.TriggerType.Scheduled, "Quartz Scheduler");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error executing workflow {WorkflowId} from Quartz job", workflowId);
            throw;
        }
    }
}
