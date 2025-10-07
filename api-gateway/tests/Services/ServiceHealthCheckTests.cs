using FluentAssertions;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Moq;
using Moq.Protected;
using OmarinoEms.ApiGateway.Services;
using System.Net;
using Xunit;

namespace OmarinoEms.ApiGateway.Tests.Services;

public class ServiceHealthCheckTests
{
    private readonly Mock<IHttpClientFactory> _mockHttpClientFactory;
    private readonly Mock<IConfiguration> _mockConfiguration;
    private readonly Mock<ILogger<ServiceHealthCheck>> _mockLogger;
    private readonly ServiceHealthCheck _serviceHealthCheck;

    public ServiceHealthCheckTests()
    {
        _mockHttpClientFactory = new Mock<IHttpClientFactory>();
        _mockConfiguration = new Mock<IConfiguration>();
        _mockLogger = new Mock<ILogger<ServiceHealthCheck>>();

        // Setup configuration
        _mockConfiguration.Setup(x => x["ServiceEndpoints:TimeseriesService"]).Returns("http://localhost:5001");
        _mockConfiguration.Setup(x => x["ServiceEndpoints:ForecastService"]).Returns("http://localhost:8001");
        _mockConfiguration.Setup(x => x["ServiceEndpoints:OptimizeService"]).Returns("http://localhost:8002");
        _mockConfiguration.Setup(x => x["ServiceEndpoints:SchedulerService"]).Returns("http://localhost:5003");

        _serviceHealthCheck = new ServiceHealthCheck(
            _mockHttpClientFactory.Object,
            _mockConfiguration.Object,
            _mockLogger.Object);
    }

    [Fact]
    public async Task CheckServiceHealthAsync_WhenServiceIsHealthy_ShouldReturnHealthyStatus()
    {
        // Arrange
        var mockHttpMessageHandler = new Mock<HttpMessageHandler>();
        mockHttpMessageHandler
            .Protected()
            .Setup<Task<HttpResponseMessage>>(
                "SendAsync",
                ItExpr.IsAny<HttpRequestMessage>(),
                ItExpr.IsAny<CancellationToken>())
            .ReturnsAsync(new HttpResponseMessage
            {
                StatusCode = HttpStatusCode.OK
            });

        var httpClient = new HttpClient(mockHttpMessageHandler.Object);
        _mockHttpClientFactory.Setup(x => x.CreateClient(It.IsAny<string>())).Returns(httpClient);

        // Act
        var result = await _serviceHealthCheck.CheckServiceHealthAsync("Timeseries");

        // Assert
        result.Should().NotBeNull();
        result.Name.Should().Be("Timeseries");
        result.Status.Should().Be("Healthy");
        result.ResponseTime.Should().BeGreaterThanOrEqualTo(0);
    }

    [Fact]
    public async Task CheckServiceHealthAsync_WhenServiceReturnsError_ShouldReturnUnhealthyStatus()
    {
        // Arrange
        var mockHttpMessageHandler = new Mock<HttpMessageHandler>();
        mockHttpMessageHandler
            .Protected()
            .Setup<Task<HttpResponseMessage>>(
                "SendAsync",
                ItExpr.IsAny<HttpRequestMessage>(),
                ItExpr.IsAny<CancellationToken>())
            .ReturnsAsync(new HttpResponseMessage
            {
                StatusCode = HttpStatusCode.InternalServerError
            });

        var httpClient = new HttpClient(mockHttpMessageHandler.Object);
        _mockHttpClientFactory.Setup(x => x.CreateClient(It.IsAny<string>())).Returns(httpClient);

        // Act
        var result = await _serviceHealthCheck.CheckServiceHealthAsync("Forecast");

        // Assert
        result.Should().NotBeNull();
        result.Name.Should().Be("Forecast");
        result.Status.Should().Be("Unhealthy");
        result.Message.Should().Contain("500");
    }

    [Fact]
    public async Task CheckServiceHealthAsync_WhenServiceNotConfigured_ShouldReturnUnknownStatus()
    {
        // Arrange
        _mockConfiguration.Setup(x => x["ServiceEndpoints:UnknownService"]).Returns((string?)null);

        // Act
        var result = await _serviceHealthCheck.CheckServiceHealthAsync("Unknown");

        // Assert
        result.Should().NotBeNull();
        result.Name.Should().Be("Unknown");
        result.Status.Should().Be("Unknown");
        result.Message.Should().Contain("not configured");
    }

    [Fact]
    public async Task CheckServicesHealthAsync_ShouldCheckAllServices()
    {
        // Arrange
        var mockHttpMessageHandler = new Mock<HttpMessageHandler>();
        mockHttpMessageHandler
            .Protected()
            .Setup<Task<HttpResponseMessage>>(
                "SendAsync",
                ItExpr.IsAny<HttpRequestMessage>(),
                ItExpr.IsAny<CancellationToken>())
            .ReturnsAsync(new HttpResponseMessage
            {
                StatusCode = HttpStatusCode.OK
            });

        var httpClient = new HttpClient(mockHttpMessageHandler.Object);
        _mockHttpClientFactory.Setup(x => x.CreateClient(It.IsAny<string>())).Returns(httpClient);

        // Act
        var result = await _serviceHealthCheck.CheckServicesHealthAsync();

        // Assert
        result.Should().NotBeNull();
        result.Services.Should().HaveCount(4);
        result.Services.Should().Contain(s => s.Name == "Timeseries");
        result.Services.Should().Contain(s => s.Name == "Forecast");
        result.Services.Should().Contain(s => s.Name == "Optimize");
        result.Services.Should().Contain(s => s.Name == "Scheduler");
        result.OverallStatus.Should().Be("Healthy");
    }
}
