using Microsoft.EntityFrameworkCore;
using OmarinoEms.SchedulerService.Data;
using OmarinoEms.SchedulerService.Services;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using Quartz;
using Serilog;

var builder = WebApplication.CreateBuilder(args);

// Configure Serilog
Log.Logger = new LoggerConfiguration()
    .ReadFrom.Configuration(builder.Configuration)
    .Enrich.FromLogContext()
    .Enrich.WithMachineName()
    .Enrich.WithThreadId()
    .WriteTo.Console()
    .CreateLogger();

builder.Host.UseSerilog();

// Add services to the container
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new Microsoft.OpenApi.Models.OpenApiInfo
    {
        Title = "OMARINO EMS Scheduler Service",
        Version = "v1",
        Description = "Workflow orchestration and job scheduling service using Quartz.NET"
    });
});

// Configure Database
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");

// Enable dynamic JSON serialization globally for Dictionary fields
// Note: This uses the deprecated GlobalTypeMapper API, but it's the simplest solution for Npgsql 7.0+
#pragma warning disable CS0618 // Type or member is obsolete
Npgsql.NpgsqlConnection.GlobalTypeMapper.EnableDynamicJson();
#pragma warning restore CS0618

builder.Services.AddDbContext<SchedulerDbContext>(options =>
    options.UseNpgsql(connectionString, o => o.UseNodaTime()));

// Configure Quartz.NET
builder.Services.AddQuartz(q =>
{
    // Use JSON serialization
    q.UseMicrosoftDependencyInjectionJobFactory();
    q.UseSimpleTypeLoader();
    q.UseInMemoryStore(); // For development - use PostgreSQL in production
    q.UseDefaultThreadPool(tp =>
    {
        tp.MaxConcurrency = 10;
    });
    
    // Configure job serialization using JSON
    q.UseMicrosoftDependencyInjectionJobFactory();
});

// Add Quartz hosted service
builder.Services.AddQuartzHostedService(options =>
{
    options.WaitForJobsToComplete = true;
});

// Add custom services
builder.Services.AddHttpClient();
builder.Services.AddScoped<IWorkflowEngine, WorkflowEngine>();
builder.Services.AddScoped<IWorkflowExecutor, WorkflowExecutor>();
builder.Services.AddScoped<IJobRepository, JobRepository>();
builder.Services.AddSingleton<ISchedulerManager, SchedulerManager>();

// Add Health Checks
builder.Services.AddHealthChecks()
    .AddNpgSql(connectionString!)
    .AddCheck<QuartzHealthCheck>("quartz");

// Configure CORS
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});

// Configure OpenTelemetry
builder.Services.AddOpenTelemetry()
    .WithMetrics(metrics =>
    {
        metrics
            .SetResourceBuilder(ResourceBuilder.CreateDefault().AddService("scheduler-service"))
            .AddAspNetCoreInstrumentation()
            .AddHttpClientInstrumentation()
            .AddPrometheusExporter();
    })
    .WithTracing(tracing =>
    {
        tracing
            .SetResourceBuilder(ResourceBuilder.CreateDefault().AddService("scheduler-service"))
            .AddAspNetCoreInstrumentation()
            .AddHttpClientInstrumentation()
            .AddEntityFrameworkCoreInstrumentation();
    });

var app = builder.Build();

// Configure the HTTP request pipeline
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI(c =>
    {
        c.SwaggerEndpoint("/swagger/v1/swagger.json", "Scheduler Service v1");
    });
}

// Middleware pipeline
app.UseSerilogRequestLogging();
app.UseCors("AllowAll");
app.UseAuthorization();

// Map controllers
app.MapControllers();

// Map health checks
app.MapHealthChecks("/api/health", new Microsoft.AspNetCore.Diagnostics.HealthChecks.HealthCheckOptions
{
    ResponseWriter = async (context, report) =>
    {
        context.Response.ContentType = "application/json";
        var result = System.Text.Json.JsonSerializer.Serialize(new
        {
            status = report.Status.ToString(),
            checks = report.Entries.Select(e => new
            {
                name = e.Key,
                status = e.Value.Status.ToString(),
                description = e.Value.Description,
                duration = e.Value.Duration.TotalMilliseconds
            }),
            totalDuration = report.TotalDuration.TotalMilliseconds
        });
        await context.Response.WriteAsync(result);
    }
});

// Map Prometheus metrics endpoint
app.MapPrometheusScrapingEndpoint();

// Apply database migrations
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<SchedulerDbContext>();
    try
    {
        db.Database.Migrate();
        Log.Information("Database migrations applied successfully");
    }
    catch (Exception ex)
    {
        Log.Error(ex, "Error applying database migrations");
    }
}

Log.Information("Scheduler Service starting on {Environment}", app.Environment.EnvironmentName);

try
{
    app.Run();
}
catch (Exception ex)
{
    Log.Fatal(ex, "Scheduler Service terminated unexpectedly");
}
finally
{
    Log.CloseAndFlush();
}
