# Optimize Service

**Energy optimization microservice** for the OMARINO EMS Suite.

Provides mathematical optimization using Pyomo with multiple solvers (HiGHS, CBC, GLPK) for battery dispatch, unit commitment, procurement optimization, and more.

---

## Features

- **Multiple Optimization Types**
  - **Battery Dispatch**: Optimize charge/discharge schedule to minimize costs
  - **Unit Commitment**: Generator on/off scheduling with startup costs
  - **Procurement**: Energy procurement optimization from grid
  - **Self-Consumption**: Maximize renewable energy self-consumption
  - **Peak Shaving**: Minimize peak demand charges

- **Mathematical Programming**
  - Linear Programming (LP) and Mixed-Integer Linear Programming (MILP)
  - Pyomo modeling framework
  - Multiple solver support (HiGHS, CBC, GLPK, Gurobi, CPLEX)

- **REST API**
  - FastAPI with automatic OpenAPI documentation
  - Asynchronous optimization (background tasks)
  - Job status tracking and result retrieval

- **Production Features**
  - Time series interpolation for price/forecast data
  - Configurable solver timeout and MIP gap
  - Cost breakdown (energy, fuel, startup, degradation)
  - Sensitivity analysis

---

## Quick Start

### Prerequisites

- Python 3.11+
- Optimization solvers (at least one):
  - HiGHS (recommended, open-source)
  - CBC (open-source, MILP)
  - GLPK (open-source, basic LP)

### Local Development

1. **Navigate to service**
   ```bash
   cd optimize-service
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install solvers (Ubuntu/Debian)**
   ```bash
   sudo apt-get update
   sudo apt-get install coinor-cbc glpk-utils
   
   # HiGHS is included via pip (highspy)
   ```

5. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. **Run service**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
   ```

7. **Access API documentation**
   - Swagger UI: http://localhost:8002/api/docs
   - ReDoc: http://localhost:8002/api/redoc
   - Prometheus metrics: http://localhost:9090/metrics

### Docker

```bash
# Build image (includes CBC and GLPK solvers)
docker build -t omarino/optimize-service:latest .

# Run container
docker run -d \
  --name optimize-service \
  -p 8002:8002 \
  -p 9090:9090 \
  omarino/optimize-service:latest
```

---

## API Usage

### 1. Battery Dispatch Optimization

Optimize battery charge/discharge schedule to minimize energy costs.

```bash
curl -X POST http://localhost:8002/api/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "optimization_type": "battery_dispatch",
    "objective": "minimize_cost",
    "start_time": "2024-01-15T00:00:00Z",
    "end_time": "2024-01-15T23:00:00Z",
    "time_step_minutes": 15,
    "assets": [
      {
        "asset_id": "battery-1",
        "asset_type": "battery",
        "name": "Main Battery",
        "battery": {
          "capacity_kwh": 200.0,
          "max_charge_kw": 100.0,
          "max_discharge_kw": 100.0,
          "efficiency": 0.95,
          "initial_soc": 0.5,
          "min_soc": 0.1,
          "max_soc": 0.9,
          "degradation_cost_per_kwh": 0.01
        }
      },
      {
        "asset_id": "grid-1",
        "asset_type": "grid_connection",
        "name": "Grid Connection",
        "grid": {
          "max_import_kw": 300.0,
          "max_export_kw": 200.0
        }
      }
    ],
    "import_prices": {
      "timestamps": ["2024-01-15T00:00:00Z", "2024-01-15T06:00:00Z", "2024-01-15T12:00:00Z", "2024-01-15T18:00:00Z", "2024-01-15T23:00:00Z"],
      "values": [0.08, 0.12, 0.25, 0.30, 0.10]
    },
    "export_prices": {
      "timestamps": ["2024-01-15T00:00:00Z", "2024-01-15T23:00:00Z"],
      "values": [0.05, 0.05]
    },
    "load_forecast": {
      "timestamps": ["2024-01-15T00:00:00Z", "2024-01-15T23:00:00Z"],
      "values": [80.0, 80.0]
    },
    "solver": "highs",
    "time_limit_seconds": 300,
    "mip_gap": 0.01
  }'
```

**Response (202 Accepted)**:
```json
{
  "optimization_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "optimization_type": "battery_dispatch",
  "created_at": "2024-01-15T10:00:00Z",
  "schedule": [],
  "objective_value": null
}
```

### 2. Get Optimization Result

```bash
curl http://localhost:8002/api/optimize/123e4567-e89b-12d3-a456-426614174000
```

**Response (when completed)**:
```json
{
  "optimization_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "optimization_type": "battery_dispatch",
  "created_at": "2024-01-15T10:00:00Z",
  "completed_at": "2024-01-15T10:00:45Z",
  "schedule": [
    {
      "timestamp": "2024-01-15T00:00:00Z",
      "battery_charge_kw": 50.0,
      "battery_discharge_kw": 0.0,
      "battery_soc": 0.525,
      "grid_import_kw": 130.0,
      "grid_export_kw": 0.0,
      "load_kw": 80.0,
      "cost": 10.4
    },
    ...
  ],
  "objective_value": 245.67,
  "total_cost": 245.67,
  "energy_cost": 240.50,
  "degradation_cost": 5.17,
  "solver_info": {
    "solver_name": "highs",
    "status": "optimal",
    "objective_value": 245.67,
    "solve_time_seconds": 2.345
  }
}
```

### 3. Unit Commitment Optimization

```bash
curl -X POST http://localhost:8002/api/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "optimization_type": "unit_commitment",
    "start_time": "2024-01-15T00:00:00Z",
    "end_time": "2024-01-15T23:00:00Z",
    "time_step_minutes": 60,
    "assets": [
      {
        "asset_id": "gen-1",
        "asset_type": "generator",
        "name": "Diesel Generator",
        "generator": {
          "capacity_kw": 500.0,
          "min_output_kw": 100.0,
          "fuel_cost_per_kwh": 0.20,
          "startup_cost": 500.0,
          "shutdown_cost": 200.0,
          "min_uptime_hours": 2,
          "min_downtime_hours": 1
        }
      }
    ],
    "load_forecast": {
      "timestamps": ["2024-01-15T00:00:00Z", "2024-01-15T12:00:00Z", "2024-01-15T23:00:00Z"],
      "values": [200.0, 450.0, 200.0]
    },
    "solver": "cbc"
  }'
```

### 4. List Optimization Types

```bash
curl http://localhost:8002/api/types
```

### 5. List All Optimizations

```bash
# All optimizations
curl http://localhost:8002/api/optimize

# Filter by status
curl "http://localhost:8002/api/optimize?status=completed"

# Filter by type
curl "http://localhost:8002/api/optimize?optimization_type=battery_dispatch"
```

### 6. Cancel Optimization

```bash
curl -X DELETE http://localhost:8002/api/optimize/123e4567-e89b-12d3-a456-426614174000
```

---

## Optimization Models

### Battery Dispatch

**Objective**: Minimize total cost (energy purchase - energy sales + battery degradation)

**Decision Variables**:
- Battery charge power (kW) at each time step
- Battery discharge power (kW) at each time step
- Grid import power (kW)
- Grid export power (kW)

**Constraints**:
- Energy balance: Import + Discharge = Load + Charge + Export
- Battery SOC dynamics: SOC[t] = SOC[t-1] + (Charge * η - Discharge) * Δt
- Battery capacity limits: min_SOC ≤ SOC[t] ≤ max_SOC
- Power limits: 0 ≤ Charge ≤ max_charge, 0 ≤ Discharge ≤ max_discharge
- Grid connection limits: Import ≤ max_import, Export ≤ max_export

**Cost Components**:
- Energy cost: Σ (Import[t] * price_import[t] - Export[t] * price_export[t]) * Δt
- Degradation cost: Σ (Charge[t] + Discharge[t]) * degradation_cost * Δt

### Unit Commitment

**Objective**: Minimize total cost (fuel + startup + shutdown)

**Decision Variables**:
- Generator output power (kW)
- Generator on/off status (binary)
- Startup indicator (binary)
- Shutdown indicator (binary)

**Constraints**:
- Meet load: Output[t] ≥ Load[t]
- Minimum output when on: Output[t] ≥ min_output * Status[t]
- Maximum output: Output[t] ≤ max_output * Status[t]
- Startup/shutdown logic: Startup[t] ≥ Status[t] - Status[t-1]
- Minimum uptime/downtime (optional, requires additional constraints)

**Cost Components**:
- Fuel cost: Σ Output[t] * fuel_cost * Δt
- Startup cost: Σ Startup[t] * startup_cost
- Shutdown cost: Σ Shutdown[t] * shutdown_cost

---

## Solvers

### Solver Comparison

| Solver | Type | License | Speed | MILP Support | Recommended For |
|--------|------|---------|-------|--------------|-----------------|
| **HiGHS** | LP/MILP | Open-source | Fast | ✅ | All problems (default) |
| **CBC** | MILP | Open-source | Medium | ✅ | Unit commitment |
| **GLPK** | LP | Open-source | Slow | ❌ | Simple LP only |
| **Gurobi** | LP/MILP | Commercial | Very fast | ✅ | Large-scale problems |
| **CPLEX** | LP/MILP | Commercial | Very fast | ✅ | Large-scale problems |

### Solver Installation

**HiGHS** (Python package):
```bash
pip install highspy
```

**CBC** (Ubuntu/Debian):
```bash
sudo apt-get install coinor-cbc coinor-libcbc-dev
```

**GLPK** (Ubuntu/Debian):
```bash
sudo apt-get install glpk-utils libglpk-dev
```

**Gurobi/CPLEX**: Requires commercial license and installation

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_NAME` | Service identifier | `optimize-service` |
| `API_PORT` | HTTP port | `8002` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis for task queue | `redis://localhost:6379/0` |
| `DEFAULT_SOLVER` | Default solver | `highs` |
| `SOLVER_TIMEOUT_SECONDS` | Solver time limit | `300` (5 min) |
| `MAX_TIME_HORIZON_HOURS` | Maximum optimization horizon | `168` (1 week) |
| `MAX_ASSETS` | Maximum assets per optimization | `50` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ENABLE_METRICS` | Enable Prometheus metrics | `true` |
| `METRICS_PORT` | Metrics endpoint port | `9090` |

---

## Development

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_optimization_service.py

# Skip tests requiring solvers
pytest -m "not slow"
```

### Code Quality

```bash
# Format code
black app/ tests/

# Lint
ruff check app/ tests/

# Type check
mypy app/

# Run all checks
black app/ tests/ && ruff check app/ tests/ && mypy app/
```

### Project Structure

```
optimize-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration
│   ├── models.py               # Pydantic models (API contracts)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── optimize.py         # Optimization endpoints
│   │   └── health.py           # Health checks
│   └── services/
│       ├── __init__.py
│       ├── optimization_service.py  # Core Pyomo models
│       └── solver_manager.py        # Solver detection
├── tests/
│   ├── __init__.py
│   ├── test_api.py                  # Integration tests
│   └── test_optimization_service.py # Unit tests
├── requirements.txt
├── pyproject.toml              # Tool configuration
├── Dockerfile
├── .dockerignore
├── .env.example
└── README.md
```

---

## Architecture

### Data Flow

```
1. Client → POST /api/optimize (optimization request)
2. Optimize Service → Create job (status: pending)
3. Optimize Service → Background task starts
4. Build Pyomo model → Solve with selected solver
5. Extract results → Update job (status: completed)
6. Client → GET /api/optimize/{id} (retrieve results)
```

### Optimization Pipeline

```
Request Validation
  ↓
Time Step Generation
  ↓
Time Series Interpolation (prices, forecasts)
  ↓
Pyomo Model Construction
  - Define sets, parameters, variables
  - Add objective function
  - Add constraints
  ↓
Solver Invocation (HiGHS/CBC/GLPK)
  ↓
Result Extraction
  ↓
Cost Breakdown Calculation
  ↓
Response Formatting
```

---

## Performance

### Benchmarks

| Problem Size | Time Steps | Assets | Solver | Solve Time | Memory |
|--------------|------------|--------|--------|------------|--------|
| Small | 96 (1 day, 15 min) | 2 | HiGHS | ~1s | ~50 MB |
| Medium | 672 (1 week, 15 min) | 5 | HiGHS | ~5s | ~200 MB |
| Large | 672 (1 week, 15 min) | 10 | HiGHS | ~20s | ~500 MB |
| Unit Commitment | 96 | 3 generators | CBC | ~10s | ~100 MB |

### Optimization Tips

1. **Reduce time horizon**: Shorter horizons solve faster
2. **Increase time step**: 60-min steps instead of 15-min
3. **Use HiGHS**: Fastest open-source solver
4. **Set MIP gap**: 1-5% gap acceptable for most problems
5. **Limit solver time**: Use timeout to prevent long runs

---

## Troubleshooting

### Common Issues

**Issue**: `No solvers available` error
- **Solution**: Install at least one solver (CBC, GLPK, or pip install highspy)

**Issue**: `Solver not available: highs`
- **Solution**: `pip install highspy` or use `"solver": "cbc"` in request

**Issue**: `Infeasible` solver status
- **Solution**: Check constraints (battery SOC limits, load > capacity, etc.)

**Issue**: Optimization takes too long
- **Solution**: Reduce time horizon, increase time step, or set lower `time_limit_seconds`

**Issue**: `Time horizon exceeds maximum`
- **Solution**: Reduce optimization horizon or increase `MAX_TIME_HORIZON_HOURS` env var

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn app.main:app --log-level debug

# Test solver availability
python -c "from app.services.solver_manager import SolverManager; print(SolverManager().get_available_solvers())"
```

---

## Advanced Topics

### Custom Constraints

Add custom constraints to optimization request:

```json
{
  "constraints": [
    {
      "name": "max_peak_demand",
      "type": "peak_limit",
      "value": 200.0,
      "penalty": 1000.0
    }
  ]
}
```

### Sensitivity Analysis

The service automatically calculates sensitivities for key parameters:
- Import price changes
- Battery capacity changes
- Load forecast changes

Access in response:
```json
{
  "sensitivities": [
    {
      "parameter": "import_price_avg",
      "base_value": 0.20,
      "objective_change_per_unit": 150.0
    }
  ]
}
```

### Multi-Asset Optimization

Optimize multiple batteries, generators, and grid connections:

```json
{
  "assets": [
    {"asset_id": "battery-1", ...},
    {"asset_id": "battery-2", ...},
    {"asset_id": "gen-1", ...},
    {"asset_id": "grid-1", ...}
  ]
}
```

---

## Roadmap

- [ ] **Stochastic optimization**: Scenario-based optimization
- [ ] **Robust optimization**: Worst-case optimization
- [ ] **Multi-objective**: Pareto frontier (cost vs emissions)
- [ ] **Rolling horizon**: Receding horizon optimization
- [ ] **Warm start**: Use previous solution as starting point
- [ ] **Distributed optimization**: ADMM for large-scale problems
- [ ] **Renewable curtailment**: Optimize PV/wind curtailment
- [ ] **Electric vehicle charging**: EV fleet optimization
- [ ] **Demand response**: Load shifting optimization
- [ ] **Reserve markets**: Ancillary services optimization

---

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines.

---

## License

MIT License - see [LICENSE](../LICENSE) for details.

---

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/omarino-ems/issues
- Documentation: https://your-org.github.io/omarino-ems/
