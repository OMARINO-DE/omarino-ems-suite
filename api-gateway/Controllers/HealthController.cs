using Microsoft.AspNetCore.Mvc;
using OmarinoEms.ApiGateway.Services;

namespace OmarinoEms.ApiGateway.Controllers;

/// <summary>
/// Controller for health checks and service status.
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class HealthController : ControllerBase
{
    private readonly IServiceHealthCheck _serviceHealthCheck;
    private readonly ILogger<HealthController> _logger;

    public HealthController(IServiceHealthCheck serviceHealthCheck, ILogger<HealthController> logger)
    {
        _serviceHealthCheck = serviceHealthCheck;
        _logger = logger;
    }

    /// <summary>
    /// Checks the health of all backend services.
    /// </summary>
    /// <returns>Aggregated health status of all services</returns>
    [HttpGet("services")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    public async Task<IActionResult> CheckServices()
    {
        _logger.LogDebug("Checking health of all backend services");
        
        var health = await _serviceHealthCheck.CheckServicesHealthAsync();
        
        return Ok(health);
    }

    /// <summary>
    /// Checks the health of a specific service.
    /// </summary>
    /// <param name="serviceName">Name of the service (Timeseries, Forecast, Optimize, Scheduler)</param>
    /// <returns>Health status of the specified service</returns>
    [HttpGet("services/{serviceName}")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> CheckService(string serviceName)
    {
        var validServices = new[] { "Timeseries", "Forecast", "Optimize", "Scheduler" };
        
        if (!validServices.Contains(serviceName, StringComparer.OrdinalIgnoreCase))
        {
            return NotFound(new { message = $"Service '{serviceName}' not found" });
        }

        _logger.LogDebug("Checking health of {ServiceName} service", serviceName);
        
        var health = await _serviceHealthCheck.CheckServiceHealthAsync(serviceName);
        
        return Ok(health);
    }

    /// <summary>
    /// Returns gateway information and version.
    /// </summary>
    /// <returns>Gateway information</returns>
    [HttpGet("info")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    public IActionResult GetInfo()
    {
        return Ok(new
        {
            service = "api-gateway",
            version = "1.0.0",
            environment = Environment.GetEnvironmentVariable("ASPNETCORE_ENVIRONMENT") ?? "Production",
            timestamp = DateTime.UtcNow
        });
    }
}
