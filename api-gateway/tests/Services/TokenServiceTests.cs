using FluentAssertions;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Moq;
using OmarinoEms.ApiGateway.Services;
using Xunit;

namespace OmarinoEms.ApiGateway.Tests.Services;

public class TokenServiceTests
{
    private readonly Mock<IConfiguration> _mockConfiguration;
    private readonly Mock<IConfigurationSection> _mockJwtSection;
    private readonly Mock<ILogger<TokenService>> _mockLogger;
    private readonly TokenService _tokenService;

    public TokenServiceTests()
    {
        _mockConfiguration = new Mock<IConfiguration>();
        _mockJwtSection = new Mock<IConfigurationSection>();
        _mockLogger = new Mock<ILogger<TokenService>>();

        // Setup JWT configuration
        _mockJwtSection.Setup(x => x["SecretKey"]).Returns("ThisIsASecretKeyForTestingPurposesOnly32Characters!");
        _mockJwtSection.Setup(x => x["Issuer"]).Returns("https://test-issuer.local");
        _mockJwtSection.Setup(x => x["Audience"]).Returns("test-audience");
        _mockJwtSection.Setup(x => x["ExpirationMinutes"]).Returns("60");

        _mockConfiguration.Setup(x => x.GetSection("Jwt")).Returns(_mockJwtSection.Object);

        _tokenService = new TokenService(_mockConfiguration.Object, _mockLogger.Object);
    }

    [Fact]
    public void GenerateToken_ShouldReturnValidToken()
    {
        // Arrange
        var username = "testuser";
        var roles = new[] { "User", "Admin" };

        // Act
        var result = _tokenService.GenerateToken(username, roles);

        // Assert
        result.Should().NotBeNull();
        result.Token.Should().NotBeNullOrEmpty();
        result.TokenType.Should().Be("Bearer");
        result.ExpiresAt.Should().BeAfter(DateTime.UtcNow);
        result.ExpiresIn.Should().BeGreaterThan(0);
    }

    [Fact]
    public void GenerateToken_ShouldSetCorrectExpiration()
    {
        // Arrange
        var username = "testuser";
        var roles = new[] { "User" };
        var beforeGeneration = DateTime.UtcNow;

        // Act
        var result = _tokenService.GenerateToken(username, roles);

        // Assert
        var expectedExpiration = beforeGeneration.AddMinutes(60);
        result.ExpiresAt.Should().BeCloseTo(expectedExpiration, TimeSpan.FromSeconds(5));
    }

    [Fact]
    public void ValidateToken_WithValidToken_ShouldReturnTrue()
    {
        // Arrange
        var username = "testuser";
        var roles = new[] { "User" };
        var tokenResponse = _tokenService.GenerateToken(username, roles);

        // Act
        var isValid = _tokenService.ValidateToken(tokenResponse.Token);

        // Assert
        isValid.Should().BeTrue();
    }

    [Fact]
    public void ValidateToken_WithInvalidToken_ShouldReturnFalse()
    {
        // Arrange
        var invalidToken = "invalid.token.string";

        // Act
        var isValid = _tokenService.ValidateToken(invalidToken);

        // Assert
        isValid.Should().BeFalse();
    }

    [Fact]
    public void ValidateToken_WithEmptyToken_ShouldReturnFalse()
    {
        // Arrange
        var emptyToken = string.Empty;

        // Act
        var isValid = _tokenService.ValidateToken(emptyToken);

        // Assert
        isValid.Should().BeFalse();
    }
}
