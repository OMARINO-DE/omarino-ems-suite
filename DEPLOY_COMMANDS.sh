#!/bin/bash
# COPY AND PASTE THESE COMMANDS ONE BY ONE INTO YOUR TERMINAL
# Each section is a complete command block

echo "=========================================="
echo "Asset Service Deployment - Copy/Paste Guide"
echo "=========================================="
echo ""
echo "STEP 1: SSH to server"
echo "Copy this command:"
echo ""
cat << 'EOF'
ssh -i '/Users/omarzaror/Library/Mobile Documents/com~apple~CloudDocs/Developing/SSH-Key/server.pem' ubuntu@192.168.75.20
EOF
echo ""
echo "=========================================="
echo "STEP 2: Once logged in, copy and paste this entire block:"
echo ""
cat << 'EOF'
# Navigate to project
cd /home/ubuntu/omarino-ems-suite

# Pull latest code
echo "Pulling latest code..."
git pull origin main

# Initialize database schema
echo "Initializing database schema..."
cd asset-service/database

# Check if schema already exists
SCHEMA_EXISTS=$(PGPASSWORD=omarino_dev_pass psql -h localhost -U omarino -d omarino -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'assets');")

if [ "$SCHEMA_EXISTS" = "t" ]; then
    echo "✓ Database schema already exists, skipping..."
else
    echo "Applying database schema..."
    PGPASSWORD=omarino_dev_pass psql -h localhost -U omarino -d omarino -f schema.sql
    echo "✓ Database schema applied"
fi

# Go back to asset-service directory
cd /home/ubuntu/omarino-ems-suite/asset-service

# Stop and remove existing container
echo "Stopping existing container..."
docker stop omarino-asset-service 2>/dev/null || echo "No existing container"
docker rm omarino-asset-service 2>/dev/null || echo "Container removed"

# Build Docker image
echo "Building Docker image..."
docker build -t omarino-asset-service:latest .

# Run container
echo "Starting asset service..."
docker run -d \
  --name omarino-asset-service \
  --network omarino-network \
  --restart unless-stopped \
  -p 8003:8003 \
  -e DATABASE_URL=postgresql://omarino:omarino_dev_pass@postgres:5432/omarino \
  -e API_PREFIX=/api/assets \
  -e LOG_LEVEL=INFO \
  -e CORS_ORIGINS=* \
  omarino-asset-service:latest

# Wait for service to start
echo "Waiting for service to start..."
sleep 5

# Check health
echo "Checking service health..."
curl -s http://localhost:8003/api/assets/health | jq '.'

# Check container status
echo ""
echo "Container status:"
docker ps | grep omarino-asset-service

echo ""
echo "=========================================="
echo "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo "Service URLs:"
echo "  - Health: http://192.168.75.20:8003/api/assets/health"
echo "  - API Docs: http://192.168.75.20:8003/api/assets/docs"
echo ""
echo "View logs: docker logs -f omarino-asset-service"
echo ""
EOF
echo ""
echo "=========================================="
echo "STEP 3: After deployment, test the service"
echo "Copy and paste this to create a test battery:"
echo ""
cat << 'EOF'
curl -X POST http://localhost:8003/api/assets/batteries \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Demo Battery 1",
    "description": "100 kWh Tesla Powerpack for testing",
    "manufacturer": "Tesla",
    "model_number": "Powerpack 2",
    "serial_number": "TP2-DEMO-001",
    "installation_date": "2024-01-15",
    "chemistry": "lithium_ion",
    "capacity": 100.0,
    "usable_capacity": 90.0,
    "voltage": 400.0,
    "max_charge_rate": 50.0,
    "max_discharge_rate": 50.0,
    "efficiency": 0.95,
    "cycle_life": 6000,
    "depth_of_discharge": 90.0,
    "min_soc": 10.0,
    "max_soc": 90.0
  }' | jq '.'
EOF
echo ""
echo "=========================================="
echo "SAVE THE BATTERY asset_id FROM THE RESPONSE!"
echo "You'll need it for workflow integration."
echo "=========================================="
