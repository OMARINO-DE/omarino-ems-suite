#!/bin/bash

echo "🚀 Running post-create setup for OMARINO EMS Suite..."

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
fi

# Install pre-commit hooks
echo "🔧 Installing pre-commit hooks..."
pre-commit install

# Install Python dependencies for services (if requirements.txt exists)
if [ -d "forecast-service" ] && [ -f "forecast-service/requirements.txt" ]; then
    echo "🐍 Installing forecast-service dependencies..."
    cd forecast-service && pip install -r requirements.txt && cd ..
fi

if [ -d "optimize-service" ] && [ -f "optimize-service/requirements.txt" ]; then
    echo "🐍 Installing optimize-service dependencies..."
    cd optimize-service && pip install -r requirements.txt && cd ..
fi

# Restore .NET projects
echo "📦 Restoring .NET dependencies..."
find . -name "*.csproj" -exec dirname {} \; | while read dir; do
    echo "  Restoring $dir..."
    (cd "$dir" && dotnet restore) || true
done

# Install Node.js dependencies for webapp
if [ -d "webapp" ] && [ -f "webapp/package.json" ]; then
    echo "⚛️  Installing webapp dependencies..."
    cd webapp && pnpm install && cd ..
fi

echo "✅ Post-create setup complete!"
echo "💡 Run 'make help' to see available commands"
echo "💡 Run 'make up' to start all services"
