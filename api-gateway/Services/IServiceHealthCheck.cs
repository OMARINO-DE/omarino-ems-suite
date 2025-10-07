using OmarinoEms.ApiGateway.Models;

namespace OmarinoEms.ApiGateway.Services;

/// <summary>
/// Interface for checking the health of backend services.
/// </summary>
public interface IServiceHealthCheck
{
    /// <summary>
    /// Checks the health of all backend services.
    /// </summary>
    /// <returns>Health status of all services</returns>
    Task<ServiceHealthResponse> CheckServicesHealthAsync();

    /// <summary>
    /// Checks the health of a specific service.
    /// </summary>
    /// <param name="serviceName">The name of the service to check</param>
    /// <returns>Health status of the specified service</returns>
    Task<ServiceHealth> CheckServiceHealthAsync(string serviceName);
}
