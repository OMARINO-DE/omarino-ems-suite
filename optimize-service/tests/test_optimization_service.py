"""
Unit tests for optimization service.
"""
from datetime import datetime, timedelta
import pytest

from app.models import (
    OptimizeRequest,
    OptimizationType,
    Asset,
    AssetType,
    BatterySpec,
    GridConnectionSpec,
    GeneratorSpec,
    PriceTimeSeries,
    ForecastTimeSeries,
    SolverType
)
from app.services.optimization_service import OptimizationService
from app.services.solver_manager import SolverManager
from uuid import uuid4


@pytest.fixture
def battery_asset():
    """Create battery asset for testing."""
    return Asset(
        asset_id="battery-1",
        asset_type=AssetType.BATTERY,
        name="Test Battery",
        battery=BatterySpec(
            capacity_kwh=100.0,
            max_charge_kw=50.0,
            max_discharge_kw=50.0,
            efficiency=0.95,
            initial_soc=0.5,
            min_soc=0.1,
            max_soc=0.9,
            degradation_cost_per_kwh=0.01
        )
    )


@pytest.fixture
def grid_asset():
    """Create grid connection asset."""
    return Asset(
        asset_id="grid-1",
        asset_type=AssetType.GRID_CONNECTION,
        name="Grid Connection",
        grid=GridConnectionSpec(
            max_import_kw=200.0,
            max_export_kw=100.0
        )
    )


@pytest.fixture
def generator_asset():
    """Create generator asset."""
    return Asset(
        asset_id="gen-1",
        asset_type=AssetType.GENERATOR,
        name="Test Generator",
        generator=GeneratorSpec(
            capacity_kw=150.0,
            min_output_kw=30.0,
            fuel_cost_per_kwh=0.15,
            startup_cost=100.0,
            shutdown_cost=50.0,
            min_uptime_hours=2,
            min_downtime_hours=1
        )
    )


@pytest.fixture
def optimization_service():
    """Create optimization service instance."""
    return OptimizationService()


class TestSolverManager:
    """Tests for SolverManager."""
    
    def test_get_available_solvers(self):
        """Test solver detection."""
        manager = SolverManager()
        solvers = manager.get_available_solvers()
        
        assert isinstance(solvers, list)
        # At least one solver should be available in Docker environment
        assert len(solvers) > 0
    
    def test_is_solver_available(self):
        """Test checking specific solver availability."""
        manager = SolverManager()
        
        # HiGHS should be available
        # (may fail in local dev without highspy installed)
        available_solvers = manager.get_available_solvers()
        
        for solver in available_solvers:
            assert manager.is_solver_available(solver)
        
        assert not manager.is_solver_available("nonexistent_solver")


class TestOptimizationService:
    """Tests for OptimizationService."""
    
    @pytest.mark.asyncio
    async def test_validate_request(self, optimization_service, battery_asset, grid_asset):
        """Test request validation."""
        request = OptimizeRequest(
            optimization_type=OptimizationType.BATTERY_DISPATCH,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=24),
            time_step_minutes=15,
            assets=[battery_asset, grid_asset],
            solver=SolverType.HIGHS
        )
        
        # Should not raise
        optimization_service._validate_request(request)
    
    @pytest.mark.asyncio
    async def test_validate_request_time_horizon_too_long(
        self, 
        optimization_service,
        battery_asset,
        grid_asset
    ):
        """Test validation fails for excessive time horizon."""
        request = OptimizeRequest(
            optimization_type=OptimizationType.BATTERY_DISPATCH,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(days=30),  # Too long
            time_step_minutes=15,
            assets=[battery_asset, grid_asset],
            solver=SolverType.HIGHS
        )
        
        with pytest.raises(ValueError, match="Time horizon"):
            optimization_service._validate_request(request)
    
    def test_generate_time_steps(self, optimization_service):
        """Test time step generation."""
        start = datetime(2024, 1, 1, 0, 0)
        end = datetime(2024, 1, 1, 2, 0)
        
        request = OptimizeRequest(
            optimization_type=OptimizationType.BATTERY_DISPATCH,
            start_time=start,
            end_time=end,
            time_step_minutes=15,
            assets=[],
            solver=SolverType.HIGHS
        )
        
        time_steps = optimization_service._generate_time_steps(request)
        
        assert len(time_steps) == 9  # 0:00, 0:15, 0:30, ..., 2:00
        assert time_steps[0] == start
        assert time_steps[-1] == end
    
    def test_interpolate_timeseries(self, optimization_service):
        """Test time series interpolation."""
        source_timestamps = [
            datetime(2024, 1, 1, 0, 0),
            datetime(2024, 1, 1, 1, 0),
            datetime(2024, 1, 1, 2, 0)
        ]
        source_values = [10.0, 20.0, 15.0]
        
        target_timestamps = [
            datetime(2024, 1, 1, 0, 0),
            datetime(2024, 1, 1, 0, 30),
            datetime(2024, 1, 1, 1, 0),
            datetime(2024, 1, 1, 1, 30),
            datetime(2024, 1, 1, 2, 0)
        ]
        
        result = optimization_service._interpolate_timeseries(
            source_timestamps,
            source_values,
            target_timestamps
        )
        
        assert len(result) == len(target_timestamps)
        assert result[0] == 10.0
        assert result[2] == 20.0
        assert result[4] == 15.0
        assert 10.0 < result[1] < 20.0  # Interpolated


class TestOptimizationModels:
    """Tests for optimization model construction."""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not SolverManager().get_available_solvers(),
        reason="No solvers available"
    )
    async def test_battery_dispatch_simple(
        self,
        optimization_service,
        battery_asset,
        grid_asset
    ):
        """Test simple battery dispatch optimization."""
        start = datetime(2024, 1, 1, 0, 0)
        end = datetime(2024, 1, 1, 4, 0)
        
        # Create price time series (high price at peak hours)
        timestamps = [start + timedelta(hours=i) for i in range(5)]
        import_prices = [0.10, 0.30, 0.40, 0.30, 0.10]  # Peak in middle
        
        request = OptimizeRequest(
            optimization_type=OptimizationType.BATTERY_DISPATCH,
            start_time=start,
            end_time=end,
            time_step_minutes=60,
            assets=[battery_asset, grid_asset],
            import_prices=PriceTimeSeries(
                timestamps=timestamps,
                values=import_prices
            ),
            load_forecast=ForecastTimeSeries(
                timestamps=timestamps,
                values=[50.0] * 5  # Constant load
            ),
            solver=SolverType.HIGHS if "highs" in SolverManager().get_available_solvers() 
                   else SolverType.CBC
        )
        
        result = await optimization_service.optimize(uuid4(), request)
        
        assert result.status == "completed" or result.status.value == "completed"
        assert result.schedule is not None
        assert len(result.schedule) > 0
        assert result.objective_value is not None
        assert result.solver_info is not None
