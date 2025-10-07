using Microsoft.Extensions.Diagnostics.HealthChecks;
using Quartz;

namespace OmarinoEms.SchedulerService.Services;

/// <summary>
/// Health check for Quartz.NET scheduler.
/// </summary>
public class QuartzHealthCheck : IHealthCheck
{
    private readonly ISchedulerFactory _schedulerFactory;

    public QuartzHealthCheck(ISchedulerFactory schedulerFactory)
    {
        _schedulerFactory = schedulerFactory;
    }

    public async Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context,
        CancellationToken cancellationToken = default)
    {
        try
        {
            var scheduler = await _schedulerFactory.GetScheduler(cancellationToken);
            
            if (scheduler.IsStarted)
            {
                var jobKeys = await scheduler.GetJobKeys(
                    Quartz.Impl.Matchers.GroupMatcher<JobKey>.AnyGroup(),
                    cancellationToken);

                return HealthCheckResult.Healthy(
                    $"Quartz scheduler is running with {jobKeys.Count} scheduled job(s)");
            }

            return HealthCheckResult.Degraded("Quartz scheduler is not started");
        }
        catch (Exception ex)
        {
            return HealthCheckResult.Unhealthy(
                "Quartz scheduler is not available",
                ex);
        }
    }
}
