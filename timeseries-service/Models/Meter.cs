namespace OmarinoEMS.TimeSeriesService.Models;

/// <summary>
/// Represents a physical or virtual metering device.
/// </summary>
public class Meter
{
    public Guid Id { get; set; }
    public required string Name { get; set; }
    public required MeterType Type { get; set; }
    
    // Location
    public double? Latitude { get; set; }
    public double? Longitude { get; set; }
    public string? Address { get; set; }
    public Guid? SiteId { get; set; }
    
    // Configuration
    public int? SamplingInterval { get; set; } // Sampling interval in seconds
    public required string Timezone { get; set; } // IANA timezone
    
    // Tags (stored as JSONB in PostgreSQL)
    public Dictionary<string, string>? Tags { get; set; }
    
    // Lifecycle
    public DateTime? CommissionedAt { get; set; }
    public DateTime? DecommissionedAt { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
    
    // Navigation properties
    public ICollection<Series> Series { get; set; } = new List<Series>();
}

public enum MeterType
{
    Electricity,
    Gas,
    Water,
    Heat,
    Virtual
}
