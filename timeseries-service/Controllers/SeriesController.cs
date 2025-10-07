using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using OmarinoEMS.TimeSeriesService.Data;
using OmarinoEMS.TimeSeriesService.DTOs;
using OmarinoEMS.TimeSeriesService.Models;

namespace OmarinoEMS.TimeSeriesService.Controllers;

[ApiController]
[Route("api/[controller]")]
[Produces("application/json")]
public class SeriesController : ControllerBase
{
    private readonly TimeSeriesDbContext _context;
    private readonly ILogger<SeriesController> _logger;

    public SeriesController(TimeSeriesDbContext context, ILogger<SeriesController> logger)
    {
        _context = context;
        _logger = logger;
    }

    /// <summary>
    /// Get all series for a specific meter.
    /// </summary>
    [HttpGet]
    [ProducesResponseType(typeof(List<SeriesResponse>), StatusCodes.Status200OK)]
    public async Task<ActionResult<List<SeriesResponse>>> GetSeries(
        [FromQuery] Guid? meterId = null,
        // Temporarily removed DataType filter - column doesn't exist in current database schema
        // [FromQuery] DataType? dataType = null,
        CancellationToken cancellationToken = default)
    {
        var query = _context.Series.AsQueryable();

        if (meterId.HasValue)
            query = query.Where(s => s.MeterId == meterId.Value);

        // Temporarily removed DataType filter - column doesn't exist in current database schema
        // if (dataType.HasValue)
        //     query = query.Where(s => s.DataType == dataType.Value);

        var series = await query.ToListAsync(cancellationToken);
        return Ok(series.Select(MapToResponse));
    }

    /// <summary>
    /// Get a specific series by ID.
    /// </summary>
    [HttpGet("{id:guid}")]
    [ProducesResponseType(typeof(SeriesResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<SeriesResponse>> GetSeriesById(Guid id, CancellationToken cancellationToken)
    {
        var series = await _context.Series.FindAsync(new object[] { id }, cancellationToken);
        if (series == null)
            return NotFound(new { message = $"Series {id} not found" });

        return Ok(MapToResponse(series));
    }

    /// <summary>
    /// Create a new time series.
    /// </summary>
    [HttpPost]
    [ProducesResponseType(typeof(SeriesResponse), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<SeriesResponse>> CreateSeries(
        [FromBody] CreateSeriesRequest request,
        CancellationToken cancellationToken)
    {
        // Verify meter exists
        var meterExists = await _context.Meters.AnyAsync(m => m.Id == request.MeterId, cancellationToken);
        if (!meterExists)
            return NotFound(new { message = $"Meter {request.MeterId} not found" });

        var series = new Series
        {
            Id = Guid.NewGuid(),
            MeterId = request.MeterId,
            Name = request.Name,
            Description = request.Description,
            Unit = request.Unit,
            Aggregation = request.Aggregation
            // Temporarily removed DataType - column doesn't exist in current database schema
            // DataType = request.DataType,
            // Temporarily removed Timezone - column doesn't exist in current database schema
            // Timezone = request.Timezone
        };

        _context.Series.Add(series);
        await _context.SaveChangesAsync(cancellationToken);

        _logger.LogInformation("Created series {SeriesId} for meter {MeterId}", series.Id, series.MeterId);

        return CreatedAtAction(nameof(GetSeriesById), new { id = series.Id }, MapToResponse(series));
    }

    /// <summary>
    /// Query time series data with optional aggregation.
    /// </summary>
    [HttpGet("{id:guid}/range")]
    [ProducesResponseType(typeof(QueryResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<QueryResponse>> QuerySeriesData(
        Guid id,
        [FromQuery] DateTime from,
        [FromQuery] DateTime to,
        [FromQuery] string? agg = null,
        [FromQuery] string? interval = null,
        CancellationToken cancellationToken = default)
    {
        var series = await _context.Series.FindAsync(new object[] { id }, cancellationToken);
        if (series == null)
            return NotFound(new { message = $"Series {id} not found" });

        var fromUtc = from.ToUniversalTime();
        var toUtc = to.ToUniversalTime();

        var query = _context.TimeSeriesPoints
            .Where(p => p.SeriesId == id)
            .Where(p => p.Timestamp >= fromUtc && p.Timestamp <= toUtc)
            .OrderBy(p => p.Timestamp);

        var points = await query.ToListAsync(cancellationToken);

        var response = new QueryResponse(
            id,
            points.Select(p => new TimeSeriesPointDto(
                p.SeriesId,
                p.Timestamp,
                p.Value,
                series.Unit,
                p.Quality,
                p.Source,
                p.Version,
                p.Metadata
            )).ToList()
        );

        return Ok(response);
    }

    /// <summary>
    /// Delete a series and all associated data points.
    /// </summary>
    [HttpDelete("{id:guid}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> DeleteSeries(Guid id, CancellationToken cancellationToken)
    {
        var series = await _context.Series.FindAsync(new object[] { id }, cancellationToken);
        if (series == null)
            return NotFound(new { message = $"Series {id} not found" });

        _context.Series.Remove(series);
        await _context.SaveChangesAsync(cancellationToken);

        _logger.LogInformation("Deleted series {SeriesId}", series.Id);

        return NoContent();
    }

    private static SeriesResponse MapToResponse(Series series) => new(
        series.Id,
        series.MeterId,
        series.Name,
        series.Description,
        series.Unit,
        series.Aggregation,
        // Temporarily removed DataType - column doesn't exist in current database schema
        // series.DataType,
        // Temporarily removed Timezone - column doesn't exist in current database schema
        // series.Timezone,
        series.CreatedAt,
        series.UpdatedAt
    );
}
