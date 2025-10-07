using OmarinoEms.ApiGateway.Models;

namespace OmarinoEms.ApiGateway.Services;

/// <summary>
/// Interface for JWT token generation and validation.
/// </summary>
public interface ITokenService
{
    /// <summary>
    /// Generates a JWT token for the specified user.
    /// </summary>
    /// <param name="username">The username</param>
    /// <param name="roles">The user's roles</param>
    /// <returns>Token response containing the JWT token</returns>
    TokenResponse GenerateToken(string username, IEnumerable<string> roles);

    /// <summary>
    /// Validates a JWT token.
    /// </summary>
    /// <param name="token">The token to validate</param>
    /// <returns>True if valid, false otherwise</returns>
    bool ValidateToken(string token);
}
