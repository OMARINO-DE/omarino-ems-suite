#!/bin/bash
# Redeploy webapp on remote server

echo "📥 Pulling latest code..."
cd /home/omar/git && git pull

echo "🔨 Building webapp image..."
cd webapp
docker build -q -t 192.168.61.21:32768/omarino-ems/webapp:latest .

echo "🔄 Redeploying webapp container..."
docker stop omarino-webapp
docker rm omarino-webapp

docker run -d \
  --name omarino-webapp \
  --network ems_omarino-network \
  -p 3000:3000 \
  -e NODE_ENV=production \
  -e NEXT_PUBLIC_API_URL=http://192.168.75.20:8081 \
  192.168.61.21:32768/omarino-ems/webapp:latest

echo "✅ Waiting for webapp to start..."
sleep 5

echo "🧪 Testing webapp..."
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:3000

echo ""
echo "✅ Webapp redeployed successfully!"
echo "   Access at: http://192.168.75.20:3000"
