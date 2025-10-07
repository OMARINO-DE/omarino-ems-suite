using System.Diagnostics;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using OmarinoEms.ApiGateway.Models;

namespace OmarinoEms.ApiGateway.Services;

/// <summary>
/// Service for checking the health of backend services.
/// </summary>
public class ServiceHealthCheck : IHealthCheck, IServiceHealthCheck
{
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly IConfiguration _configuration;
    private readonly ILogger<ServiceHealthCheck> _logger;

    public ServiceHealthCheck(
        IHttpClientFactory httpClientFactory,
        IConfiguration configuration,
        ILogger<ServiceHealthCheck> logger)
    {
        _httpClientFactory = httpClientFactory;
        _configuration = configuration;
        _logger = logger;
    }

    public async Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context,
        CancellationToken cancellationToken = default)
    {
        var healthResponse = await CheckServicesHealthAsync();
        var unhealthyServices = healthResponse.Services.Where(s => s.Status != "Healthy").ToList();

        if (unhealthyServices.Any())
        {
            return HealthCheckResult.Degraded(
                $"{unhealthyServices.Count} service(s) are unhealthy: {string.Join(", ", unhealthyServices.Select(s => s.Name))}");
        }

        return HealthCheckResult.Healthy("All backend services are healthy");
    }

    public async Task<ServiceHealthResponse> CheckServicesHealthAsync()
    {
        var services = new Dictionary<string, string>
        {
            { "Timeseries", _configuration["ServiceEndpoints:TimeseriesService"] ?? string.Empty },
            { "Forecast", _configuration["ServiceEndpoints:ForecastService"] ?? string.Empty },
            { "Optimize", _configuration["ServiceEndpoints:OptimizeService"] ?? string.Empty },
            { "Scheduler", _configuration["ServiceEndpoints:SchedulerService"] ?? string.Empty }
        };

        var healthChecks = new List<ServiceHealth>();

        foreach (var service in services)
        {
            var health = await CheckServiceHealthAsync(service.Key);
            healthChecks.Add(health);
        }

        return new ServiceHealthResponse
        {
            Services = healthChecks,
            OverallStatus = healthChecks.All(s => s.Status == "Healthy") ? "Healthy" : "Degraded",
            CheckedAt = DateTime.UtcNow
        };
    }

    public async Task<ServiceHealth> CheckServiceHealthAsync(string serviceName)
    {
        var serviceEndpoint = _configuration[$"ServiceEndpoints:{serviceName}Service"];
        
        if (string.IsNullOrEmpty(serviceEndpoint))
        {
            _logger.LogWarning("Service endpoint not configured for {ServiceName}", serviceName);
            return new ServiceHealth
            {
                Name = serviceName,
                Status = "Unknown",
                Message = "Service endpoint not configured",
                ResponseTime = 0
            };
        }

        // Timeseries service uses /health, others use /api/health
        var healthPath = serviceName == "Timeseries" ? "/health" : "/api/health";
        var healthUrl = $"{serviceEndpoint}{healthPath}";
        var stopwatch = Stopwatch.StartNew();

        try
        {
            var client = _httpClientFactory.CreateClient();
            client.Timeout = TimeSpan.FromSeconds(5);

            var response = await client.GetAsync(healthUrl);
            stopwatch.Stop();

            if (response.IsSuccessStatusCode)
            {
                _logger.LogDebug("{ServiceName} service is healthy (responded in {ElapsedMilliseconds}ms)", 
                    serviceName, stopwatch.ElapsedMilliseconds);

                return new ServiceHealth
                {
                    Name = serviceName,
                    Status = "Healthy",
                    Url = healthUrl,
                    ResponseTime = stopwatch.ElapsedMilliseconds
                };
            }

            _logger.LogWarning("{ServiceName} service returned status code {StatusCode}", 
                serviceName, response.StatusCode);

            return new ServiceHealth
            {
                Name = serviceName,
                Status = "Unhealthy",
                Url = healthUrl,
                Message = $"HTTP {(int)response.StatusCode}",
                ResponseTime = stopwatch.ElapsedMilliseconds
            };
        }
        catch (TaskCanceledException)
        {
            stopwatch.Stop();
            _logger.LogWarning("{ServiceName} service health check timed out after {ElapsedMilliseconds}ms", 
                serviceName, stopwatch.ElapsedMilliseconds);

            return new ServiceHealth
            {
                Name = serviceName,
                Status = "Unhealthy",
                Url = healthUrl,
                Message = "Health check timed out",
                ResponseTime = stopwatch.ElapsedMilliseconds
            };
        }
        catch (Exception ex)
        {
            stopwatch.Stop();
            _logger.LogError(ex, "Error checking health of {ServiceName} service", serviceName);

            return new ServiceHealth
            {
                Name = serviceName,
                Status = "Unhealthy",
                Url = healthUrl,
                Message = ex.Message,
                ResponseTime = stopwatch.ElapsedMilliseconds
            };
        }
    }
}
