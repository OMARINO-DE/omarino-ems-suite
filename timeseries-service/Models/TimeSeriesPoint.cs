namespace OmarinoEMS.TimeSeriesService.Models;

/// <summary>
/// Represents a single data point in a time series.
/// Stored in Timescale hypertable for efficient time-series queries.
/// </summary>
public class TimeSeriesPoint
{
    public Guid Id { get; set; } // Primary key column in database
    public Guid SeriesId { get; set; }
    public DateTime Timestamp { get; set; }
    public double Value { get; set; }
    public DataQuality Quality { get; set; } = DataQuality.Good;
    public string? Source { get; set; }
    public int Version { get; set; } = 1;
    
    // Metadata (stored as JSONB)
    public Dictionary<string, object>? Metadata { get; set; }
    
    // Timestamp when the record was created in the database
    public DateTime CreatedAt { get; set; }
    
    // Navigation property
    public Series Series { get; set; } = null!;
}

public enum DataQuality
{
    Good,
    Uncertain,
    Bad,
    Estimated,
    Missing
}
