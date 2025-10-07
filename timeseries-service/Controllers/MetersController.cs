using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using OmarinoEMS.TimeSeriesService.Data;
using OmarinoEMS.TimeSeriesService.DTOs;
using OmarinoEMS.TimeSeriesService.Models;

namespace OmarinoEMS.TimeSeriesService.Controllers;

[ApiController]
[Route("api/[controller]")]
[Produces("application/json")]
public class MetersController : ControllerBase
{
    private readonly TimeSeriesDbContext _context;
    private readonly ILogger<MetersController> _logger;

    public MetersController(TimeSeriesDbContext context, ILogger<MetersController> logger)
    {
        _context = context;
        _logger = logger;
    }

    /// <summary>
    /// Get all meters with optional filtering.
    /// </summary>
    [HttpGet]
    [ProducesResponseType(typeof(List<MeterResponse>), StatusCodes.Status200OK)]
    public async Task<ActionResult<List<MeterResponse>>> GetMeters(
        [FromQuery] Guid? siteId = null,
        [FromQuery] MeterType? type = null,
        CancellationToken cancellationToken = default)
    {
        var query = _context.Meters.AsQueryable();

        if (siteId.HasValue)
            query = query.Where(m => m.SiteId == siteId.Value);

        if (type.HasValue)
            query = query.Where(m => m.Type == type.Value);

        var meters = await query.ToListAsync(cancellationToken);
        return Ok(meters.Select(MapToResponse));
    }

    /// <summary>
    /// Get a specific meter by ID.
    /// </summary>
    [HttpGet("{id:guid}")]
    [ProducesResponseType(typeof(MeterResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<MeterResponse>> GetMeter(Guid id, CancellationToken cancellationToken)
    {
        var meter = await _context.Meters
            .Include(m => m.Series)
            .FirstOrDefaultAsync(m => m.Id == id, cancellationToken);

        if (meter == null)
            return NotFound(new { message = $"Meter {id} not found" });

        return Ok(MapToResponse(meter));
    }

    /// <summary>
    /// Create a new meter.
    /// </summary>
    [HttpPost]
    [ProducesResponseType(typeof(MeterResponse), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<MeterResponse>> CreateMeter(
        [FromBody] CreateMeterRequest request,
        CancellationToken cancellationToken)
    {
        // Validate timezone
        try
        {
            TimeZoneInfo.FindSystemTimeZoneById(request.Timezone);
        }
        catch (TimeZoneNotFoundException)
        {
            return BadRequest(new { message = $"Invalid timezone: {request.Timezone}" });
        }

        var meter = new Meter
        {
            Id = Guid.NewGuid(),
            Name = request.Name,
            Type = request.Type,
            Latitude = request.Latitude,
            Longitude = request.Longitude,
            Address = request.Address,
            SiteId = request.SiteId,
            SamplingInterval = request.SamplingInterval,
            Timezone = request.Timezone,
            Tags = request.Tags
        };

        _context.Meters.Add(meter);
        await _context.SaveChangesAsync(cancellationToken);

        _logger.LogInformation("Created meter {MeterId} with name {MeterName}", meter.Id, meter.Name);

        return CreatedAtAction(nameof(GetMeter), new { id = meter.Id }, MapToResponse(meter));
    }

    /// <summary>
    /// Update an existing meter.
    /// </summary>
    [HttpPut("{id:guid}")]
    [ProducesResponseType(typeof(MeterResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<MeterResponse>> UpdateMeter(
        Guid id,
        [FromBody] CreateMeterRequest request,
        CancellationToken cancellationToken)
    {
        var meter = await _context.Meters.FindAsync(new object[] { id }, cancellationToken);
        if (meter == null)
            return NotFound(new { message = $"Meter {id} not found" });

        meter.Name = request.Name;
        meter.Type = request.Type;
        meter.Latitude = request.Latitude;
        meter.Longitude = request.Longitude;
        meter.Address = request.Address;
        meter.SiteId = request.SiteId;
        meter.SamplingInterval = request.SamplingInterval;
        meter.Timezone = request.Timezone;
        meter.Tags = request.Tags;

        await _context.SaveChangesAsync(cancellationToken);

        _logger.LogInformation("Updated meter {MeterId}", meter.Id);

        return Ok(MapToResponse(meter));
    }

    /// <summary>
    /// Delete a meter and all associated series/points.
    /// </summary>
    [HttpDelete("{id:guid}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> DeleteMeter(Guid id, CancellationToken cancellationToken)
    {
        var meter = await _context.Meters.FindAsync(new object[] { id }, cancellationToken);
        if (meter == null)
            return NotFound(new { message = $"Meter {id} not found" });

        _context.Meters.Remove(meter);
        await _context.SaveChangesAsync(cancellationToken);

        _logger.LogInformation("Deleted meter {MeterId}", meter.Id);

        return NoContent();
    }

    private static MeterResponse MapToResponse(Meter meter) => new(
        meter.Id,
        meter.Name,
        meter.Type,
        meter.Latitude,
        meter.Longitude,
        meter.Address,
        meter.SiteId,
        meter.SamplingInterval,
        meter.Timezone,
        meter.Tags,
        meter.CommissionedAt,
        meter.DecommissionedAt,
        meter.CreatedAt,
        meter.UpdatedAt
    );
}
