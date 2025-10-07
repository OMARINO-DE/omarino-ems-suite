namespace OmarinoEms.ApiGateway.Models;

/// <summary>
/// Response model for JWT token generation.
/// </summary>
public class TokenResponse
{
    /// <summary>
    /// The JWT token string.
    /// </summary>
    public string Token { get; set; } = string.Empty;

    /// <summary>
    /// The token type (e.g., "Bearer").
    /// </summary>
    public string TokenType { get; set; } = "Bearer";

    /// <summary>
    /// The UTC timestamp when the token expires.
    /// </summary>
    public DateTime ExpiresAt { get; set; }

    /// <summary>
    /// The token expiration time in seconds from now.
    /// </summary>
    public int ExpiresIn => (int)(ExpiresAt - DateTime.UtcNow).TotalSeconds;
}
