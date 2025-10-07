using FluentAssertions;
using OmarinoEms.SchedulerService.Models;
using OmarinoEms.SchedulerService.Services;
using Xunit;

namespace OmarinoEms.SchedulerService.Tests.Services;

public class WorkflowValidationTests
{
    [Fact]
    public async Task ValidateWorkflowAsync_WithValidWorkflow_ShouldReturnValid()
    {
        // Arrange
        var workflow = new WorkflowDefinition
        {
            Name = "Test Workflow",
            Tasks = new List<WorkflowTask>
            {
                new WorkflowTask
                {
                    Id = Guid.NewGuid(),
                    Name = "Task 1",
                    Type = TaskType.HttpCall,
                    Config = new Dictionary<string, object> { { "url", "http://example.com" } }
                }
            }
        };

        var engine = CreateWorkflowEngine();

        // Act
        var result = await engine.ValidateWorkflowAsync(workflow);

        // Assert
        result.IsValid.Should().BeTrue();
        result.Errors.Should().BeEmpty();
    }

    [Fact]
    public async Task ValidateWorkflowAsync_WithEmptyTasks_ShouldReturnInvalid()
    {
        // Arrange
        var workflow = new WorkflowDefinition
        {
            Name = "Empty Workflow",
            Tasks = new List<WorkflowTask>()
        };

        var engine = CreateWorkflowEngine();

        // Act
        var result = await engine.ValidateWorkflowAsync(workflow);

        // Assert
        result.IsValid.Should().BeFalse();
        result.Errors.Should().Contain(e => e.Contains("at least one task"));
    }

    [Fact]
    public async Task ValidateWorkflowAsync_WithCycle_ShouldReturnInvalid()
    {
        // Arrange
        var task1Id = Guid.NewGuid();
        var task2Id = Guid.NewGuid();

        var workflow = new WorkflowDefinition
        {
            Name = "Cyclic Workflow",
            Tasks = new List<WorkflowTask>
            {
                new WorkflowTask
                {
                    Id = task1Id,
                    Name = "Task 1",
                    Type = TaskType.Delay,
                    Config = new Dictionary<string, object> { { "duration", 5 } },
                    DependsOn = new List<Guid> { task2Id }
                },
                new WorkflowTask
                {
                    Id = task2Id,
                    Name = "Task 2",
                    Type = TaskType.Delay,
                    Config = new Dictionary<string, object> { { "duration", 5 } },
                    DependsOn = new List<Guid> { task1Id }
                }
            }
        };

        var engine = CreateWorkflowEngine();

        // Act
        var result = await engine.ValidateWorkflowAsync(workflow);

        // Assert
        result.IsValid.Should().BeFalse();
        result.Errors.Should().Contain(e => e.Contains("cycle"));
    }

    [Fact]
    public async Task ValidateWorkflowAsync_WithInvalidDependency_ShouldReturnInvalid()
    {
        // Arrange
        var workflow = new WorkflowDefinition
        {
            Name = "Invalid Dependency Workflow",
            Tasks = new List<WorkflowTask>
            {
                new WorkflowTask
                {
                    Id = Guid.NewGuid(),
                    Name = "Task 1",
                    Type = TaskType.Delay,
                    Config = new Dictionary<string, object> { { "duration", 5 } },
                    DependsOn = new List<Guid> { Guid.NewGuid() } // Non-existent task
                }
            }
        };

        var engine = CreateWorkflowEngine();

        // Act
        var result = await engine.ValidateWorkflowAsync(workflow);

        // Assert
        result.IsValid.Should().BeFalse();
        result.Errors.Should().Contain(e => e.Contains("non-existent"));
    }

    [Fact]
    public async Task ValidateWorkflowAsync_WithMissingHttpCallUrl_ShouldReturnInvalid()
    {
        // Arrange
        var workflow = new WorkflowDefinition
        {
            Name = "Invalid HttpCall Workflow",
            Tasks = new List<WorkflowTask>
            {
                new WorkflowTask
                {
                    Id = Guid.NewGuid(),
                    Name = "HTTP Task",
                    Type = TaskType.HttpCall,
                    Config = new Dictionary<string, object>() // Missing 'url'
                }
            }
        };

        var engine = CreateWorkflowEngine();

        // Act
        var result = await engine.ValidateWorkflowAsync(workflow);

        // Assert
        result.IsValid.Should().BeFalse();
        result.Errors.Should().Contain(e => e.Contains("url"));
    }

    private WorkflowEngine CreateWorkflowEngine()
    {
        // Create in-memory database context
        var options = new Microsoft.EntityFrameworkCore.DbContextOptionsBuilder<OmarinoEms.SchedulerService.Data.SchedulerDbContext>()
            .UseInMemoryDatabase(databaseName: Guid.NewGuid().ToString())
            .Options;

        var context = new OmarinoEms.SchedulerService.Data.SchedulerDbContext(options);
        
        var executor = new Moq.Mock<IWorkflowExecutor>();
        var logger = new Moq.Mock<Microsoft.Extensions.Logging.ILogger<WorkflowEngine>>();

        return new WorkflowEngine(context, executor.Object, logger.Object);
    }
}
