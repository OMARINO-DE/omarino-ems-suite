FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS base
WORKDIR /app
EXPOSE 5003
EXPOSE 9090

FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY ["SchedulerService.csproj", "./"]
RUN dotnet restore "./SchedulerService.csproj"
COPY . .
WORKDIR "/src/."
RUN dotnet build "SchedulerService.csproj" -c Release -o /app/build

FROM build AS publish
RUN dotnet publish "SchedulerService.csproj" -c Release -o /app/publish /p:UseAppHost=false

FROM base AS final
WORKDIR /app

# Install curl for health checks (before creating user)
USER root
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY --from=publish /app/publish .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5003/api/health || exit 1

ENTRYPOINT ["dotnet", "SchedulerService.dll"]
