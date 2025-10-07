#!/usr/bin/env python3
"""
OMARINO EMS - Demo Data Insertion Script

This script inserts realistic demo data into all OMARINO EMS services:
- Time Series Service: Meters, Series, and historical energy data
- Forecast Service: Sample forecast requests
- Optimization Service: Sample optimization problems
- Scheduler Service: Sample workflows

Usage:
    python3 insert-demo-data.py --host 192.168.75.20
"""

import argparse
import requests
import json
from datetime import datetime, timedelta
import random
import math
import sys

class DemoDataGenerator:
    def __init__(self, host, port=8081):
        self.base_url = f"http://{host}:{port}"
        self.timeseries_url = f"{self.base_url}/api"
        self.forecast_url = f"{self.base_url}/api/forecast"
        self.optimize_url = f"{self.base_url}/api/optimize"
        self.scheduler_url = f"{self.base_url}/api/scheduler"
        
        self.headers = {"Content-Type": "application/json"}
        self.meter_ids = {}
        self.series_ids = {}
    
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def generate_sine_wave_data(self, base_value, amplitude, frequency, num_points, noise_factor=0.1):
        """Generate realistic sine wave data with noise (simulates daily patterns)"""
        data = []
        for i in range(num_points):
            # Sine wave component (daily pattern)
            sine_value = base_value + amplitude * math.sin(2 * math.pi * frequency * i)
            # Add random noise
            noise = random.gauss(0, amplitude * noise_factor)
            value = max(0, sine_value + noise)  # Ensure non-negative
            data.append(round(value, 2))
        return data
    
    def generate_consumption_pattern(self, num_days=30):
        """Generate realistic energy consumption pattern"""
        points_per_day = 24  # Hourly data
        total_points = num_days * points_per_day
        
        # Base load: 20 kW, Peak: 50 kW during day
        base_load = 20
        peak_amplitude = 15
        frequency = 1 / points_per_day  # One cycle per day
        
        return self.generate_sine_wave_data(base_load, peak_amplitude, frequency, total_points, noise_factor=0.15)
    
    def generate_production_pattern(self, num_days=30):
        """Generate realistic solar production pattern"""
        points_per_day = 24
        total_points = num_days * points_per_day
        
        data = []
        for day in range(num_days):
            for hour in range(24):
                if 6 <= hour <= 18:  # Daylight hours
                    # Peak at noon
                    hours_from_noon = abs(hour - 12)
                    base_production = 30 * (1 - hours_from_noon / 6)
                    noise = random.gauss(0, 3)
                    value = max(0, base_production + noise)
                else:
                    value = 0
                data.append(round(value, 2))
        return data
    
    def generate_price_pattern(self, num_days=30):
        """Generate realistic electricity price pattern"""
        points_per_day = 24
        total_points = num_days * points_per_day
        
        # Base price: 0.25 EUR/kWh, varies between 0.15-0.35
        base_price = 0.25
        amplitude = 0.05
        frequency = 1 / points_per_day
        
        return self.generate_sine_wave_data(base_price, amplitude, frequency, total_points, noise_factor=0.2)
    
    # =====================
    # TIME SERIES SERVICE
    # =====================
    
    def create_meters(self):
        """Create sample meters"""
        self.log("Creating sample meters...")
        
        # MeterType enum values: Electricity, Gas, Water, Heat, Virtual
        # NOTE: API expects string enum names due to JsonStringEnumConverter
        meters = [
            {
                "name": "Main Building - Grid Connection",
                "type": "Electricity",
                "latitude": 52.5200,
                "longitude": 13.4050,
                "address": "Hauptstraße 123, 10115 Berlin, Germany",
                "samplingInterval": 3600,  # 1 hour
                "timezone": "Europe/Berlin",
                "tags": {"building": "main", "source": "grid", "category": "consumption"}
            },
            {
                "name": "Rooftop Solar Array 1",
                "type": "Electricity",
                "latitude": 52.5201,
                "longitude": 13.4051,
                "address": "Hauptstraße 123, 10115 Berlin, Germany",
                "samplingInterval": 3600,
                "timezone": "Europe/Berlin",
                "tags": {"building": "main", "source": "solar", "category": "production", "capacity_kw": "45"}
            },
            {
                "name": "Building 2 - Consumption",
                "type": "Electricity",
                "latitude": 52.5190,
                "longitude": 13.4040,
                "address": "Nebenstraße 45, 10115 Berlin, Germany",
                "samplingInterval": 3600,
                "timezone": "Europe/Berlin",
                "tags": {"building": "secondary", "source": "grid", "category": "consumption"}
            },
            {
                "name": "Battery Storage System",
                "type": "Virtual",
                "latitude": 52.5200,
                "longitude": 13.4050,
                "address": "Hauptstraße 123, 10115 Berlin, Germany",
                "samplingInterval": 900,  # 15 minutes
                "timezone": "Europe/Berlin",
                "tags": {"building": "main", "type": "battery", "capacity_kwh": "100"}
            },
            {
                "name": "Heat Pump",
                "type": "Heat",
                "latitude": 52.5200,
                "longitude": 13.4050,
                "address": "Hauptstraße 123, 10115 Berlin, Germany",
                "samplingInterval": 3600,
                "timezone": "Europe/Berlin",
                "tags": {"building": "main", "type": "heatpump", "cop": "3.5"}
            }
        ]
        
        for meter_data in meters:
            try:
                response = requests.post(
                    f"{self.timeseries_url}/meters",
                    headers=self.headers,
                    json=meter_data,
                    timeout=10
                )
                if response.status_code in [200, 201]:
                    meter_id = response.json().get("id")
                    self.meter_ids[meter_data["name"]] = meter_id
                    self.log(f"✓ Created meter: {meter_data['name']} (ID: {meter_id})")
                else:
                    self.log(f"✗ Failed to create meter {meter_data['name']}: {response.status_code} - {response.text}", "ERROR")
            except Exception as e:
                self.log(f"✗ Error creating meter {meter_data['name']}: {str(e)}", "ERROR")
        
        self.log(f"Created {len(self.meter_ids)} meters")
    
    def create_series(self):
        """Create time series for each meter"""
        self.log("Creating time series...")
        
        # AggregationType enum: Instant, Mean, Sum, Min, Max, Count
        # DataType enum: Measurement, Forecast, Schedule, Price, Weather
        # NOTE: API expects string enum names due to JsonStringEnumConverter
        series_config = [
            {
                "meter": "Main Building - Grid Connection",
                "series": [
                    {"name": "Active Power", "unit": "kW", "aggregation": "Mean", "dataType": "Measurement"},
                    {"name": "Energy Consumption", "unit": "kWh", "aggregation": "Sum", "dataType": "Measurement"},
                    {"name": "Grid Price", "unit": "EUR/kWh", "aggregation": "Mean", "dataType": "Price"}
                ]
            },
            {
                "meter": "Rooftop Solar Array 1",
                "series": [
                    {"name": "Active Power", "unit": "kW", "aggregation": "Mean", "dataType": "Measurement"},
                    {"name": "Energy Production", "unit": "kWh", "aggregation": "Sum", "dataType": "Measurement"}
                ]
            },
            {
                "meter": "Building 2 - Consumption",
                "series": [
                    {"name": "Active Power", "unit": "kW", "aggregation": "Mean", "dataType": "Measurement"},
                    {"name": "Energy Consumption", "unit": "kWh", "aggregation": "Sum", "dataType": "Measurement"}
                ]
            },
            {
                "meter": "Battery Storage System",
                "series": [
                    {"name": "State of Charge", "unit": "%", "aggregation": "Instant", "dataType": "Measurement"},
                    {"name": "Charge Power", "unit": "kW", "aggregation": "Mean", "dataType": "Measurement"}
                ]
            },
            {
                "meter": "Heat Pump",
                "series": [
                    {"name": "Thermal Power", "unit": "kW", "aggregation": "Mean", "dataType": "Measurement"},
                    {"name": "Electric Power", "unit": "kW", "aggregation": "Mean", "dataType": "Measurement"},
                    {"name": "COP", "unit": "-", "aggregation": "Mean", "dataType": "Measurement"}
                ]
            }
        ]
        
        for config in series_config:
            meter_name = config["meter"]
            meter_id = self.meter_ids.get(meter_name)
            
            if not meter_id:
                self.log(f"Meter not found: {meter_name}", "WARNING")
                continue
            
            for series in config["series"]:
                series_data = {
                    "meterId": meter_id,
                    "name": series["name"],
                    "description": f"{series['name']} for {meter_name}",
                    "unit": series["unit"],
                    "aggregation": series["aggregation"],
                    "dataType": series["dataType"]
                }
                
                try:
                    response = requests.post(
                        f"{self.timeseries_url}/series",
                        headers=self.headers,
                        json=series_data,
                        timeout=10
                    )
                    if response.status_code in [200, 201]:
                        series_id = response.json().get("id")
                        key = f"{meter_name}|{series['name']}"
                        self.series_ids[key] = series_id
                        self.log(f"✓ Created series: {meter_name} - {series['name']}")
                    else:
                        self.log(f"✗ Failed to create series: {response.status_code}", "ERROR")
                except Exception as e:
                    self.log(f"✗ Error creating series: {str(e)}", "ERROR")
        
        self.log(f"Created {len(self.series_ids)} series")
    
    def insert_timeseries_data(self):
        """Insert historical time series data"""
        self.log("Inserting historical time series data (last 30 days)...")
        
        num_days = 30
        end_time = datetime.now()
        start_time = end_time - timedelta(days=num_days)
        
        # Generate timestamps (hourly)
        timestamps = []
        current = start_time
        while current <= end_time:
            timestamps.append(current.isoformat() + "Z")
            current += timedelta(hours=1)
        
        # Data patterns
        data_patterns = {
            "Main Building - Grid Connection|Active Power": self.generate_consumption_pattern(num_days),
            "Main Building - Grid Connection|Energy Consumption": self.generate_consumption_pattern(num_days),
            "Main Building - Grid Connection|Grid Price": self.generate_price_pattern(num_days),
            "Rooftop Solar Array 1|Active Power": self.generate_production_pattern(num_days),
            "Rooftop Solar Array 1|Energy Production": self.generate_production_pattern(num_days),
            "Building 2 - Consumption|Active Power": [x * 0.6 for x in self.generate_consumption_pattern(num_days)],
            "Building 2 - Consumption|Energy Consumption": [x * 0.6 for x in self.generate_consumption_pattern(num_days)],
            "Battery Storage System|State of Charge": [random.uniform(20, 90) for _ in range(len(timestamps))],
            "Battery Storage System|Charge Power": [random.uniform(-10, 10) for _ in range(len(timestamps))],
            "Heat Pump|Thermal Power": [random.uniform(5, 15) for _ in range(len(timestamps))],
            "Heat Pump|Electric Power": [random.uniform(2, 5) for _ in range(len(timestamps))],
            "Heat Pump|COP": [random.uniform(3.0, 4.0) for _ in range(len(timestamps))]
        }
        
        for series_key, series_id in self.series_ids.items():
            if series_key not in data_patterns:
                continue
            
            values = data_patterns[series_key]
            
            # Prepare data points in the format expected by /api/Ingest
            points = []
            for i, timestamp in enumerate(timestamps):
                if i < len(values):
                    points.append({
                        "seriesId": series_id,
                        "timestamp": timestamp,
                        "value": values[i],
                        "quality": 0,  # DataQuality enum: Good = 0
                        "source": "demo-data-script",
                        "version": 1,
                        "metadata": {}
                    })
            
            # Insert in batches of 1000 using /api/Ingest endpoint
            batch_size = 1000
            for i in range(0, len(points), batch_size):
                batch = points[i:i+batch_size]
                try:
                    response = requests.post(
                        f"{self.timeseries_url}/ingest",
                        headers=self.headers,
                        json={
                            "source": "demo-data-script",
                            "points": batch
                        },
                        timeout=30
                    )
                    if response.status_code in [200, 201, 202]:
                        self.log(f"✓ Inserted {len(batch)} points for {series_key}")
                    else:
                        self.log(f"✗ Failed to insert data: {response.status_code} - {response.text}", "ERROR")
                except Exception as e:
                    self.log(f"✗ Error inserting data: {str(e)}", "ERROR")
        
        self.log("Completed inserting time series data")
    
    # =====================
    # SCHEDULER SERVICE
    # =====================
    
    def create_workflows(self):
        """Create sample workflows"""
        self.log("Creating sample workflows...")
        
        workflows = [
            {
                "name": "Daily Energy Forecast",
                "description": "Generate energy consumption forecast for next 24 hours",
                "tasks": [
                    {
                        "name": "fetch_historical_data",
                        "type": "HttpCall",
                        "configuration": {
                            "url": f"{self.timeseries_url}/series/query",
                            "method": "POST",
                            "body": {"timerange": "last_7_days"}
                        }
                    },
                    {
                        "name": "generate_forecast",
                        "type": "HttpCall",
                        "configuration": {
                            "url": f"{self.forecast_url}/predict",
                            "method": "POST",
                            "body": {"horizon": "24h", "model": "prophet"}
                        },
                        "dependencies": ["fetch_historical_data"]
                    }
                ],
                "schedule": {
                    "type": "Cron",
                    "cronExpression": "0 0 * * *",  # Daily at midnight
                    "timezone": "Europe/Berlin"
                },
                "isEnabled": True,
                "maxExecutionTime": "PT30M",
                "tags": ["forecast", "daily", "production"]
            },
            {
                "name": "Hourly Optimization",
                "description": "Optimize energy dispatch every hour",
                "tasks": [
                    {
                        "name": "fetch_forecast",
                        "type": "HttpCall",
                        "configuration": {
                            "url": f"{self.forecast_url}/latest",
                            "method": "GET"
                        }
                    },
                    {
                        "name": "fetch_prices",
                        "type": "HttpCall",
                        "configuration": {
                            "url": f"{self.timeseries_url}/prices/current",
                            "method": "GET"
                        }
                    },
                    {
                        "name": "optimize_dispatch",
                        "type": "HttpCall",
                        "configuration": {
                            "url": f"{self.optimize_url}/solve",
                            "method": "POST",
                            "body": {"objective": "minimize_cost", "horizon": "24h"}
                        },
                        "dependencies": ["fetch_forecast", "fetch_prices"]
                    }
                ],
                "schedule": {
                    "type": "Cron",
                    "cronExpression": "0 * * * *",  # Every hour
                    "timezone": "Europe/Berlin"
                },
                "isEnabled": True,
                "maxExecutionTime": "PT15M",
                "tags": ["optimization", "hourly", "production"]
            },
            {
                "name": "Weekly Report Generation",
                "description": "Generate weekly energy report and send notifications",
                "tasks": [
                    {
                        "name": "aggregate_weekly_data",
                        "type": "HttpCall",
                        "configuration": {
                            "url": f"{self.timeseries_url}/aggregate",
                            "method": "POST",
                            "body": {"period": "week", "aggregation": "sum"}
                        }
                    },
                    {
                        "name": "generate_report",
                        "type": "Script",
                        "configuration": {
                            "script": "python3 /app/scripts/generate_report.py"
                        },
                        "dependencies": ["aggregate_weekly_data"]
                    }
                ],
                "schedule": {
                    "type": "Cron",
                    "cronExpression": "0 8 * * 1",  # Every Monday at 8 AM
                    "timezone": "Europe/Berlin"
                },
                "isEnabled": False,
                "maxExecutionTime": "PT1H",
                "tags": ["report", "weekly"]
            }
        ]
        
        for workflow in workflows:
            try:
                response = requests.post(
                    f"{self.scheduler_url}/workflows",
                    headers=self.headers,
                    json=workflow,
                    timeout=10
                )
                if response.status_code in [200, 201]:
                    workflow_id = response.json().get("id")
                    self.log(f"✓ Created workflow: {workflow['name']} (ID: {workflow_id})")
                else:
                    self.log(f"✗ Failed to create workflow {workflow['name']}: {response.status_code} - {response.text}", "ERROR")
            except Exception as e:
                self.log(f"✗ Error creating workflow {workflow['name']}: {str(e)}", "ERROR")
        
        self.log("Completed creating workflows")
    
    # =====================
    # MAIN EXECUTION
    # =====================
    
    def run_all(self):
        """Run all demo data generation"""
        self.log("=" * 60)
        self.log("OMARINO EMS - Demo Data Insertion")
        self.log("=" * 60)
        self.log(f"Target: {self.base_url}")
        self.log("")
        
        try:
            # Time Series Service
            self.create_meters()
            self.create_series()
            self.insert_timeseries_data()
            
            # Scheduler Service
            self.create_workflows()
            
            self.log("")
            self.log("=" * 60)
            self.log("Demo data insertion completed successfully!")
            self.log("=" * 60)
            self.log("")
            self.log("Summary:")
            self.log(f"  - Meters created: {len(self.meter_ids)}")
            self.log(f"  - Series created: {len(self.series_ids)}")
            self.log(f"  - Time series data: ~{len(self.series_ids) * 720} data points (30 days, hourly)")
            self.log(f"  - Workflows created: 3")
            self.log("")
            self.log("You can now:")
            self.log(f"  - View meters: {self.timeseries_url}/meters")
            self.log(f"  - Query data: {self.timeseries_url}/series/query")
            self.log(f"  - View workflows: {self.scheduler_url}/workflows")
            
        except Exception as e:
            self.log(f"Fatal error: {str(e)}", "ERROR")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Insert demo data into OMARINO EMS")
    parser.add_argument("--host", default="localhost", help="API Gateway host (default: localhost)")
    parser.add_argument("--port", type=int, default=8081, help="API Gateway port (default: 8081)")
    
    args = parser.parse_args()
    
    generator = DemoDataGenerator(args.host, args.port)
    generator.run_all()

if __name__ == "__main__":
    main()
