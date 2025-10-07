using FluentAssertions;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using Moq;
using OmarinoEms.ApiGateway.Controllers;
using OmarinoEms.ApiGateway.Models;
using OmarinoEms.ApiGateway.Services;
using Xunit;

namespace OmarinoEms.ApiGateway.Tests.Controllers;

public class AuthControllerTests
{
    private readonly Mock<ITokenService> _mockTokenService;
    private readonly Mock<ILogger<AuthController>> _mockLogger;
    private readonly AuthController _controller;

    public AuthControllerTests()
    {
        _mockTokenService = new Mock<ITokenService>();
        _mockLogger = new Mock<ILogger<AuthController>>();
        _controller = new AuthController(_mockTokenService.Object, _mockLogger.Object);
    }

    [Fact]
    public void Login_WithValidCredentials_ShouldReturnToken()
    {
        // Arrange
        var request = new LoginRequest { Username = "demo", Password = "demo123" };
        var expectedToken = new TokenResponse
        {
            Token = "test-token",
            TokenType = "Bearer",
            ExpiresAt = DateTime.UtcNow.AddHours(1)
        };

        _mockTokenService.Setup(x => x.GenerateToken(It.IsAny<string>(), It.IsAny<IEnumerable<string>>()))
            .Returns(expectedToken);

        // Act
        var result = _controller.Login(request);

        // Assert
        result.Should().BeOfType<OkObjectResult>();
        var okResult = result as OkObjectResult;
        okResult!.Value.Should().BeEquivalentTo(expectedToken);
    }

    [Fact]
    public void Login_WithInvalidCredentials_ShouldReturnUnauthorized()
    {
        // Arrange
        var request = new LoginRequest { Username = "invalid", Password = "invalid" };

        // Act
        var result = _controller.Login(request);

        // Assert
        result.Should().BeOfType<UnauthorizedObjectResult>();
    }

    [Fact]
    public void Login_WithEmptyUsername_ShouldReturnBadRequest()
    {
        // Arrange
        var request = new LoginRequest { Username = "", Password = "password" };

        // Act
        var result = _controller.Login(request);

        // Assert
        result.Should().BeOfType<BadRequestObjectResult>();
    }

    [Fact]
    public void Login_WithEmptyPassword_ShouldReturnBadRequest()
    {
        // Arrange
        var request = new LoginRequest { Username = "username", Password = "" };

        // Act
        var result = _controller.Login(request);

        // Assert
        result.Should().BeOfType<BadRequestObjectResult>();
    }

    [Fact]
    public void ValidateToken_WithNoToken_ShouldReturnUnauthorized()
    {
        // Act
        var result = _controller.ValidateToken();

        // Assert
        result.Should().BeOfType<UnauthorizedObjectResult>();
    }
}
