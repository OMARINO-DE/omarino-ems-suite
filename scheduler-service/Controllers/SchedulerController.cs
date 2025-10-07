using Microsoft.AspNetCore.Mvc;
using OmarinoEms.SchedulerService.Services;

namespace OmarinoEms.SchedulerService.Controllers;

/// <summary>
/// Controller for scheduler management and monitoring.
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class SchedulerController : ControllerBase
{
    private readonly ISchedulerManager _schedulerManager;
    private readonly ILogger<SchedulerController> _logger;

    public SchedulerController(ISchedulerManager schedulerManager, ILogger<SchedulerController> logger)
    {
        _schedulerManager = schedulerManager;
        _logger = logger;
    }

    /// <summary>
    /// Gets all scheduled jobs.
    /// </summary>
    [HttpGet("jobs")]
    [ProducesResponseType(typeof(List<ScheduledJobInfo>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetScheduledJobs()
    {
        var jobs = await _schedulerManager.GetScheduledJobsAsync();
        return Ok(jobs);
    }

    /// <summary>
    /// Triggers a scheduled job immediately.
    /// </summary>
    [HttpPost("jobs/{workflowId}/trigger")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> TriggerJob(Guid workflowId)
    {
        try
        {
            await _schedulerManager.TriggerJobAsync(workflowId);
            return Ok(new { message = "Job triggered", workflowId });
        }
        catch (InvalidOperationException ex)
        {
            return NotFound(new { message = ex.Message });
        }
    }

    /// <summary>
    /// Gets scheduler information.
    /// </summary>
    [HttpGet("info")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    public IActionResult GetSchedulerInfo()
    {
        return Ok(new
        {
            service = "scheduler-service",
            version = "1.0.0",
            scheduler = "Quartz.NET 3.8.0",
            environment = Environment.GetEnvironmentVariable("ASPNETCORE_ENVIRONMENT") ?? "Production",
            timestamp = DateTime.UtcNow
        });
    }
}
