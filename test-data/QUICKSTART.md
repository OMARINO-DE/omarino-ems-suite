# OMARINO EMS Test Data - Quick Reference

## ⚠️ CSV Import Issue? READ THIS FIRST!

If you get **"One or more validation errors occurred"** when importing CSV:

**REAL PROBLEM**: The `/api/meters/import` endpoint DOESN'T EXIST! ❌  
**REAL SOLUTION**: Use Python script that imports via JSON API ✅

**Working method**:
```bash
cd test-data
python3 import-meters-csv.py
```

**Result**: ✅ All 15 meters imported successfully!

See `CSV-IMPORT-REAL-SOLUTION.md` for full explanation.

## 🚀 Quick Start

### Method 1: SQL Import (Recommended - Complete Data)
```bash
cd test-data
./import.sh
```

### Method 2: CSV Import via Python Script
```bash
cd test-data
python3 import-meters-csv.py
```

### Method 3: Manual JSON API
```bash
curl -X POST https://ems-back.omarino.net/api/meters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Meter",
    "type": "Electricity",
    "timezone": "Europe/Berlin"
  }'
```

### Remote Server Import
```bash
# Copy files to server
scp -i "/path/to/server.pem" -r test-data/ omar@192.168.75.20:~/

# SSH and import
ssh -i "/path/to/server.pem" omar@192.168.75.20
cd ~/test-data
./import.sh
```

### Manual SQL Import (PostgreSQL)
```bash
# Import all at once
cat test-data/import-all.sql | sudo docker exec -i omarino-postgres psql -U omarino -d omarino

# Or import individually
cat test-data/01-meters.sql | sudo docker exec -i omarino-postgres psql -U omarino -d omarino
cat test-data/02-series.sql | sudo docker exec -i omarino-postgres psql -U omarino -d omarino
cat test-data/03-timeseries-data.sql | sudo docker exec -i omarino-postgres psql -U omarino -d omarino
cat test-data/04-forecasts.sql | sudo docker exec -i omarino-postgres psql -U omarino -d omarino
cat test-data/05-optimizations.sql | sudo docker exec -i omarino-postgres psql -U omarino -d omarino
```

## 📊 Test Data Overview

### Meters (15 total)
- **3 Building A meters**: Main, HVAC, Lighting
- **2 Building B meters**: Main, HVAC
- **2 Solar arrays**: 250 kWp and 150 kWp
- **1 Battery storage**: 500 kWh capacity
- **2 Gas meters**: Building A and B
- **2 Water meters**: Building A and B
- **3 Temperature sensors**: Outdoor, Building A, Building B

### Time Series
- **~45 series total** (3 series per meter on average)
- **Data types**: consumption, power, generation, cost, temperature, state_of_charge
- **Granularity**: 15-minute intervals
- **Duration**: 7 days of historical data
- **Total data points**: ~19,000

### Patterns
- **Daily cycles**: Morning peak (7-10 AM), Evening peak (6-9 PM)
- **Solar generation**: Follows sun pattern (6 AM - 8 PM)
- **Weekend reduction**: 30% lower consumption
- **Night baseline**: 50% of daytime consumption
- **Random variation**: ±5-10% for realism

### Forecasts (3 samples)
- **Models**: XGBoost
- **Horizon**: 24 hours
- **Results**: Hourly predictions with confidence bounds (p10, p50, p90)
- **Metrics**: MAE, RMSE, MAPE included

### Optimizations (2 samples)
1. **Cost Optimization**: Minimize energy costs using battery storage and grid trading
2. **Load Balancing**: Reduce peak demand through load shifting

## 🔍 Verification Queries

### Check imported data
```sql
-- Count meters
SELECT COUNT(*) FROM meters WHERE name LIKE 'TEST_%';

-- Count series
SELECT COUNT(*) FROM meter_series ms
JOIN meters m ON ms.meter_id = m.meter_id
WHERE m.name LIKE 'TEST_%';

-- Count data points
SELECT COUNT(*) FROM time_series_data tsd
JOIN meter_series ms ON tsd.series_id = ms.series_id
JOIN meters m ON ms.meter_id = m.meter_id
WHERE m.name LIKE 'TEST_%';

-- View sample data
SELECT m.name, ms.name as series, COUNT(*) as points
FROM time_series_data tsd
JOIN meter_series ms ON tsd.series_id = ms.series_id
JOIN meters m ON ms.meter_id = m.meter_id
WHERE m.name LIKE 'TEST_%'
GROUP BY m.name, ms.name
ORDER BY m.name;
```

### Check forecasts
```sql
SELECT f.forecast_id, m.name, f.model_name, COUNT(fr.*) as results
FROM forecast_jobs f
JOIN meter_series ms ON f.series_id = ms.series_id::TEXT
JOIN meters m ON ms.meter_id = m.meter_id
LEFT JOIN forecast_results fr ON f.forecast_id = fr.forecast_id
WHERE m.name LIKE 'TEST_%'
GROUP BY f.forecast_id, m.name, f.model_name;
```

### Check optimizations
```sql
SELECT 
  optimization_id,
  type,
  objective,
  (results->>'total_cost_eur')::NUMERIC(10,2) as cost,
  status
FROM optimization_jobs;
```

## 🌐 Testing via API

### Get test meters
```bash
curl https://ems-back.omarino.net/api/meters | jq '.[] | select(.name | startswith("TEST_"))'
```

### Get time series data
```bash
# Get a specific meter's series
METER_ID="<meter_id_from_above>"
curl "https://ems-back.omarino.net/api/meters/$METER_ID/series"

# Get data for a series
SERIES_ID="<series_id_from_above>"
curl "https://ems-back.omarino.net/api/series/$SERIES_ID/data?start=2025-10-01T00:00:00Z&end=2025-10-08T00:00:00Z"
```

### Get forecasts
```bash
curl https://ems-back.omarino.net/api/forecast/forecasts
```

### Get optimizations
```bash
curl https://ems-back.omarino.net/api/optimize/optimizations
```

## 🧹 Cleanup

### Remove all test data
```bash
# Using cleanup script
cat test-data/cleanup.sql | sudo docker exec -i omarino-postgres psql -U omarino -d omarino

# Or delete manually
sudo docker exec -i omarino-postgres psql -U omarino -d omarino -c "
DELETE FROM time_series_data WHERE series_id IN (
  SELECT series_id FROM meter_series WHERE meter_id IN (
    SELECT meter_id FROM meters WHERE name LIKE 'TEST_%'
  )
);
DELETE FROM meter_series WHERE meter_id IN (
  SELECT meter_id FROM meters WHERE name LIKE 'TEST_%'
);
DELETE FROM meters WHERE name LIKE 'TEST_%';
"
```

## 💡 Tips

1. **Data Prefix**: All test data is prefixed with `TEST_` for easy identification and cleanup
2. **Import Time**: Full import takes 1-3 minutes depending on system
3. **Disk Space**: Test data uses approximately 50-100 MB
4. **Performance**: Use indexes on timestamp columns for faster queries
5. **Customization**: Edit the SQL files to adjust data ranges, values, or patterns

## 📝 File Structure

```
test-data/
├── README.md                  # Main documentation
├── QUICKSTART.md             # This file
├── import.sh                 # Automated import script
├── import-all.sql            # Import all files at once
├── cleanup.sql               # Remove test data
├── 01-meters.sql            # Create test meters
├── 02-series.sql            # Create time series definitions
├── 03-timeseries-data.sql   # Generate historical data
├── 04-forecasts.sql         # Create sample forecasts
└── 05-optimizations.sql     # Create sample optimizations
```

## 🐛 Troubleshooting

### Import fails with permission error
```bash
# Make sure script is executable
chmod +x test-data/import.sh
```

### Database connection error
```bash
# Check if container is running
sudo docker ps | grep postgres

# Start if needed
sudo docker start omarino-postgres
```

### Out of memory during import
```bash
# Import files one by one instead of all at once
for file in test-data/0*.sql; do
  cat "$file" | sudo docker exec -i omarino-postgres psql -U omarino -d omarino
done
```

### Want to reimport data
```bash
# Clean first, then import
cat test-data/cleanup.sql | sudo docker exec -i omarino-postgres psql -U omarino -d omarino
cat test-data/import-all.sql | sudo docker exec -i omarino-postgres psql -U omarino -d omarino
```
