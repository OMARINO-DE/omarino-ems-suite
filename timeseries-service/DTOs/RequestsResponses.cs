using System.ComponentModel.DataAnnotations;
using OmarinoEMS.TimeSeriesService.Models;

namespace OmarinoEMS.TimeSeriesService.DTOs;

public record CreateMeterRequest(
    [Required] string Name,
    [Required] MeterType Type,
    double? Latitude,
    double? Longitude,
    string? Address,
    Guid? SiteId,
    int? SamplingInterval,
    [Required] string Timezone,
    Dictionary<string, string>? Tags
);

public record MeterResponse(
    Guid Id,
    string Name,
    MeterType Type,
    double? Latitude,
    double? Longitude,
    string? Address,
    Guid? SiteId,
    int? SamplingInterval,
    string Timezone,
    Dictionary<string, string>? Tags,
    DateTime? CommissionedAt,
    DateTime? DecommissionedAt,
    DateTime CreatedAt,
    DateTime UpdatedAt
);

public record CreateSeriesRequest(
    [Required] Guid MeterId,
    [Required] string Name,
    string? Description,
    [Required] string Unit,
    [Required] AggregationType Aggregation
    // Temporarily removed DataType - column doesn't exist in current database schema
    // Models.DataType DataType,
    // Temporarily removed Timezone - column doesn't exist in current database schema
    // string? Timezone
);

public record SeriesResponse(
    Guid Id,
    Guid MeterId,
    string Name,
    string? Description,
    string Unit,
    AggregationType Aggregation,
    // Temporarily removed DataType - column doesn't exist in current database schema
    // Models.DataType DataType,
    // Temporarily removed Timezone - column doesn't exist in current database schema
    // string? Timezone,
    DateTime CreatedAt,
    DateTime UpdatedAt
);

public record TimeSeriesPointDto(
    Guid SeriesId,
    DateTime Timestamp,
    double Value,
    string? Unit,
    DataQuality Quality,
    string? Source,
    int Version,
    Dictionary<string, object>? Metadata
);

public record IngestRequest(
    [Required] string Source,
    [Required] List<TimeSeriesPointDto> Points
);

public record IngestResponse(
    Guid JobId,
    int PointsImported,
    int PointsFailed,
    List<string>? Errors
);

public record QueryRequest(
    [Required] Guid SeriesId,
    [Required] DateTime From,
    [Required] DateTime To,
    string? Aggregation = "mean",
    string? Interval = null // e.g., "15m", "1h", "1d"
);

public record QueryResponse(
    Guid SeriesId,
    List<TimeSeriesPointDto> Points
);
