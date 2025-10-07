using Microsoft.AspNetCore.Mvc;
using OmarinoEms.ApiGateway.Models;
using OmarinoEms.ApiGateway.Services;

namespace OmarinoEms.ApiGateway.Controllers;

/// <summary>
/// Controller for user authentication and token management.
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class AuthController : ControllerBase
{
    private readonly ITokenService _tokenService;
    private readonly ILogger<AuthController> _logger;

    public AuthController(ITokenService tokenService, ILogger<AuthController> logger)
    {
        _tokenService = tokenService;
        _logger = logger;
    }

    /// <summary>
    /// Authenticates a user and returns a JWT token.
    /// </summary>
    /// <param name="request">Login credentials</param>
    /// <returns>JWT token response</returns>
    [HttpPost("login")]
    [ProducesResponseType(typeof(TokenResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public IActionResult Login([FromBody] LoginRequest request)
    {
        // TODO: Replace with actual user authentication against a user store
        // This is a simplified example - in production, use ASP.NET Core Identity or similar
        
        if (string.IsNullOrEmpty(request.Username) || string.IsNullOrEmpty(request.Password))
        {
            return BadRequest(new { message = "Username and password are required" });
        }

        // Simple demo authentication (REPLACE WITH REAL AUTHENTICATION)
        if (request.Username == "demo" && request.Password == "demo123")
        {
            var roles = new[] { "User", "Admin" };
            var token = _tokenService.GenerateToken(request.Username, roles);

            _logger.LogInformation("User {Username} authenticated successfully", request.Username);
            
            return Ok(token);
        }

        _logger.LogWarning("Failed login attempt for user {Username}", request.Username);
        return Unauthorized(new { message = "Invalid username or password" });
    }

    /// <summary>
    /// Validates the current JWT token.
    /// </summary>
    /// <returns>Token validation result</returns>
    [HttpGet("validate")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public IActionResult ValidateToken()
    {
        var authHeader = Request.Headers["Authorization"].FirstOrDefault();
        
        if (string.IsNullOrEmpty(authHeader) || !authHeader.StartsWith("Bearer "))
        {
            return Unauthorized(new { message = "No token provided" });
        }

        var token = authHeader.Substring("Bearer ".Length).Trim();
        var isValid = _tokenService.ValidateToken(token);

        if (isValid)
        {
            return Ok(new { valid = true, message = "Token is valid" });
        }

        return Unauthorized(new { valid = false, message = "Token is invalid or expired" });
    }

    /// <summary>
    /// Refreshes an existing JWT token.
    /// </summary>
    /// <returns>New JWT token</returns>
    [HttpPost("refresh")]
    [ProducesResponseType(typeof(TokenResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public IActionResult RefreshToken()
    {
        var authHeader = Request.Headers["Authorization"].FirstOrDefault();
        
        if (string.IsNullOrEmpty(authHeader) || !authHeader.StartsWith("Bearer "))
        {
            return Unauthorized(new { message = "No token provided" });
        }

        var token = authHeader.Substring("Bearer ".Length).Trim();
        
        // TODO: Implement proper token refresh logic with refresh tokens
        // This is a simplified example
        
        if (_tokenService.ValidateToken(token))
        {
            // Extract username from the existing token and generate a new one
            var username = User.Identity?.Name ?? "unknown";
            var roles = User.Claims
                .Where(c => c.Type == System.Security.Claims.ClaimTypes.Role)
                .Select(c => c.Value);

            var newToken = _tokenService.GenerateToken(username, roles);
            
            _logger.LogInformation("Token refreshed for user {Username}", username);
            
            return Ok(newToken);
        }

        return Unauthorized(new { message = "Token is invalid or expired" });
    }
}
