using Microsoft.EntityFrameworkCore;
using OmarinoEms.SchedulerService.Data;
using OmarinoEms.SchedulerService.Models;

namespace OmarinoEms.SchedulerService.Services;

/// <summary>
/// Interface for job repository operations.
/// </summary>
public interface IJobRepository
{
    Task<WorkflowDefinition?> GetWorkflowAsync(Guid id);
    Task<List<WorkflowDefinition>> GetAllWorkflowsAsync();
    Task<WorkflowDefinition> CreateWorkflowAsync(WorkflowDefinition workflow);
    Task<WorkflowDefinition> UpdateWorkflowAsync(WorkflowDefinition workflow);
    Task DeleteWorkflowAsync(Guid id);
    Task<List<WorkflowExecution>> GetExecutionsAsync(Guid? workflowId = null, int limit = 100);
    Task<WorkflowExecution?> GetExecutionAsync(Guid id);
}

/// <summary>
/// Repository for workflow and execution persistence.
/// </summary>
public class JobRepository : IJobRepository
{
    private readonly SchedulerDbContext _context;
    private readonly ILogger<JobRepository> _logger;

    public JobRepository(SchedulerDbContext context, ILogger<JobRepository> logger)
    {
        _context = context;
        _logger = logger;
    }

    public async Task<WorkflowDefinition?> GetWorkflowAsync(Guid id)
    {
        return await _context.WorkflowDefinitions.FindAsync(id);
    }

    public async Task<List<WorkflowDefinition>> GetAllWorkflowsAsync()
    {
        return await _context.WorkflowDefinitions
            .OrderBy(w => w.Name)
            .ToListAsync();
    }

    public async Task<WorkflowDefinition> CreateWorkflowAsync(WorkflowDefinition workflow)
    {
        _context.WorkflowDefinitions.Add(workflow);
        await _context.SaveChangesAsync();
        
        _logger.LogInformation("Created workflow {WorkflowName} with ID {WorkflowId}",
            workflow.Name, workflow.Id);
        
        return workflow;
    }

    public async Task<WorkflowDefinition> UpdateWorkflowAsync(WorkflowDefinition workflow)
    {
        workflow.UpdatedAt = NodaTime.SystemClock.Instance.GetCurrentInstant();
        _context.WorkflowDefinitions.Update(workflow);
        await _context.SaveChangesAsync();
        
        _logger.LogInformation("Updated workflow {WorkflowName} ({WorkflowId})",
            workflow.Name, workflow.Id);
        
        return workflow;
    }

    public async Task DeleteWorkflowAsync(Guid id)
    {
        var workflow = await _context.WorkflowDefinitions.FindAsync(id);
        if (workflow != null)
        {
            _context.WorkflowDefinitions.Remove(workflow);
            await _context.SaveChangesAsync();
            
            _logger.LogInformation("Deleted workflow {WorkflowId}", id);
        }
    }

    public async Task<List<WorkflowExecution>> GetExecutionsAsync(Guid? workflowId = null, int limit = 100)
    {
        var query = _context.WorkflowExecutions
            .Include(e => e.TaskExecutions)
            .Include(e => e.Workflow)
            .AsQueryable();

        if (workflowId.HasValue)
        {
            query = query.Where(e => e.WorkflowId == workflowId.Value);
        }

        return await query
            .OrderByDescending(e => e.CreatedAt)
            .Take(limit)
            .ToListAsync();
    }

    public async Task<WorkflowExecution?> GetExecutionAsync(Guid id)
    {
        return await _context.WorkflowExecutions
            .Include(e => e.TaskExecutions)
            .Include(e => e.Workflow)
            .FirstOrDefaultAsync(e => e.Id == id);
    }
}
