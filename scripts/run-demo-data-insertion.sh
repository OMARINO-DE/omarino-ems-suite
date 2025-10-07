#!/bin/bash
# OMARINO EMS - Demo Data Insertion Runner
# This script runs the demo data insertion on the remote server

set -e

SERVER_HOST="192.168.75.20"
SSH_KEY="/Users/omarzaror/Library/Mobile Documents/com~apple~CloudDocs/Developing/SSH-Key/server.pem"
API_HOST="localhost"
API_PORT="8081"

echo "=========================================="
echo "OMARINO EMS - Demo Data Insertion"
echo "=========================================="
echo ""
echo "This will insert demo data into:"
echo "  - Time Series Service (meters, series, data)"
echo "  - Scheduler Service (workflows)"
echo ""
echo "Target: http://${API_HOST}:${API_PORT}"
echo ""

# Copy script to server
echo "Copying demo data script to server..."
scp -i "${SSH_KEY}" \
    "/Users/omarzaror/Library/Mobile Documents/com~apple~CloudDocs/Developing/OMARINO EMS Suite/scripts/insert-demo-data.py" \
    omar@${SERVER_HOST}:/tmp/insert-demo-data.py

# Install dependencies and run script on server
echo "Running demo data insertion on server..."
ssh -i "${SSH_KEY}" omar@${SERVER_HOST} << 'ENDSSH'
    # Install Python and dependencies
    if ! command -v python3 &> /dev/null; then
        echo "Installing Python3..."
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip
    fi
    
    # Install requests library if not present
    python3 -c "import requests" 2>/dev/null || {
        echo "Installing requests library..."
        python3 -m pip install --user requests
    }
    
    # Run the demo data script
    echo ""
    echo "Inserting demo data..."
    python3 /tmp/insert-demo-data.py --host localhost --port 8081
    
    # Cleanup
    rm /tmp/insert-demo-data.py
ENDSSH

echo ""
echo "=========================================="
echo "Demo data insertion completed!"
echo "=========================================="
echo ""
echo "You can now access:"
echo "  - Time Series API: http://${SERVER_HOST}:8081/api/timeseries"
echo "  - Scheduler API: http://${SERVER_HOST}:8081/api/scheduler"
echo "  - Webapp: http://${SERVER_HOST}:3000"
