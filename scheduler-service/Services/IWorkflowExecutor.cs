using OmarinoEms.SchedulerService.Models;

namespace OmarinoEms.SchedulerService.Services;

/// <summary>
/// Interface for executing workflow tasks.
/// </summary>
public interface IWorkflowExecutor
{
    /// <summary>
    /// Executes a workflow's tasks in the correct order based on dependencies.
    /// </summary>
    /// <param name="workflow">Workflow definition</param>
    /// <param name="execution">Workflow execution instance</param>
    /// <param name="cancellationToken">Cancellation token</param>
    Task ExecuteAsync(WorkflowDefinition workflow, WorkflowExecution execution, CancellationToken cancellationToken);
}
