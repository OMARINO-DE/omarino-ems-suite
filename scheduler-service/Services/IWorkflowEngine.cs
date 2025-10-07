using OmarinoEms.SchedulerService.Models;

namespace OmarinoEms.SchedulerService.Services;

/// <summary>
/// Interface for workflow engine operations.
/// </summary>
public interface IWorkflowEngine
{
    /// <summary>
    /// Executes a workflow.
    /// </summary>
    /// <param name="workflowId">ID of the workflow to execute</param>
    /// <param name="triggerType">How the workflow was triggered</param>
    /// <param name="triggeredBy">User or system that triggered the workflow</param>
    /// <returns>Workflow execution instance</returns>
    Task<WorkflowExecution> ExecuteWorkflowAsync(Guid workflowId, TriggerType triggerType, string? triggeredBy = null);

    /// <summary>
    /// Cancels a running workflow execution.
    /// </summary>
    /// <param name="executionId">ID of the execution to cancel</param>
    Task CancelExecutionAsync(Guid executionId);

    /// <summary>
    /// Gets the status of a workflow execution.
    /// </summary>
    /// <param name="executionId">ID of the execution</param>
    /// <returns>Workflow execution instance</returns>
    Task<WorkflowExecution?> GetExecutionStatusAsync(Guid executionId);

    /// <summary>
    /// Validates a workflow definition (checks for cycles, missing dependencies, etc.).
    /// </summary>
    /// <param name="workflow">Workflow to validate</param>
    /// <returns>Validation result</returns>
    Task<ValidationResult> ValidateWorkflowAsync(WorkflowDefinition workflow);
}

/// <summary>
/// Result of workflow validation.
/// </summary>
public class ValidationResult
{
    public bool IsValid { get; set; }
    public List<string> Errors { get; set; } = new();
    public List<string> Warnings { get; set; } = new();
}
