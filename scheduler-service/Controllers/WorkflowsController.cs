using Microsoft.AspNetCore.Mvc;
using OmarinoEms.SchedulerService.Models;
using OmarinoEms.SchedulerService.Services;

namespace OmarinoEms.SchedulerService.Controllers;

/// <summary>
/// Controller for workflow management.
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class WorkflowsController : ControllerBase
{
    private readonly IJobRepository _repository;
    private readonly IWorkflowEngine _engine;
    private readonly ISchedulerManager _schedulerManager;
    private readonly ILogger<WorkflowsController> _logger;

    public WorkflowsController(
        IJobRepository repository,
        IWorkflowEngine engine,
        ISchedulerManager schedulerManager,
        ILogger<WorkflowsController> logger)
    {
        _repository = repository;
        _engine = engine;
        _schedulerManager = schedulerManager;
        _logger = logger;
    }

    /// <summary>
    /// Gets all workflows.
    /// </summary>
    [HttpGet]
    [ProducesResponseType(typeof(List<WorkflowDefinition>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetWorkflows()
    {
        var workflows = await _repository.GetAllWorkflowsAsync();
        return Ok(workflows);
    }

    /// <summary>
    /// Gets a workflow by ID.
    /// </summary>
    [HttpGet("{id}")]
    [ProducesResponseType(typeof(WorkflowDefinition), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetWorkflow(Guid id)
    {
        var workflow = await _repository.GetWorkflowAsync(id);
        
        if (workflow == null)
        {
            return NotFound(new { message = $"Workflow {id} not found" });
        }

        return Ok(workflow);
    }

    /// <summary>
    /// Creates a new workflow.
    /// </summary>
    [HttpPost]
    [ProducesResponseType(typeof(WorkflowDefinition), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> CreateWorkflow([FromBody] WorkflowDefinition workflow)
    {
        // Validate workflow
        var validation = await _engine.ValidateWorkflowAsync(workflow);
        if (!validation.IsValid)
        {
            return BadRequest(new
            {
                message = "Workflow validation failed",
                errors = validation.Errors,
                warnings = validation.Warnings
            });
        }

        var created = await _repository.CreateWorkflowAsync(workflow);

        // Schedule if configured
        if (workflow.Schedule != null && workflow.Schedule.Type == ScheduleType.Cron && workflow.IsEnabled)
        {
            await _schedulerManager.ScheduleWorkflowAsync(
                created.Id,
                workflow.Schedule.CronExpression!,
                workflow.Schedule.TimeZone);
        }

        return CreatedAtAction(nameof(GetWorkflow), new { id = created.Id }, created);
    }

    /// <summary>
    /// Updates an existing workflow.
    /// </summary>
    [HttpPut("{id}")]
    [ProducesResponseType(typeof(WorkflowDefinition), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> UpdateWorkflow(Guid id, [FromBody] WorkflowDefinition workflow)
    {
        var existing = await _repository.GetWorkflowAsync(id);
        if (existing == null)
        {
            return NotFound(new { message = $"Workflow {id} not found" });
        }

        // Validate workflow
        var validation = await _engine.ValidateWorkflowAsync(workflow);
        if (!validation.IsValid)
        {
            return BadRequest(new
            {
                message = "Workflow validation failed",
                errors = validation.Errors,
                warnings = validation.Warnings
            });
        }

        workflow.Id = id;
        var updated = await _repository.UpdateWorkflowAsync(workflow);

        // Update schedule
        await _schedulerManager.UnscheduleWorkflowAsync(id);
        
        if (workflow.Schedule != null && workflow.Schedule.Type == ScheduleType.Cron && workflow.IsEnabled)
        {
            await _schedulerManager.ScheduleWorkflowAsync(
                id,
                workflow.Schedule.CronExpression!,
                workflow.Schedule.TimeZone);
        }

        return Ok(updated);
    }

    /// <summary>
    /// Deletes a workflow.
    /// </summary>
    [HttpDelete("{id}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> DeleteWorkflow(Guid id)
    {
        var workflow = await _repository.GetWorkflowAsync(id);
        if (workflow == null)
        {
            return NotFound(new { message = $"Workflow {id} not found" });
        }

        await _schedulerManager.UnscheduleWorkflowAsync(id);
        await _repository.DeleteWorkflowAsync(id);

        return NoContent();
    }

    /// <summary>
    /// Validates a workflow definition.
    /// </summary>
    [HttpPost("validate")]
    [ProducesResponseType(typeof(ValidationResult), StatusCodes.Status200OK)]
    public async Task<IActionResult> ValidateWorkflow([FromBody] WorkflowDefinition workflow)
    {
        var validation = await _engine.ValidateWorkflowAsync(workflow);
        return Ok(validation);
    }

    /// <summary>
    /// Triggers a workflow execution immediately.
    /// </summary>
    [HttpPost("{id}/trigger")]
    [ProducesResponseType(typeof(WorkflowExecution), StatusCodes.Status202Accepted)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> TriggerWorkflow(Guid id)
    {
        var workflow = await _repository.GetWorkflowAsync(id);
        if (workflow == null)
        {
            return NotFound(new { message = $"Workflow {id} not found" });
        }

        var execution = await _engine.ExecuteWorkflowAsync(id, TriggerType.Manual, User.Identity?.Name);

        return AcceptedAtAction(nameof(GetExecution), new { id = execution.Id }, execution);
    }

    /// <summary>
    /// Gets an execution by ID (redirects to ExecutionsController).
    /// </summary>
    [HttpGet("executions/{id}")]
    [ProducesResponseType(typeof(WorkflowExecution), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetExecution(Guid id)
    {
        var execution = await _repository.GetExecutionAsync(id);
        
        if (execution == null)
        {
            return NotFound(new { message = $"Execution {id} not found" });
        }

        return Ok(execution);
    }
}
