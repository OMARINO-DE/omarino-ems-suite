namespace OmarinoEMS.TimeSeriesService.Models;

/// <summary>
/// Represents a time series linked to a meter.
/// </summary>
public class Series
{
    public Guid Id { get; set; }
    public Guid MeterId { get; set; }
    public required string Name { get; set; }
    public string? Description { get; set; }
    public required string Unit { get; set; }
    public required AggregationType Aggregation { get; set; }
    // Temporarily removed DataType property - column doesn't exist in current database schema
    // public DataType DataType { get; set; } = DataType.Measurement;
    // Temporarily removed Timezone property - column doesn't exist in current database schema
    // public string? Timezone { get; set; } // Inherits from meter if null
    
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
    
    // Navigation properties
    public Meter Meter { get; set; } = null!;
    public ICollection<TimeSeriesPoint> Points { get; set; } = new List<TimeSeriesPoint>();
}

public enum AggregationType
{
    Instant,
    Mean,
    Sum,
    Min,
    Max,
    Count
}

public enum DataType
{
    Measurement,
    Forecast,
    Schedule,
    Price,
    Weather
}
