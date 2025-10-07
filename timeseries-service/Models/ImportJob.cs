namespace OmarinoEMS.TimeSeriesService.Models;

/// <summary>
/// Tracks data import jobs for auditing and monitoring.
/// </summary>
public class ImportJob
{
    public Guid Id { get; set; }
    public required string Source { get; set; } // e.g., "file:///samples/meters.csv"
    public ImportStatus Status { get; set; } = ImportStatus.Running;
    public int PointsImported { get; set; }
    public int PointsFailed { get; set; }
    public string? ErrorMessage { get; set; }
    
    public DateTime StartedAt { get; set; }
    public DateTime? CompletedAt { get; set; }
    
    // Metadata about the import
    public Dictionary<string, object>? Metadata { get; set; }
}

public enum ImportStatus
{
    Running,
    Completed,
    Failed,
    Cancelled
}
