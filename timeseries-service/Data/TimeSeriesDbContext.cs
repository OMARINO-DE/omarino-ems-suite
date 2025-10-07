using Microsoft.EntityFrameworkCore;
using OmarinoEMS.TimeSeriesService.Models;

namespace OmarinoEMS.TimeSeriesService.Data;

public class TimeSeriesDbContext : DbContext
{
    public TimeSeriesDbContext(DbContextOptions<TimeSeriesDbContext> options)
        : base(options)
    {
    }

    public DbSet<Meter> Meters => Set<Meter>();
    public DbSet<Series> Series => Set<Series>();
    public DbSet<TimeSeriesPoint> TimeSeriesPoints => Set<TimeSeriesPoint>();
    public DbSet<ImportJob> ImportJobs => Set<ImportJob>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // Meter configuration
        modelBuilder.Entity<Meter>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Name).IsRequired().HasMaxLength(255);
            entity.Property(e => e.Type).IsRequired().HasConversion<int>();
            entity.Property(e => e.Timezone).IsRequired().HasMaxLength(100);
            
            // Store tags as JSONB
            entity.Property(e => e.Tags)
                .HasColumnType("jsonb");
            
            // Indexes
            entity.HasIndex(e => e.Name);
            entity.HasIndex(e => e.Type);
            entity.HasIndex(e => e.SiteId);
        });

        // Series configuration
        modelBuilder.Entity<Series>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Name).IsRequired().HasMaxLength(255);
            entity.Property(e => e.Unit).IsRequired().HasMaxLength(50);
            entity.Property(e => e.Aggregation).IsRequired().HasConversion<int>().HasColumnName("AggregationMethod");
            // DataType property temporarily removed from model - column doesn't exist in current database schema
            
            // Foreign key
            entity.HasOne(e => e.Meter)
                .WithMany(m => m.Series)
                .HasForeignKey(e => e.MeterId)
                .OnDelete(DeleteBehavior.Cascade);
            
            // Indexes
            entity.HasIndex(e => e.MeterId);
            entity.HasIndex(e => e.Name);
            // Temporarily removed DataType index - column doesn't exist in current database schema
            // entity.HasIndex(e => e.DataType);
        });

        // TimeSeriesPoint configuration (Timescale hypertable)
        modelBuilder.Entity<TimeSeriesPoint>(entity =>
        {
            // Composite primary key: Id + Timestamp (required by TimescaleDB hypertable)
            entity.HasKey(e => new { e.Id, e.Timestamp });
            
            entity.Property(e => e.Quality).IsRequired().HasConversion<int>();
            entity.Property(e => e.Source).HasMaxLength(255);
            
            // Store metadata as JSONB
            entity.Property(e => e.Metadata)
                .HasColumnType("jsonb");
            
            // Foreign key
            entity.HasOne(e => e.Series)
                .WithMany(s => s.Points)
                .HasForeignKey(e => e.SeriesId)
                .OnDelete(DeleteBehavior.Cascade);
            
            // Indexes
            entity.HasIndex(e => e.Timestamp);
            entity.HasIndex(e => e.Quality);
            entity.HasIndex(e => new { e.SeriesId, e.Timestamp, e.Version });
            
            // Note: Hypertable conversion happens in migration
            // Changed from "time_series_points" to match actual database table name
            entity.ToTable("DataPoints");
        });

        // ImportJob configuration
        modelBuilder.Entity<ImportJob>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Source).IsRequired().HasMaxLength(1000);
            entity.Property(e => e.Status).IsRequired().HasConversion<int>();
            
            entity.Property(e => e.Metadata)
                .HasColumnType("jsonb");
            
            // Indexes
            entity.HasIndex(e => e.Status);
            entity.HasIndex(e => e.StartedAt);
        });
    }

    public override int SaveChanges()
    {
        UpdateTimestamps();
        return base.SaveChanges();
    }

    public override Task<int> SaveChangesAsync(CancellationToken cancellationToken = default)
    {
        UpdateTimestamps();
        return base.SaveChangesAsync(cancellationToken);
    }

    private void UpdateTimestamps()
    {
        var now = DateTime.UtcNow;
        var entries = ChangeTracker.Entries()
            .Where(e => e.State == EntityState.Added || e.State == EntityState.Modified);

        foreach (var entry in entries)
        {
            if (entry.Entity is Meter meter)
            {
                if (entry.State == EntityState.Added)
                    meter.CreatedAt = now;
                meter.UpdatedAt = now;
            }
            else if (entry.Entity is Series series)
            {
                if (entry.State == EntityState.Added)
                    series.CreatedAt = now;
                series.UpdatedAt = now;
            }
            else if (entry.Entity is ImportJob job && entry.State == EntityState.Added)
            {
                job.StartedAt = now;
            }
            else if (entry.Entity is TimeSeriesPoint point && entry.State == EntityState.Added)
            {
                point.CreatedAt = now;
            }
        }
    }
}
