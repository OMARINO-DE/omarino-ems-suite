# Scheduler Service - OMARINO EMS Suite

The Scheduler Service provides workflow orchestration and job scheduling capabilities for the OMARINO Energy Management System. It uses Quartz.NET for scheduling and implements a DAG (Directed Acyclic Graph) workflow engine for complex task orchestration.

## Features

- **Workflow Engine**: Execute complex workflows with task dependencies (DAG)
- **Job Scheduling**: Cron-based, interval-based, webhook, and manual triggers
- **Task Types**: HTTP calls, delays, conditions, transformations, notifications
- **Persistence**: PostgreSQL for workflow definitions and execution history
- **Validation**: Cycle detection, dependency validation, configuration validation
- **Monitoring**: Execution tracking, task-level metrics, health checks
- **Retry Logic**: Configurable retry attempts with exponential backoff
- **Observability**: OpenTelemetry tracing, Prometheus metrics, Serilog logging

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Scheduler Service (ASP.NET Core 8)         │
│                                                          │
│  ┌────────────────┐      ┌──────────────────────┐      │
│  │   Quartz.NET   │      │   Workflow Engine    │      │
│  │   Scheduler    │──────│  - Validation        │      │
│  │  - Cron jobs   │      │  - Topological sort  │      │
│  │  - Triggers    │      │  - Task execution    │      │
│  └────────────────┘      └──────────────────────┘      │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │           Workflow Executor                     │    │
│  │  - HTTP Call  - Delay      - Condition         │    │
│  │  - Transform  - Notification                    │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────┐      ┌──────────────────────┐      │
│  │  PostgreSQL    │      │   REST API           │      │
│  │  - Workflows   │      │  - Workflows CRUD    │      │
│  │  - Executions  │      │  - Execution mgmt    │      │
│  │  - Tasks       │      │  - Scheduler control │      │
│  └────────────────┘      └──────────────────────┘      │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- .NET 8.0 SDK
- PostgreSQL 14+
- Docker (optional, for containerized deployment)

### Run Locally

```bash
# Navigate to the scheduler-service directory
cd scheduler-service

# Set up database connection
export ConnectionStrings__DefaultConnection="Host=localhost;Port=5432;Database=scheduler_dev;Username=postgres;Password=postgres"

# Restore dependencies
dotnet restore

# Apply database migrations
dotnet ef database update

# Run the service
dotnet run

# Or use dotnet watch for development
dotnet watch run
```

The Scheduler Service will start on:
- **HTTP**: http://localhost:5003
- **Swagger UI**: http://localhost:5003/swagger
- **Metrics**: http://localhost:9090/metrics

### Run with Docker

```bash
# Build the Docker image
docker build -t omarino-ems/scheduler-service:latest .

# Run with PostgreSQL
docker run -d \
  --name postgres-scheduler \
  -e POSTGRES_DB=scheduler \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:14

# Run the scheduler service
docker run -d \
  -p 5003:5003 \
  -p 9090:9090 \
  -e ConnectionStrings__DefaultConnection="Host=postgres-scheduler;Port=5432;Database=scheduler;Username=postgres;Password=postgres" \
  -e ServiceEndpoints__TimeseriesService="http://timeseries-service:5001" \
  -e ServiceEndpoints__ForecastService="http://forecast-service:8001" \
  -e ServiceEndpoints__OptimizeService="http://optimize-service:8002" \
  --link postgres-scheduler \
  --name scheduler-service \
  omarino-ems/scheduler-service:latest
```

## API Endpoints

### Workflows

#### POST /api/workflows
Create a new workflow.

**Request:**
```json
{
  "name": "Daily Forecast and Optimization",
  "description": "Run forecast and optimization every day at 6 AM",
  "tasks": [
    {
      "name": "Fetch Time Series Data",
      "type": "HttpCall",
      "config": {
        "url": "http://timeseries-service:5001/api/series/latest",
        "method": "GET"
      },
      "dependsOn": [],
      "timeout": "00:05:00"
    },
    {
      "name": "Run Forecast",
      "type": "HttpCall",
      "config": {
        "url": "http://forecast-service:8001/api/forecast/models/arima/forecast",
        "method": "POST",
        "body": {
          "series_id": "meter-001-load",
          "horizon_hours": 24
        }
      },
      "dependsOn": ["<task-1-id>"],
      "timeout": "00:10:00"
    },
    {
      "name": "Run Optimization",
      "type": "HttpCall",
      "config": {
        "url": "http://optimize-service:8002/api/optimize",
        "method": "POST",
        "body": {
          "type": "battery_dispatch",
          "start_time": "2025-10-02T06:00:00Z",
          "end_time": "2025-10-03T06:00:00Z"
        }
      },
      "dependsOn": ["<task-2-id>"],
      "timeout": "00:15:00"
    }
  ],
  "schedule": {
    "type": "Cron",
    "cronExpression": "0 6 * * *",
    "timeZone": "UTC"
  },
  "isEnabled": true,
  "maxExecutionTime": "01:00:00",
  "maxRetries": 3
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Daily Forecast and Optimization",
  "description": "Run forecast and optimization every day at 6 AM",
  "tasks": [...],
  "schedule": {...},
  "isEnabled": true,
  "createdAt": "2025-10-02T10:00:00Z",
  "updatedAt": "2025-10-02T10:00:00Z"
}
```

**Example:**
```bash
curl -X POST http://localhost:5003/api/workflows \
  -H "Content-Type: application/json" \
  -d @workflow.json
```

#### GET /api/workflows
Get all workflows.

**Example:**
```bash
curl http://localhost:5003/api/workflows
```

#### GET /api/workflows/{id}
Get a specific workflow by ID.

#### PUT /api/workflows/{id}
Update a workflow.

#### DELETE /api/workflows/{id}
Delete a workflow.

#### POST /api/workflows/validate
Validate a workflow definition without creating it.

**Example:**
```bash
curl -X POST http://localhost:5003/api/workflows/validate \
  -H "Content-Type: application/json" \
  -d @workflow.json
```

#### POST /api/workflows/{id}/trigger
Trigger a workflow execution immediately (manual trigger).

**Example:**
```bash
curl -X POST http://localhost:5003/api/workflows/550e8400-e29b-41d4-a716-446655440000/trigger
```

### Executions

#### GET /api/executions
Get workflow executions with optional filtering.

**Query Parameters:**
- `workflowId` (optional): Filter by workflow ID
- `limit` (default: 100): Maximum number of executions to return

**Example:**
```bash
# Get all executions
curl http://localhost:5003/api/executions

# Get executions for a specific workflow
curl "http://localhost:5003/api/executions?workflowId=550e8400-e29b-41d4-a716-446655440000&limit=50"
```

#### GET /api/executions/{id}
Get a specific execution by ID.

**Response:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "workflowId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "Completed",
  "taskExecutions": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440002",
      "taskId": "880e8400-e29b-41d4-a716-446655440003",
      "taskName": "Fetch Time Series Data",
      "status": "Completed",
      "result": "{\"statusCode\":200,\"body\":\"...\"}",
      "startedAt": "2025-10-02T06:00:00Z",
      "completedAt": "2025-10-02T06:00:02Z",
      "duration": "00:00:02"
    },
    {
      "id": "770e8400-e29b-41d4-a716-446655440004",
      "taskId": "880e8400-e29b-41d4-a716-446655440005",
      "taskName": "Run Forecast",
      "status": "Completed",
      "result": "{\"statusCode\":200,\"body\":\"...\"}",
      "startedAt": "2025-10-02T06:00:02Z",
      "completedAt": "2025-10-02T06:00:15Z",
      "duration": "00:00:13"
    }
  ],
  "triggerType": "Scheduled",
  "triggeredBy": "Quartz Scheduler",
  "startedAt": "2025-10-02T06:00:00Z",
  "completedAt": "2025-10-02T06:00:30Z",
  "duration": "00:00:30"
}
```

#### POST /api/executions/{id}/cancel
Cancel a running execution.

**Example:**
```bash
curl -X POST http://localhost:5003/api/executions/660e8400-e29b-41d4-a716-446655440001/cancel
```

### Scheduler

#### GET /api/scheduler/jobs
Get all scheduled jobs.

**Response:**
```json
[
  {
    "workflowId": "550e8400-e29b-41d4-a716-446655440000",
    "jobKey": "workflows.workflow-550e8400-e29b-41d4-a716-446655440000",
    "cronExpression": "0 6 * * *",
    "nextFireTime": "2025-10-03T06:00:00Z",
    "previousFireTime": "2025-10-02T06:00:00Z"
  }
]
```

#### POST /api/scheduler/jobs/{workflowId}/trigger
Trigger a scheduled job immediately.

#### GET /api/scheduler/info
Get scheduler service information.

### Health Checks

#### GET /api/health
Service health check (includes database and Quartz scheduler status).

**Response:**
```json
{
  "status": "Healthy",
  "checks": [
    {
      "name": "npgsql",
      "status": "Healthy",
      "duration": 12.5
    },
    {
      "name": "quartz",
      "status": "Healthy",
      "description": "Quartz scheduler is running with 3 scheduled job(s)",
      "duration": 5.2
    }
  ],
  "totalDuration": 17.7
}
```

## Workflow Task Types

### 1. HttpCall
Make an HTTP request to any service.

**Configuration:**
```json
{
  "type": "HttpCall",
  "config": {
    "url": "https://api.example.com/endpoint",
    "method": "POST",
    "headers": {
      "Authorization": "Bearer token",
      "Content-Type": "application/json"
    },
    "body": {
      "key": "value"
    }
  }
}
```

### 2. Delay
Wait for a specified duration.

**Configuration:**
```json
{
  "type": "Delay",
  "config": {
    "duration": 300
  }
}
```

### 3. Condition
Conditional branching (basic implementation).

**Configuration:**
```json
{
  "type": "Condition",
  "config": {
    "condition": "result.status == 'success'"
  }
}
```

### 4. Transform
Data transformation (basic implementation).

**Configuration:**
```json
{
  "type": "Transform",
  "config": {
    "transform": "map(x => x * 2)"
  }
}
```

### 5. Notification
Send notifications (log, email, webhook).

**Configuration:**
```json
{
  "type": "Notification",
  "config": {
    "type": "log",
    "message": "Workflow completed successfully"
  }
}
```

## Workflow Examples

### Example 1: Simple HTTP Call Chain

```json
{
  "name": "Forecast Pipeline",
  "tasks": [
    {
      "id": "task-1",
      "name": "Fetch Data",
      "type": "HttpCall",
      "config": {
        "url": "http://timeseries-service:5001/api/series/meter-001-load",
        "method": "GET"
      }
    },
    {
      "id": "task-2",
      "name": "Run Forecast",
      "type": "HttpCall",
      "config": {
        "url": "http://forecast-service:8001/api/forecast",
        "method": "POST"
      },
      "dependsOn": ["task-1"]
    }
  ]
}
```

### Example 2: Parallel Tasks with Final Aggregation

```json
{
  "name": "Parallel Optimization",
  "tasks": [
    {
      "id": "task-1",
      "name": "Battery Optimization",
      "type": "HttpCall",
      "config": {
        "url": "http://optimize-service:8002/api/optimize",
        "body": { "type": "battery_dispatch" }
      }
    },
    {
      "id": "task-2",
      "name": "Generator Optimization",
      "type": "HttpCall",
      "config": {
        "url": "http://optimize-service:8002/api/optimize",
        "body": { "type": "unit_commitment" }
      }
    },
    {
      "id": "task-3",
      "name": "Aggregate Results",
      "type": "HttpCall",
      "config": {
        "url": "http://aggregator-service/api/aggregate",
        "method": "POST"
      },
      "dependsOn": ["task-1", "task-2"]
    }
  ]
}
```

## Scheduling

### Cron Expressions

The scheduler uses standard cron expressions:

```
┌───────────── second (0-59)
│ ┌───────────── minute (0-59)
│ │ ┌───────────── hour (0-23)
│ │ │ ┌───────────── day of month (1-31)
│ │ │ │ ┌───────────── month (1-12)
│ │ │ │ │ ┌───────────── day of week (0-6, Sunday=0)
│ │ │ │ │ │
* * * * * *
```

**Examples:**

| Cron Expression | Description |
|----------------|-------------|
| `0 0 * * *` | Every day at midnight |
| `0 6 * * *` | Every day at 6 AM |
| `*/15 * * * *` | Every 15 minutes |
| `0 0 * * 0` | Every Sunday at midnight |
| `0 9 * * 1-5` | Every weekday at 9 AM |
| `0 0 1 * *` | First day of every month at midnight |

### Schedule Types

1. **Cron**: Use cron expressions for complex schedules
2. **Interval**: Fixed interval (e.g., every 5 minutes)
3. **Webhook**: Triggered by external webhook
4. **Manual**: Triggered manually via API

## Database Schema

### WorkflowDefinitions Table

| Column | Type | Description |
|--------|------|-------------|
| Id | UUID | Primary key |
| Name | VARCHAR(200) | Workflow name |
| Description | VARCHAR(1000) | Optional description |
| Tasks | JSONB | Task definitions (JSON) |
| Schedule | JSONB | Schedule configuration (JSON) |
| IsEnabled | BOOLEAN | Whether workflow is active |
| MaxExecutionTime | INTERVAL | Maximum execution duration |
| MaxRetries | INTEGER | Number of retry attempts |
| Tags | JSONB | Tags for categorization |
| CreatedAt | TIMESTAMPTZ | Creation timestamp |
| UpdatedAt | TIMESTAMPTZ | Last update timestamp |

### WorkflowExecutions Table

| Column | Type | Description |
|--------|------|-------------|
| Id | UUID | Primary key |
| WorkflowId | UUID | Foreign key to WorkflowDefinitions |
| Status | VARCHAR(50) | Execution status (Pending, Running, Completed, Failed, Cancelled, TimedOut) |
| Result | TEXT | Overall execution result (JSON) |
| ErrorMessage | TEXT | Error message if failed |
| TriggerType | VARCHAR(50) | How execution was triggered |
| TriggeredBy | VARCHAR(200) | User or system that triggered |
| CreatedAt | TIMESTAMPTZ | Creation timestamp |
| StartedAt | TIMESTAMPTZ | Execution start time |
| CompletedAt | TIMESTAMPTZ | Execution completion time |

### TaskExecutions Table

| Column | Type | Description |
|--------|------|-------------|
| Id | UUID | Primary key |
| ExecutionId | UUID | Foreign key to WorkflowExecutions |
| TaskId | UUID | Task definition ID |
| TaskName | VARCHAR(200) | Task name (denormalized) |
| Status | VARCHAR(50) | Task status |
| Result | TEXT | Task result (JSON) |
| ErrorMessage | TEXT | Error message if failed |
| RetryCount | INTEGER | Number of retry attempts |
| CreatedAt | TIMESTAMPTZ | Creation timestamp |
| StartedAt | TIMESTAMPTZ | Task start time |
| CompletedAt | TIMESTAMPTZ | Task completion time |

## Configuration

### Environment Variables

```bash
# Database
CONNECTION_STRING=Host=postgres;Port=5432;Database=scheduler;Username=postgres;Password=postgres

# Quartz.NET
QUARTZ_INSTANCE_NAME=OmarinoEmsScheduler
QUARTZ_THREAD_POOL_MAX_CONCURRENCY=10

# Workflow Engine
WORKFLOW_MAX_EXECUTION_TIME=01:00:00
WORKFLOW_MAX_RETRIES=3
WORKFLOW_RETRY_DELAY=00:00:30

# Backend Services
TIMESERIES_SERVICE_URL=http://timeseries-service:5001
FORECAST_SERVICE_URL=http://forecast-service:8001
OPTIMIZE_SERVICE_URL=http://optimize-service:8002

# Observability
PROMETHEUS_PORT=9090
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

## Development

### Project Structure

```
scheduler-service/
├── Controllers/           # API controllers
│   ├── WorkflowsController.cs
│   ├── ExecutionsController.cs
│   └── SchedulerController.cs
├── Models/                # Domain models
│   ├── WorkflowDefinition.cs
│   └── WorkflowExecution.cs
├── Services/              # Business logic services
│   ├── IWorkflowEngine.cs
│   ├── WorkflowEngine.cs
│   ├── IWorkflowExecutor.cs
│   ├── WorkflowExecutor.cs
│   ├── ISchedulerManager.cs
│   ├── SchedulerManager.cs
│   ├── IJobRepository.cs
│   ├── JobRepository.cs
│   └── QuartzHealthCheck.cs
├── Data/                  # Database context
│   └── SchedulerDbContext.cs
├── tests/                 # Unit and integration tests
├── Program.cs             # Application entry point
├── appsettings.json       # Configuration
├── Dockerfile             # Container image
└── README.md              # This file
```

### Running Tests

```bash
# Run all tests
dotnet test

# Run with coverage
dotnet test --collect:"XPlat Code Coverage"

# Run specific test
dotnet test --filter "FullyQualifiedName~WorkflowValidationTests"
```

### Database Migrations

```bash
# Add a new migration
dotnet ef migrations add MigrationName

# Apply migrations
dotnet ef database update

# Rollback migration
dotnet ef database update PreviousMigrationName

# Remove last migration
dotnet ef migrations remove
```

## Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: scheduler
      POSTGRES_PASSWORD: postgres
    volumes:
      - scheduler-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  scheduler-service:
    image: omarino-ems/scheduler-service:latest
    ports:
      - "5003:5003"
      - "9090:9090"
    environment:
      - ConnectionStrings__DefaultConnection=Host=postgres;Port=5432;Database=scheduler;Username=postgres;Password=postgres
      - ServiceEndpoints__TimeseriesService=http://timeseries-service:5001
      - ServiceEndpoints__ForecastService=http://forecast-service:8001
      - ServiceEndpoints__OptimizeService=http://optimize-service:8002
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  scheduler-data:
```

## Troubleshooting

### Database Connection Issues

**Problem**: Service fails to connect to PostgreSQL.

**Solution**:
1. Check connection string is correct
2. Ensure PostgreSQL is running and accessible
3. Verify database exists: `psql -U postgres -l`
4. Check network connectivity in Docker: `docker network inspect bridge`

### Workflow Not Executing

**Problem**: Scheduled workflow doesn't run.

**Solution**:
1. Check workflow is enabled: `GET /api/workflows/{id}`
2. Verify cron expression: `POST /api/workflows/validate`
3. Check Quartz scheduler status: `GET /api/health`
4. View scheduled jobs: `GET /api/scheduler/jobs`
5. Check logs for errors

### Task Execution Timeout

**Problem**: Tasks timeout before completion.

**Solution**:
1. Increase task timeout in workflow definition
2. Increase workflow max execution time
3. Check backend service performance
4. Review task logs in execution details

## License

Part of the OMARINO EMS Suite. See main repository for license information.

## Support

For issues and questions:
- Create an issue in the main repository
- Check the [architecture documentation](../docs/architecture.md)
- Review Quartz.NET documentation: https://www.quartz-scheduler.net/
