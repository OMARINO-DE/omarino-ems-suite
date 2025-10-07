using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using OmarinoEMS.TimeSeriesService.Data;
using OmarinoEMS.TimeSeriesService.DTOs;
using OmarinoEMS.TimeSeriesService.Models;

namespace OmarinoEMS.TimeSeriesService.Controllers;

[ApiController]
[Route("api/[controller]")]
[Produces("application/json")]
public class IngestController : ControllerBase
{
    private readonly TimeSeriesDbContext _context;
    private readonly ILogger<IngestController> _logger;

    public IngestController(TimeSeriesDbContext context, ILogger<IngestController> logger)
    {
        _context = context;
        _logger = logger;
    }

    /// <summary>
    /// Bulk ingest time series data points.
    /// Supports upsert (insert or update based on version).
    /// </summary>
    [HttpPost]
    [ProducesResponseType(typeof(IngestResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<IngestResponse>> IngestData(
        [FromBody] IngestRequest request,
        CancellationToken cancellationToken)
    {
        var job = new ImportJob
        {
            Id = Guid.NewGuid(),
            Source = request.Source,
            Status = ImportStatus.Running
        };

        _context.ImportJobs.Add(job);
        await _context.SaveChangesAsync(cancellationToken);

        var errors = new List<string>();
        var imported = 0;
        var failed = 0;

        try
        {
            // Group points by series for efficient processing
            var pointsBySeriesId = request.Points.GroupBy(p => p.SeriesId);

            foreach (var group in pointsBySeriesId)
            {
                var seriesId = group.Key;
                
                // Verify series exists
                var seriesExists = await _context.Series.AnyAsync(s => s.Id == seriesId, cancellationToken);
                if (!seriesExists)
                {
                    var error = $"Series {seriesId} not found";
                    errors.Add(error);
                    failed += group.Count();
                    continue;
                }

                foreach (var pointDto in group)
                {
                    try
                    {
                        var timestamp = pointDto.Timestamp.ToUniversalTime();
                        
                        // Check if point already exists (find by SeriesId and Timestamp, not by composite PK)
                        var existingPoint = await _context.TimeSeriesPoints
                            .FirstOrDefaultAsync(p => p.SeriesId == seriesId && p.Timestamp == timestamp, cancellationToken);

                        if (existingPoint != null)
                        {
                            // Update if new version is higher
                            if (pointDto.Version > existingPoint.Version)
                            {
                                existingPoint.Value = pointDto.Value;
                                existingPoint.Quality = pointDto.Quality;
                                existingPoint.Source = pointDto.Source;
                                existingPoint.Version = pointDto.Version;
                                existingPoint.Metadata = pointDto.Metadata;
                                imported++;
                            }
                            else
                            {
                                // Skip - existing version is same or newer
                                continue;
                            }
                        }
                        else
                        {
                            // Insert new point
                            var point = new TimeSeriesPoint
                            {
                                Id = Guid.NewGuid(), // Generate new Id for the data point
                                SeriesId = seriesId,
                                Timestamp = timestamp,
                                Value = pointDto.Value,
                                Quality = pointDto.Quality,
                                Source = pointDto.Source,
                                Version = pointDto.Version,
                                Metadata = pointDto.Metadata
                            };
                            _context.TimeSeriesPoints.Add(point);
                            imported++;
                        }
                    }
                    catch (Exception ex)
                    {
                        errors.Add($"Failed to import point at {pointDto.Timestamp}: {ex.Message}");
                        failed++;
                    }
                }
            }

            await _context.SaveChangesAsync(cancellationToken);

            job.Status = failed == 0 ? ImportStatus.Completed : ImportStatus.Failed;
            job.PointsImported = imported;
            job.PointsFailed = failed;
            job.CompletedAt = DateTime.UtcNow;
            
            if (errors.Any())
                job.ErrorMessage = string.Join("; ", errors.Take(10)); // Store first 10 errors

            await _context.SaveChangesAsync(cancellationToken);

            _logger.LogInformation(
                "Import job {JobId} completed: {Imported} imported, {Failed} failed",
                job.Id, imported, failed);

            return Ok(new IngestResponse(job.Id, imported, failed, errors.Any() ? errors : null));
        }
        catch (Exception ex)
        {
            job.Status = ImportStatus.Failed;
            job.PointsFailed = request.Points.Count;
            job.ErrorMessage = ex.Message;
            job.CompletedAt = DateTime.UtcNow;
            await _context.SaveChangesAsync(cancellationToken);

            _logger.LogError(ex, "Import job {JobId} failed", job.Id);
            
            return BadRequest(new { message = "Import failed", error = ex.Message, jobId = job.Id });
        }
    }

    /// <summary>
    /// Get import job status and results.
    /// </summary>
    [HttpGet("jobs/{jobId:guid}")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult> GetImportJob(Guid jobId, CancellationToken cancellationToken)
    {
        var job = await _context.ImportJobs.FindAsync(new object[] { jobId }, cancellationToken);
        if (job == null)
            return NotFound(new { message = $"Import job {jobId} not found" });

        return Ok(new
        {
            job.Id,
            job.Source,
            job.Status,
            job.PointsImported,
            job.PointsFailed,
            job.ErrorMessage,
            StartedAt = job.StartedAt,
            CompletedAt = job.CompletedAt
        });
    }
}
