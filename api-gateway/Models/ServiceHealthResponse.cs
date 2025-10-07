namespace OmarinoEms.ApiGateway.Models;

/// <summary>
/// Response model for aggregated service health checks.
/// </summary>
public class ServiceHealthResponse
{
    /// <summary>
    /// List of individual service health statuses.
    /// </summary>
    public List<ServiceHealth> Services { get; set; } = new();

    /// <summary>
    /// Overall health status (Healthy, Degraded, Unhealthy).
    /// </summary>
    public string OverallStatus { get; set; } = "Unknown";

    /// <summary>
    /// UTC timestamp when the health check was performed.
    /// </summary>
    public DateTime CheckedAt { get; set; }
}

/// <summary>
/// Health status of an individual service.
/// </summary>
public class ServiceHealth
{
    /// <summary>
    /// Name of the service.
    /// </summary>
    public string Name { get; set; } = string.Empty;

    /// <summary>
    /// Health status (Healthy, Unhealthy, Unknown).
    /// </summary>
    public string Status { get; set; } = "Unknown";

    /// <summary>
    /// URL that was checked.
    /// </summary>
    public string? Url { get; set; }

    /// <summary>
    /// Additional message (e.g., error details).
    /// </summary>
    public string? Message { get; set; }

    /// <summary>
    /// Response time in milliseconds.
    /// </summary>
    public long ResponseTime { get; set; }
}
