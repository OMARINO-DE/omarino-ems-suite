# 🎯 OMARINO EMS Test Data - Complete Guide

## 📦 What's Included

Complete test dataset for the OMARINO Energy Management System with:

- **15 Meters**: Electricity, solar, battery, gas, water, temperature sensors
- **~45 Time Series**: Multiple data types per meter
- **~19,000 Data Points**: 7 days of 15-minute interval data
- **3 Sample Forecasts**: ML-generated predictions with confidence intervals
- **2 Sample Optimizations**: Cost optimization and load balancing scenarios

## 🚀 Quick Start (3 Steps)

### Local Deployment

```bash
# 1. Navigate to test data directory
cd "OMARINO EMS Suite/test-data"

# 2. Run import script
./import.sh

# 3. Open web UI
open https://ems-demo.omarino.net
```

### Remote Server

```bash
# 1. Copy files to server
scp -i "/path/to/key.pem" -r test-data/ user@server:~/

# 2. SSH and import
ssh -i "/path/to/key.pem" user@server
cd ~/test-data && ./import.sh

# 3. Access via browser
# https://ems-demo.omarino.net
```

## 📁 File Structure

```
test-data/
├── README.md                    # Main documentation
├── QUICKSTART.md               # Quick reference
├── GUIDE.md                    # This comprehensive guide
│
├── import.sh                   # 🔥 Automated import (RECOMMENDED)
├── import-all.sql              # Import all SQL at once
├── cleanup.sql                 # Remove test data
│
├── 01-meters.sql              # Step 1: Create meters
├── 02-series.sql              # Step 2: Create time series
├── 03-timeseries-data.sql     # Step 3: Generate data (1-2 min)
├── 04-forecasts.sql           # Step 4: Create forecasts
├── 05-optimizations.sql       # Step 5: Create optimizations
│
└── csv/                        # Alternative CSV format
    ├── README.md
    └── meters.csv
```

## 🎨 Test Data Details

### Meters (15 total)

#### Building A (3 meters)
- **Main Electrical**: 500 kW capacity, consumption tracking
- **HVAC System**: 150 kW capacity, basement location
- **Lighting**: 50 kW capacity, all floors

#### Building B (2 meters)
- **Main Electrical**: 300 kW capacity
- **HVAC System**: 100 kW capacity, roof location

#### Renewable Energy (2 solar + 1 battery)
- **Solar Array 1**: 250 kWp, Building A roof, south-facing
- **Solar Array 2**: 150 kWp, Building B roof
- **Battery Storage**: 500 kWh Li-ion, ±100 kW charge/discharge

#### Utilities (4 meters)
- **Gas Meters**: Building A (500 m³/h) and B (300 m³/h)
- **Water Meters**: Building A and B cold water

#### Sensors (3 temperature)
- **Outdoor**: North side, 2m height
- **Building A Average**: Indoor temperature
- **Building B Average**: Indoor temperature

### Time Series Data

Each meter has 2-4 time series:

1. **Primary measurement**: consumption, generation, or state_of_charge
2. **Power series**: Instantaneous power (kW) for electrical meters
3. **Cost series**: Associated costs (€) for consumed resources
4. **Temperature**: Direct measurement (°C) for sensors

**Characteristics**:
- **Granularity**: 15-minute intervals
- **Duration**: 7 days (Oct 1-7, 2025)
- **Quality**: All marked as "good"
- **Total points**: ~19,000 across all series

### Realistic Patterns

#### Daily Consumption Pattern
```
00:00 - 06:00: 50% baseline (night)
06:00 - 10:00: 130% peak (morning)
10:00 - 18:00: 90% baseline (day)
18:00 - 22:00: 140% peak (evening)
22:00 - 24:00: 70% winding down
```

#### Solar Generation Pattern
```
00:00 - 06:00: 0 kW (night)
06:00 - 08:00: Ramp up
08:00 - 16:00: Peak production
16:00 - 20:00: Ramp down
20:00 - 24:00: 0 kW (night)
```

#### Weekend Adjustment
- Consumption reduced by 30%
- Solar production unchanged
- Temperature patterns similar

#### Random Variation
- ±5-10% noise added for realism
- Prevents perfectly predictable patterns
- Simulates real-world variability

### Forecasts (3 samples)

Each forecast includes:

- **Model**: XGBoost (gradient boosting)
- **Horizon**: 24 hours ahead
- **Results**: Hourly predictions
- **Confidence intervals**: p10, p50, p90 quantiles
- **Metrics**: MAE, RMSE, MAPE
- **Training samples**: 672 (1 week of 15-min data)

**Example Forecast**:
```json
{
  "forecast_id": "uuid",
  "series_id": "TEST_Building_A_Main_consumption",
  "model_name": "xgboost",
  "horizon": 24,
  "metrics": {
    "mae": 5.2,
    "rmse": 8.5,
    "mape": 0.08
  }
}
```

### Optimizations (2 samples)

#### 1. Cost Optimization
**Objective**: Minimize energy costs

**Parameters**:
- Grid price: €0.25/kWh
- Feed-in tariff: €0.10/kWh
- Battery: 500 kWh capacity
- Charge/discharge: ±100 kW

**Results**:
- Total cost: €156.75
- Grid import: 890.5 kWh
- Grid export: 234.2 kWh
- Cost savings: 23.4%
- Solar utilization: 87.3%

**Schedule**: 24-hour optimization with hourly decisions for:
- Battery charging/discharging
- Grid import/export
- Solar usage allocation

#### 2. Load Balancing
**Objective**: Minimize peak demand

**Parameters**:
- Peak limit: 400 kW
- Demand response enabled
- Shiftable loads: 150 kW

**Results**:
- Peak demand: 387.5 kW
- Peak reduction: 18.3%
- Load factor: 0.82
- Battery cycles: 0.8

**Schedule**: Load shifting actions to flatten demand curve

## 💻 Import Methods

### Method 1: Automated Script (Recommended)

```bash
cd test-data
./import.sh
```

**Pros**: 
- ✅ Fastest method
- ✅ Shows progress
- ✅ Handles errors
- ✅ Displays summary

**Time**: 1-3 minutes

### Method 2: PostgreSQL Direct

```bash
# Import all at once
cat test-data/import-all.sql | \
  sudo docker exec -i omarino-postgres \
  psql -U omarino -d omarino

# Or step by step
for file in test-data/0*.sql; do
  cat "$file" | sudo docker exec -i omarino-postgres \
    psql -U omarino -d omarino
done
```

### Method 3: CSV via API

⚠️ **IMPORTANT**: Use `meters-fixed.csv` not `meters.csv`!

```bash
# Import meters (use the FIXED version!)
curl -X POST https://ems-back.omarino.net/api/meters/import \
  -F "file=@test-data/csv/meters-fixed.csv"
```

**Why the fix was needed:**
- ❌ Original `meters.csv`: Wrong format causes "One or more validation errors occurred"
- ✅ Fixed `meters-fixed.csv`: Correct format matching API validation

**Key differences:**
- Type values MUST be PascalCase: `Electricity` not `electricity`
- Field is `address` not `location`
- Required `timezone` field (IANA format like `Europe/Berlin`)
- Removed unsupported `unit` and `metadata` columns

See `test-data/csv/README.md` for full technical details.

**Note**: CSV method requires API import endpoints to be implemented.

## 🔍 Verification & Testing

### Check Import Success

```bash
# Quick check via API
curl -s https://ems-back.omarino.net/api/meters | \
  jq '[.[] | select(.name | startswith("TEST_"))] | length'
```

Expected output: `15` (meters)

### Database Verification

```sql
-- Connect to database
sudo docker exec -it omarino-postgres psql -U omarino -d omarino

-- Check all test data
SELECT 
  'Meters' as type, COUNT(*) FROM meters WHERE name LIKE 'TEST_%'
UNION ALL
  SELECT 'Series', COUNT(*) FROM meter_series ms 
    JOIN meters m ON ms.meter_id = m.meter_id WHERE m.name LIKE 'TEST_%'
UNION ALL
  SELECT 'Data Points', COUNT(*) FROM time_series_data tsd
    JOIN meter_series ms ON tsd.series_id = ms.series_id
    JOIN meters m ON ms.meter_id = m.meter_id WHERE m.name LIKE 'TEST_%';
```

Expected output:
```
    type     | count 
-------------+-------
 Meters      |    15
 Series      |    45
 Data Points | 19000
```

### View Sample Data

```sql
-- View meters
SELECT meter_id, name, type, location FROM meters 
WHERE name LIKE 'TEST_%' 
ORDER BY type, name;

-- View time series
SELECT m.name, ms.name, ms.data_type, ms.unit
FROM meter_series ms
JOIN meters m ON ms.meter_id = m.meter_id
WHERE m.name LIKE 'TEST_%'
ORDER BY m.name;

-- View latest data
SELECT m.name, tsd.timestamp, tsd.value, tsd.quality
FROM time_series_data tsd
JOIN meter_series ms ON tsd.series_id = ms.series_id
JOIN meters m ON ms.meter_id = m.meter_id
WHERE m.name LIKE 'TEST_%'
ORDER BY tsd.timestamp DESC
LIMIT 10;
```

## 🌐 Web UI Testing

### Navigate to Dashboard
1. Open https://ems-demo.omarino.net
2. Go to **Time Series** page
3. Filter by "TEST_" to see test meters
4. Select a meter to view data
5. Charts should display 7 days of data

### Create Forecast
1. Go to **Forecasts** page
2. Click "New Forecast"
3. Select a TEST_ series
4. Set horizon to 24 hours
5. Click "Generate"
6. View results

### Run Optimization
1. Go to **Optimization** page
2. Click "New Optimization"
3. Select cost optimization
4. Configure parameters
5. Click "Run"
6. View schedule

## 🧹 Cleanup

### Remove Test Data

```bash
# Using cleanup script
cat test-data/cleanup.sql | \
  sudo docker exec -i omarino-postgres \
  psql -U omarino -d omarino
```

### Verify Cleanup

```sql
SELECT COUNT(*) FROM meters WHERE name LIKE 'TEST_%';
-- Expected: 0
```

## 🎓 Use Cases

### 1. Development Testing
- Test UI components with realistic data
- Verify API endpoints
- Check data visualization
- Validate calculations

### 2. Demo/Presentation
- Show system capabilities
- Present to stakeholders
- Training sessions
- Sales demos

### 3. Performance Testing
- Load testing with ~19k data points
- Query optimization
- Chart rendering speed
- API response times

### 4. Feature Development
- Forecast algorithm testing
- Optimization logic validation
- New visualizations
- Report generation

## 🐛 Troubleshooting

### Import Fails

**Issue**: Permission denied
```bash
chmod +x test-data/import.sh
```

**Issue**: Container not running
```bash
sudo docker start omarino-postgres
```

**Issue**: Out of memory
```bash
# Import files one at a time
cat test-data/01-meters.sql | sudo docker exec -i omarino-postgres psql -U omarino -d omarino
# ... repeat for each file
```

### Data Not Visible in UI

**Check API**:
```bash
curl https://ems-back.omarino.net/api/meters
```

**Check Database**:
```bash
sudo docker exec omarino-postgres psql -U omarino -d omarino -c \
  "SELECT COUNT(*) FROM meters WHERE name LIKE 'TEST_%';"
```

**Clear Browser Cache**:
- Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)

### Forecasts Not Working

**Check forecast service**:
```bash
curl https://ems-back.omarino.net/api/forecast/health
```

**Check logs**:
```bash
sudo docker logs omarino-forecast --tail 50
```

## 📊 Data Statistics

| Metric | Count | Size |
|--------|-------|------|
| Meters | 15 | - |
| Time Series | 45 | - |
| Data Points | ~19,000 | ~50 MB |
| Time Range | 7 days | - |
| Forecasts | 3 | ~200 points |
| Optimizations | 2 | ~100 points |
| Total Disk | - | ~100 MB |

## 🔐 Security Notes

- Test data uses `TEST_` prefix for easy identification
- No sensitive information included
- Safe to share and demonstrate
- Can be deleted anytime without affecting real data

## 📝 Customization

### Adjust Time Range

Edit `03-timeseries-data.sql`:
```sql
-- Change from 7 days to 30 days
start_time := end_time - INTERVAL '30 days';
```

### Adjust Granularity

Edit `02-series.sql`:
```sql
-- Change from 15 minutes to 1 hour
'PT1H'  -- instead of 'PT15M'
```

### Add More Meters

Edit `01-meters.sql`:
```sql
INSERT INTO meters (meter_id, name, type, location, unit, metadata)
VALUES (gen_random_uuid(), 'TEST_Your_Meter', 'electricity', ...);
```

## 🤝 Support

For issues or questions:
1. Check this guide
2. Review SQL file comments
3. Check application logs
4. Contact development team

## 📚 References

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [TimescaleDB Hypertables](https://docs.timescale.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)

---

**Version**: 1.0  
**Last Updated**: October 7, 2025  
**License**: Internal Use Only
