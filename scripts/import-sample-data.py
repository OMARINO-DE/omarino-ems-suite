#!/usr/bin/env python3
"""
OMARINO EMS - Sample Data Import Script

This script imports sample meter and time series data into the OMARINO EMS system.
"""

import csv
import sys
import time
import json
import requests
from datetime import datetime
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8080"
METERS_FILE = "sample-data/meters.csv"
TIME_SERIES_FILE = "sample-data/time_series.csv"

# Colors for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_info(message):
    """Print info message"""
    print(f"{BLUE}ℹ️  {message}{RESET}")


def print_success(message):
    """Print success message"""
    print(f"{GREEN}✅ {message}{RESET}")


def print_warning(message):
    """Print warning message"""
    print(f"{YELLOW}⚠️  {message}{RESET}")


def print_error(message):
    """Print error message"""
    print(f"{RED}❌ {message}{RESET}")


def wait_for_services():
    """Wait for services to be ready"""
    print_info("Waiting for services to be ready...")
    max_retries = 30
    retry_interval = 2
    
    for i in range(max_retries):
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                print_success("All services are ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if i < max_retries - 1:
            print(f"  Retry {i+1}/{max_retries}...", end='\r')
            time.sleep(retry_interval)
    
    print_error("Services did not become ready in time")
    return False


def get_auth_token():
    """Get JWT authentication token"""
    print_info("Authenticating with API Gateway...")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/auth/login",
            json={"username": "demo", "password": "demo123"},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        token = data.get("token")
        
        if token:
            print_success("Authentication successful!")
            return token
        else:
            print_error("No token in response")
            return None
            
    except requests.exceptions.RequestException as e:
        print_error(f"Authentication failed: {e}")
        return None


def import_meters(token):
    """Import meters from CSV file"""
    print_info(f"Importing meters from {METERS_FILE}...")
    
    if not Path(METERS_FILE).exists():
        print_error(f"File not found: {METERS_FILE}")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    imported_count = 0
    
    try:
        with open(METERS_FILE, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                meter_data = {
                    "id": row["meter_id"],
                    "name": row["name"],
                    "location": row["location"],
                    "type": row["type"],
                    "unit": row["unit"],
                    "metadata": {
                        "description": row["description"]
                    }
                }
                
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/api/timeseries/meters",
                        json=meter_data,
                        headers=headers,
                        timeout=10
                    )
                    
                    if response.status_code in [200, 201]:
                        imported_count += 1
                        print(f"  ✓ Imported meter: {row['meter_id']} - {row['name']}")
                    elif response.status_code == 409:
                        print_warning(f"  Meter already exists: {row['meter_id']}")
                    else:
                        print_warning(f"  Failed to import meter {row['meter_id']}: {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    print_warning(f"  Error importing meter {row['meter_id']}: {e}")
        
        print_success(f"Imported {imported_count} meters")
        return True
        
    except Exception as e:
        print_error(f"Error reading meters file: {e}")
        return False


def import_time_series(token):
    """Import time series data from CSV file"""
    print_info(f"Importing time series data from {TIME_SERIES_FILE}...")
    
    if not Path(TIME_SERIES_FILE).exists():
        print_error(f"File not found: {TIME_SERIES_FILE}")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Read all data points
        data_points = []
        with open(TIME_SERIES_FILE, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                data_points.append(row)
        
        total_points = len(data_points)
        print_info(f"Found {total_points} data points to import")
        
        # Import in batches
        batch_size = 100
        imported_count = 0
        
        for i in range(0, total_points, batch_size):
            batch = data_points[i:i + batch_size]
            
            # Group by meter_id and series_id
            series_data = {}
            for point in batch:
                key = (point["meter_id"], point["series_id"])
                if key not in series_data:
                    series_data[key] = []
                
                series_data[key].append({
                    "timestamp": point["timestamp"],
                    "value": float(point["value"]),
                    "quality": point["quality"]
                })
            
            # Send each series batch
            for (meter_id, series_id), points in series_data.items():
                payload = {
                    "meterId": meter_id,
                    "seriesId": series_id,
                    "dataPoints": points
                }
                
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/api/timeseries/ingest",
                        json=payload,
                        headers=headers,
                        timeout=30
                    )
                    
                    if response.status_code in [200, 201]:
                        imported_count += len(points)
                        print(f"  ✓ Imported batch for {series_id}: {len(points)} points "
                              f"({imported_count}/{total_points})")
                    else:
                        print_warning(f"  Failed to import batch for {series_id}: {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    print_warning(f"  Error importing batch for {series_id}: {e}")
        
        print_success(f"Imported {imported_count}/{total_points} data points")
        return True
        
    except Exception as e:
        print_error(f"Error importing time series data: {e}")
        return False


def verify_import(token):
    """Verify that data was imported successfully"""
    print_info("Verifying imported data...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Check meters
        response = requests.get(
            f"{API_BASE_URL}/api/timeseries/meters",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            meters = response.json()
            print_success(f"Found {len(meters)} meters in database")
            
            # Check time series for first meter
            if meters:
                meter_id = meters[0]["id"]
                response = requests.get(
                    f"{API_BASE_URL}/api/timeseries/meters/{meter_id}/series",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    series = response.json()
                    print_success(f"Found {len(series)} time series for meter {meter_id}")
                    
                    # Check data points for first series
                    if series:
                        series_id = series[0]["id"]
                        response = requests.get(
                            f"{API_BASE_URL}/api/timeseries/series/{series_id}/data",
                            headers=headers,
                            params={"limit": 10},
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            data_points = response.json()
                            print_success(f"Found {len(data_points)} data points for series {series_id}")
                            return True
        
        return False
        
    except Exception as e:
        print_error(f"Verification failed: {e}")
        return False


def main():
    """Main function"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}OMARINO EMS - Sample Data Import{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    # Wait for services
    if not wait_for_services():
        sys.exit(1)
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        sys.exit(1)
    
    # Import data
    print()
    if not import_meters(token):
        sys.exit(1)
    
    print()
    if not import_time_series(token):
        sys.exit(1)
    
    # Verify import
    print()
    if not verify_import(token):
        print_warning("Verification had issues, but import may have succeeded")
    
    print(f"\n{GREEN}{'='*60}{RESET}")
    print(f"{GREEN}✅ Sample data import complete!{RESET}")
    print(f"{GREEN}{'='*60}{RESET}\n")
    
    print_info("You can now:")
    print("  • View the data in the web UI: http://localhost:3000")
    print("  • Run forecasts with the imported data")
    print("  • Create optimization scenarios")
    print("  • Set up automated workflows")
    print()


if __name__ == "__main__":
    main()
