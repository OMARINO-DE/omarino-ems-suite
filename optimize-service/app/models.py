"""
Pydantic models for optimize service API contracts.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class OptimizationType(str, Enum):
    """Available optimization types."""
    BATTERY_DISPATCH = "battery_dispatch"
    UNIT_COMMITMENT = "unit_commitment"
    PROCUREMENT = "procurement"
    SELF_CONSUMPTION = "self_consumption"
    PEAK_SHAVING = "peak_shaving"


class OptimizationStatus(str, Enum):
    """Optimization job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SolverType(str, Enum):
    """Available solvers."""
    HIGHS = "highs"  # Default: Open-source, fast
    CBC = "cbc"      # Open-source, MILP
    GLPK = "glpk"    # Open-source, basic
    GUROBI = "gurobi"  # Commercial (if licensed)
    CPLEX = "cplex"    # Commercial (if licensed)


class AssetType(str, Enum):
    """Energy asset types."""
    BATTERY = "battery"
    GENERATOR = "generator"
    GRID_CONNECTION = "grid_connection"
    LOAD = "load"
    SOLAR_PV = "solar_pv"
    WIND = "wind"


class BatterySpec(BaseModel):
    """Battery energy storage system specifications."""
    capacity_kwh: float = Field(..., gt=0, description="Battery capacity in kWh")
    max_charge_kw: float = Field(..., gt=0, description="Maximum charging power in kW")
    max_discharge_kw: float = Field(..., gt=0, description="Maximum discharging power in kW")
    efficiency: float = Field(0.95, ge=0, le=1, description="Round-trip efficiency")
    initial_soc: float = Field(0.5, ge=0, le=1, description="Initial state of charge (0-1)")
    min_soc: float = Field(0.1, ge=0, le=1, description="Minimum state of charge")
    max_soc: float = Field(0.9, ge=0, le=1, description="Maximum state of charge")
    degradation_cost_per_kwh: float = Field(0.01, ge=0, description="Degradation cost per kWh cycled")


class GeneratorSpec(BaseModel):
    """Generator specifications."""
    capacity_kw: float = Field(..., gt=0, description="Generator capacity in kW")
    min_output_kw: float = Field(0, ge=0, description="Minimum output when running")
    fuel_cost_per_kwh: float = Field(..., ge=0, description="Fuel cost per kWh generated")
    startup_cost: float = Field(0, ge=0, description="Cost to start generator")
    shutdown_cost: float = Field(0, ge=0, description="Cost to shut down generator")
    min_uptime_hours: int = Field(1, ge=0, description="Minimum running time once started")
    min_downtime_hours: int = Field(1, ge=0, description="Minimum off time once stopped")
    emissions_kg_co2_per_kwh: float = Field(0.5, ge=0, description="CO2 emissions per kWh")


class GridConnectionSpec(BaseModel):
    """Grid connection specifications."""
    max_import_kw: float = Field(..., gt=0, description="Maximum import power in kW")
    max_export_kw: float = Field(..., gt=0, description="Maximum export power in kW")
    import_enabled: bool = Field(True, description="Allow importing from grid")
    export_enabled: bool = Field(True, description="Allow exporting to grid")


class Asset(BaseModel):
    """Energy asset definition."""
    asset_id: str = Field(..., description="Unique asset identifier")
    asset_type: AssetType = Field(..., description="Type of asset")
    name: str = Field(..., description="Human-readable name")
    battery: Optional[BatterySpec] = None
    generator: Optional[GeneratorSpec] = None
    grid: Optional[GridConnectionSpec] = None


class PriceTimeSeries(BaseModel):
    """Time series of prices."""
    timestamps: List[datetime] = Field(..., description="Timestamps for each price point")
    values: List[float] = Field(..., description="Price values (currency per kWh)")
    
    @field_validator("values")
    @classmethod
    def validate_prices(cls, v: List[float], info) -> List[float]:
        """Ensure prices match timestamps."""
        timestamps = info.data.get("timestamps", [])
        if timestamps and len(v) != len(timestamps):
            raise ValueError(f"Price values ({len(v)}) must match timestamps ({len(timestamps)})")
        return v


class ForecastTimeSeries(BaseModel):
    """Time series forecast (e.g., load, solar generation)."""
    timestamps: List[datetime] = Field(..., description="Timestamps for each forecast point")
    values: List[float] = Field(..., description="Forecast values in kW")
    
    @field_validator("values")
    @classmethod
    def validate_forecast(cls, v: List[float], info) -> List[float]:
        """Ensure forecast matches timestamps."""
        timestamps = info.data.get("timestamps", [])
        if timestamps and len(v) != len(timestamps):
            raise ValueError(f"Forecast values ({len(v)}) must match timestamps ({len(timestamps)})")
        return v


class Constraint(BaseModel):
    """Optimization constraint."""
    name: str = Field(..., description="Constraint name")
    type: str = Field(..., description="Constraint type (e.g., 'max_peak_demand')")
    value: float = Field(..., description="Constraint value")
    penalty: float = Field(1000.0, ge=0, description="Penalty for violating constraint")


class OptimizeRequest(BaseModel):
    """Request for energy optimization."""
    optimization_type: OptimizationType = Field(..., description="Type of optimization")
    objective: str = Field("minimize_cost", description="Optimization objective")
    
    # Time horizon
    start_time: datetime = Field(..., description="Optimization start time")
    end_time: datetime = Field(..., description="Optimization end time")
    time_step_minutes: int = Field(15, ge=1, le=60, description="Time step in minutes")
    
    # Assets
    assets: List[Asset] = Field(..., min_length=1, description="Energy assets to optimize")
    
    # Prices
    import_prices: Optional[PriceTimeSeries] = Field(None, description="Grid import prices")
    export_prices: Optional[PriceTimeSeries] = Field(None, description="Grid export prices")
    
    # Forecasts
    load_forecast: Optional[ForecastTimeSeries] = Field(None, description="Load forecast")
    solar_forecast: Optional[ForecastTimeSeries] = Field(None, description="Solar generation forecast")
    wind_forecast: Optional[ForecastTimeSeries] = Field(None, description="Wind generation forecast")
    
    # Constraints
    constraints: List[Constraint] = Field(default_factory=list, description="Additional constraints")
    
    # Solver settings
    solver: SolverType = Field(SolverType.CBC, description="Optimization solver")
    time_limit_seconds: int = Field(300, ge=1, description="Solver time limit")
    mip_gap: float = Field(0.01, ge=0, le=1, description="MIP optimality gap tolerance")


class SchedulePoint(BaseModel):
    """Single point in optimization schedule."""
    timestamp: datetime
    battery_charge_kw: Optional[float] = Field(None, description="Battery charging power (positive)")
    battery_discharge_kw: Optional[float] = Field(None, description="Battery discharging power (positive)")
    battery_soc: Optional[float] = Field(None, ge=0, le=1, description="Battery state of charge")
    generator_output_kw: Optional[float] = Field(None, description="Generator output")
    generator_status: Optional[bool] = Field(None, description="Generator on/off status")
    grid_import_kw: Optional[float] = Field(None, description="Import from grid")
    grid_export_kw: Optional[float] = Field(None, description="Export to grid")
    load_kw: Optional[float] = Field(None, description="Load demand")
    cost: Optional[float] = Field(None, description="Cost for this time step")


class SolverInfo(BaseModel):
    """Solver execution information."""
    solver_name: str
    status: str = Field(..., description="Solver status (optimal, feasible, infeasible)")
    objective_value: float = Field(..., description="Objective function value")
    solve_time_seconds: float
    iterations: Optional[int] = None
    nodes_explored: Optional[int] = None
    gap: Optional[float] = Field(None, description="MIP gap at termination")


class Sensitivity(BaseModel):
    """Sensitivity analysis results."""
    parameter: str = Field(..., description="Parameter name")
    base_value: float = Field(..., description="Base parameter value")
    objective_change_per_unit: float = Field(..., description="Change in objective per unit change")


class OptimizeResponse(BaseModel):
    """Optimization result."""
    optimization_id: UUID = Field(..., description="Unique optimization job ID")
    status: OptimizationStatus = Field(..., description="Optimization status")
    optimization_type: OptimizationType
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    # Results
    schedule: List[SchedulePoint] = Field(default_factory=list, description="Optimized schedule")
    objective_value: Optional[float] = Field(None, description="Total objective value (e.g., cost)")
    
    # Breakdown
    total_cost: Optional[float] = None
    energy_cost: Optional[float] = None
    grid_cost: Optional[float] = None
    fuel_cost: Optional[float] = None
    startup_cost: Optional[float] = None
    degradation_cost: Optional[float] = None
    penalty_cost: Optional[float] = None
    
    # Solver info
    solver_info: Optional[SolverInfo] = None
    
    # Sensitivity analysis
    sensitivities: List[Sensitivity] = Field(default_factory=list)
    
    # Error info
    error: Optional[str] = None


class OptimizationJob(BaseModel):
    """Optimization job metadata."""
    optimization_id: UUID
    status: OptimizationStatus
    optimization_type: OptimizationType
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = Field(0.0, ge=0, le=1, description="Progress (0-1)")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: datetime
    solvers_available: List[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
