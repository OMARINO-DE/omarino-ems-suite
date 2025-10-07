using Microsoft.AspNetCore.Mvc;
using OmarinoEms.SchedulerService.Models;
using OmarinoEms.SchedulerService.Services;

namespace OmarinoEms.SchedulerService.Controllers;

/// <summary>
/// Controller for workflow execution management.
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class ExecutionsController : ControllerBase
{
    private readonly IJobRepository _repository;
    private readonly IWorkflowEngine _engine;
    private readonly ILogger<ExecutionsController> _logger;

    public ExecutionsController(
        IJobRepository repository,
        IWorkflowEngine engine,
        ILogger<ExecutionsController> logger)
    {
        _repository = repository;
        _engine = engine;
        _logger = logger;
    }

    /// <summary>
    /// Gets executions with optional filtering by workflow ID.
    /// </summary>
    [HttpGet]
    [ProducesResponseType(typeof(List<WorkflowExecution>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetExecutions(
        [FromQuery] Guid? workflowId = null,
        [FromQuery] int limit = 100)
    {
        var executions = await _repository.GetExecutionsAsync(workflowId, limit);
        return Ok(executions);
    }

    /// <summary>
    /// Gets a specific execution by ID.
    /// </summary>
    [HttpGet("{id}")]
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

    /// <summary>
    /// Cancels a running execution.
    /// </summary>
    [HttpPost("{id}/cancel")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> CancelExecution(Guid id)
    {
        try
        {
            await _engine.CancelExecutionAsync(id);
            return Ok(new { message = "Execution cancelled", executionId = id });
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(new { message = ex.Message });
        }
    }
}
