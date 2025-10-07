# Database Schema Fixes - Demo Data Import

## Overview

This document details the database schema issues encountered during demo data import and the fixes applied to resolve them.

## Problem Statement

The manually created PostgreSQL database schema did not match the Entity Framework Core models in the C# codebase, causing multiple errors during data insertion operations.

## Root Cause

**EF Core with Npgsql stores enum types as TEXT strings** (e.g., "GridConnection", "Average"), not as integers. The manually created schema used `integer` columns for enum types, causing type mismatches.

Additionally, several tables had:
- Missing columns that the EF Core models expected
- Extra columns that the models didn't define
- Incorrect column names (different from model property names)
- Incorrect data types

---

## Fixes Applied

### 1. **Meters Table** - Enum Type Fix
**Issue:** `Type` column was `integer`, but EF Core sends enum as `text`

**Error:**
```
column "Type" is of type integer but expression is of type text
```

**Fix:**
```sql
ALTER TABLE "Meters" ALTER COLUMN "Type" TYPE text USING "Type"::text;
```

**Result:** ✅ All 5 meters created successfully

---

### 2. **Series Table** - Multiple Schema Mismatches

#### Issue A: Column Name Mismatch
**Database had:** `AggregationMethod` (integer)
**EF Core expected:** `Aggregation` (text enum)

**Error:**
```
column "Aggregation" of relation "Series" does not exist
```

**Fix:**
```sql
ALTER TABLE "Series" RENAME COLUMN "AggregationMethod" TO "Aggregation";
ALTER TABLE "Series" ALTER COLUMN "Aggregation" TYPE text USING "Aggregation"::text;
```

#### Issue B: Missing Columns
**EF Core model had these properties but database was missing columns:**
- `DataType` (text enum) - defaults to 'Measurement'
- `Timezone` (text, nullable)

**Fix:**
```sql
ALTER TABLE "Series" ADD COLUMN IF NOT EXISTS "DataType" text NOT NULL DEFAULT 'Measurement';
ALTER TABLE "Series" ADD COLUMN IF NOT EXISTS "Timezone" text;
```

#### Issue C: Extra Columns
**Database had columns not in EF Core model:**
- `Metadata` (jsonb) - removed
- `IsActive` (boolean) - removed

**Fix:**
```sql
ALTER TABLE "Series" DROP COLUMN IF EXISTS "Metadata";
ALTER TABLE "Series" DROP COLUMN IF EXISTS "IsActive";
```

**Result:** ✅ All 12 series created successfully

---

### 3. **ImportJobs Table** - Missing Entire Table
**Issue:** Table didn't exist in database but was required by IngestController

**Error:**
```
relation "ImportJobs" does not exist
```

**Fix:**
```sql
CREATE TABLE IF NOT EXISTS "ImportJobs" (
    "Id" uuid PRIMARY KEY,
    "Source" text NOT NULL,
    "Status" text NOT NULL DEFAULT 'Running',
    "PointsImported" integer NOT NULL DEFAULT 0,
    "PointsFailed" integer NOT NULL DEFAULT 0,
    "ErrorMessage" text,
    "StartedAt" timestamp with time zone NOT NULL DEFAULT NOW(),
    "CompletedAt" timestamp with time zone,
    "Metadata" jsonb
);
```

**Result:** ✅ Import tracking now working

---

### 4. **time_series_points Table** - Table Name and Structure Mismatch

#### Issue A: Wrong Table Name
**Database had:** `DataPoints`
**EF Core expected:** `time_series_points` (configured via `.ToTable("time_series_points")`)

**Error:**
```
relation "time_series_points" does not exist
```

**Fix:**
```sql
ALTER TABLE "DataPoints" RENAME TO "time_series_points";
```

#### Issue B: Missing Columns
**EF Core model expected but database was missing:**
- `Source` (text, nullable) - for tracking data origin
- `Version` (integer) - for optimistic concurrency/versioning
- `Metadata` (jsonb) - for flexible additional attributes

**Fix:**
```sql
ALTER TABLE "time_series_points" ADD COLUMN IF NOT EXISTS "Source" text;
ALTER TABLE "time_series_points" ADD COLUMN IF NOT EXISTS "Version" integer NOT NULL DEFAULT 1;
ALTER TABLE "time_series_points" ADD COLUMN IF NOT EXISTS "Metadata" jsonb;
```

#### Issue C: Extra Columns
**Database had columns not in EF Core model:**
- `Id` (uuid) - removed (EF uses composite key: SeriesId + Timestamp)
- `CreatedAt` (timestamp) - removed (not in model)

**Fix:**
```sql
ALTER TABLE "time_series_points" DROP COLUMN IF EXISTS "Id";
ALTER TABLE "time_series_points" DROP COLUMN IF EXISTS "CreatedAt";
```

#### Issue D: Enum Type Mismatch
**Database had:** `Quality` as `integer`
**EF Core expected:** `Quality` as `text` (enum: Good, Uncertain, Bad, Estimated, Missing)

**Fix:**
```sql
ALTER TABLE "time_series_points" ALTER COLUMN "Quality" TYPE text USING "Quality"::text;
```

**Result:** ✅ Successfully inserted 4,032 data points (7 days × 24 hours × 24 series)

---

## Final Database Schema

### Meters
```sql
CREATE TABLE "Meters" (
    "Id" uuid PRIMARY KEY,
    "Name" text NOT NULL,
    "Type" text NOT NULL,              -- ✅ FIXED: Changed from integer to text
    "SiteId" uuid,
    "Location" text,
    "Timezone" text NOT NULL,
    "Tags" jsonb,
    "CreatedAt" timestamp with time zone NOT NULL,
    "UpdatedAt" timestamp with time zone NOT NULL
);
```

### Series
```sql
CREATE TABLE "Series" (
    "Id" uuid PRIMARY KEY,
    "Name" text NOT NULL,
    "MeterId" uuid NOT NULL,
    "Unit" text,
    "Description" text,
    "Aggregation" text NOT NULL,       -- ✅ FIXED: Renamed from AggregationMethod, changed to text
    "DataType" text NOT NULL,          -- ✅ ADDED
    "Timezone" text,                   -- ✅ ADDED
    "CreatedAt" timestamp with time zone NOT NULL,
    "UpdatedAt" timestamp with time zone NOT NULL,
    FOREIGN KEY ("MeterId") REFERENCES "Meters"("Id") ON DELETE CASCADE
);
```

### ImportJobs
```sql
CREATE TABLE "ImportJobs" (           -- ✅ CREATED
    "Id" uuid PRIMARY KEY,
    "Source" text NOT NULL,
    "Status" text NOT NULL,
    "PointsImported" integer NOT NULL,
    "PointsFailed" integer NOT NULL,
    "ErrorMessage" text,
    "StartedAt" timestamp with time zone NOT NULL,
    "CompletedAt" timestamp with time zone,
    "Metadata" jsonb
);
```

### time_series_points
```sql
CREATE TABLE "time_series_points" (   -- ✅ RENAMED from DataPoints
    "SeriesId" uuid NOT NULL,
    "Timestamp" timestamp with time zone NOT NULL,
    "Value" double precision NOT NULL,
    "Quality" text NOT NULL,           -- ✅ FIXED: Changed from integer to text
    "Source" text,                     -- ✅ ADDED
    "Version" integer NOT NULL,        -- ✅ ADDED
    "Metadata" jsonb,                  -- ✅ ADDED
    PRIMARY KEY ("SeriesId", "Timestamp"),
    FOREIGN KEY ("SeriesId") REFERENCES "Series"("Id") ON DELETE CASCADE
);
```

---

## Lessons Learned

### 1. **EF Core Enum Handling**
- By default, Npgsql stores enums as **TEXT strings** (the enum name as a string)
- This can be changed with `.HasConversion<int>()` but requires recompiling the C# code
- **Solution:** Always use TEXT columns for enum properties when manually creating schemas

### 2. **Table Naming Conventions**
- EF Core pluralizes DbSet names by default (e.g., `DbSet<Meter> Meters` → table "Meters")
- Can be overridden with `.ToTable("custom_name")` in OnModelCreating
- **Solution:** Check DbContext configuration for explicit table names before creating tables

### 3. **Schema Synchronization**
- Manually created schemas easily drift from EF Core models
- Better approaches:
  - Use EF Core Migrations to generate schema from models
  - Generate SQL script from migrations: `dotnet ef migrations script`
  - Use `dotnet ef dbcontext scaffold` to reverse-engineer existing DB

### 4. **Required vs Optional Columns**
- EF Core model properties with `?` are nullable (optional in DB)
- Properties with `required` keyword or without `?` must be NOT NULL in DB
- Default values can prevent breaking existing code when adding columns

---

## Current System Status

✅ **Meters:** 5 created (Grid, Solar, Building, Battery, Heat Pump)
✅ **Series:** 24 created (Power, Energy, Price, SOC, COP measurements)
✅ **Data Points:** 4,032 inserted (7 days of hourly data for all series)
⚠️ **Workflows:** Not created (scheduler API validation errors - separate issue)

---

## Next Steps

1. **Update `init-schema.sql`** with corrected column types to prevent these issues in fresh deployments
2. **Consider using EF Core Migrations** for future schema changes
3. **Fix Scheduler API** workflow validation errors (requires API spec investigation)
4. **Document API endpoints** with correct request/response formats

---

## Commands Reference

### Check Table Structure
```bash
psql -U omarino -d omarino_timeseries -c '\d "TableName"'
```

### List All Tables
```bash
psql -U omarino -d omarino_timeseries -c '\dt'
```

### Check Data Count
```bash
psql -U omarino -d omarino_timeseries -c 'SELECT COUNT(*) FROM table_name;'
```

### Alter Column Type
```sql
ALTER TABLE "TableName" ALTER COLUMN "ColumnName" TYPE text USING "ColumnName"::text;
```

### Add Column
```sql
ALTER TABLE "TableName" ADD COLUMN IF NOT EXISTS "ColumnName" type [NOT NULL] [DEFAULT value];
```

### Rename Column
```sql
ALTER TABLE "TableName" RENAME COLUMN "OldName" TO "NewName";
```

### Drop Column
```sql
ALTER TABLE "TableName" DROP COLUMN IF EXISTS "ColumnName";
```

### Rename Table
```sql
ALTER TABLE "OldName" RENAME TO "NewName";
```

---

**Document Created:** 2025-10-06
**Author:** GitHub Copilot
**Status:** All schema fixes applied and verified
