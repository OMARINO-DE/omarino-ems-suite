#!/usr/bin/env python3
"""
Import meters from CSV to OMARINO EMS via JSON API

This script reads meters-fixed.csv and imports them one by one
using the actual working POST /api/meters endpoint.
"""

import csv
import json
import requests
import sys
from pathlib import Path

# Configuration
API_URL = "https://ems-back.omarino.net"
CSV_FILE = "csv/meters-fixed.csv"

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def import_meters():
    """Import meters from CSV"""
    csv_path = Path(__file__).parent / CSV_FILE
    
    if not csv_path.exists():
        print_error(f"CSV file not found: {csv_path}")
        return False
    
    print_info(f"Reading meters from {CSV_FILE}...")
    
    imported = 0
    failed = 0
    errors = []
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            meters = list(reader)
            
        print_info(f"Found {len(meters)} meters to import")
        print()
        
        for meter in meters:
            # Build JSON payload matching CreateMeterRequest
            payload = {
                "name": meter['name'],
                "type": meter['type'],  # Already PascalCase in meters-fixed.csv
                "timezone": meter['timezone']
            }
            
            # Add optional fields if not empty
            if meter.get('latitude') and meter['latitude'].strip():
                payload['latitude'] = float(meter['latitude'])
            
            if meter.get('longitude') and meter['longitude'].strip():
                payload['longitude'] = float(meter['longitude'])
            
            if meter.get('address') and meter['address'].strip():
                payload['address'] = meter['address']
            
            if meter.get('siteId') and meter['siteId'].strip():
                payload['siteId'] = meter['siteId']
            
            if meter.get('samplingInterval') and meter['samplingInterval'].strip():
                payload['samplingInterval'] = int(meter['samplingInterval'])
            
            # Try to create meter
            try:
                response = requests.post(
                    f"{API_URL}/api/meters",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    imported += 1
                    result = response.json()
                    print_success(f"Imported: {meter['name']} (ID: {result['id']})")
                elif response.status_code == 409:
                    print_warning(f"Already exists: {meter['name']}")
                else:
                    failed += 1
                    error_msg = f"{meter['name']}: HTTP {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail.get('message', error_detail)}"
                    except:
                        error_msg += f" - {response.text[:100]}"
                    
                    print_error(error_msg)
                    errors.append(error_msg)
                    
            except requests.exceptions.RequestException as e:
                failed += 1
                error_msg = f"{meter['name']}: {str(e)}"
                print_error(error_msg)
                errors.append(error_msg)
        
        # Summary
        print()
        print("=" * 60)
        print_info(f"Import Summary:")
        print_success(f"  Imported: {imported}")
        if failed > 0:
            print_error(f"  Failed: {failed}")
        print("=" * 60)
        
        if errors:
            print()
            print_warning("Errors encountered:")
            for err in errors[:5]:  # Show first 5 errors
                print(f"  • {err}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more")
        
        return failed == 0
        
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print()
    print(f"{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}OMARINO EMS - CSV Meter Import (via JSON API){RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}")
    print()
    
    success = import_meters()
    
    print()
    if success:
        print_success("All meters imported successfully! 🎉")
        print()
        print_info("Next steps:")
        print("  1. Verify meters: curl https://ems-back.omarino.net/api/meters")
        print("  2. Check web UI: https://ems-demo.omarino.net")
        print("  3. Import time series data using SQL scripts")
        print()
    else:
        print_warning("Some meters failed to import. Check errors above.")
        print()
        print_info("Troubleshooting:")
        print("  • Check if API is accessible")
        print("  • Verify CSV format matches meters-fixed.csv")
        print("  • Review error messages for validation issues")
        print()
        sys.exit(1)

if __name__ == "__main__":
    main()
