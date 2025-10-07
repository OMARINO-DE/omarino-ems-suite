"""
Core optimization service with Pyomo models.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
from uuid import UUID

import numpy as np
import pandas as pd
from pyomo.environ import (
    ConcreteModel,
    Set,
    Param,
    Var,
    Objective,
    Constraint,
    NonNegativeReals,
    Binary,
    minimize,
    SolverFactory,
    value
)
import structlog

from app.models import (
    OptimizeRequest,
    OptimizeResponse,
    SchedulePoint,
    SolverInfo,
    Sensitivity,
    OptimizationStatus,
    OptimizationType,
    AssetType
)
from app.services.solver_manager import SolverManager
from app.config import get_settings

logger = structlog.get_logger()


class OptimizationService:
    """Service for energy optimization using Pyomo."""
    
    def __init__(self):
        self.solver_manager = SolverManager()
        self.settings = get_settings()
    
    async def optimize(self, optimization_id: UUID, request: OptimizeRequest) -> OptimizeResponse:
        """
        Run optimization based on request type.
        
        Args:
            optimization_id: Unique optimization job ID
            request: Optimization request parameters
            
        Returns:
            OptimizeResponse with optimized schedule and results
        """
        start_time = time.time()
        
        try:
            # Validate request
            self._validate_request(request)
            
            # Build and solve model based on optimization type
            if request.optimization_type == OptimizationType.BATTERY_DISPATCH:
                result = self._optimize_battery_dispatch(request)
            elif request.optimization_type == OptimizationType.UNIT_COMMITMENT:
                result = self._optimize_unit_commitment(request)
            elif request.optimization_type == OptimizationType.PROCUREMENT:
                result = self._optimize_procurement(request)
            elif request.optimization_type == OptimizationType.SELF_CONSUMPTION:
                result = self._optimize_self_consumption(request)
            elif request.optimization_type == OptimizationType.PEAK_SHAVING:
                result = self._optimize_peak_shaving(request)
            else:
                raise ValueError(f"Unknown optimization type: {request.optimization_type}")
            
            solve_time = time.time() - start_time
            
            # Update result with metadata
            result.optimization_id = optimization_id
            result.status = OptimizationStatus.COMPLETED
            result.completed_at = datetime.utcnow()
            
            if result.solver_info:
                result.solver_info.solve_time_seconds = solve_time
            
            return result
            
        except Exception as e:
            logger.error("optimization_failed",
                        optimization_id=str(optimization_id),
                        error=str(e),
                        exc_info=True)
            
            return OptimizeResponse(
                optimization_id=optimization_id,
                status=OptimizationStatus.FAILED,
                optimization_type=request.optimization_type,
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                error=str(e)
            )
    
    def _validate_request(self, request: OptimizeRequest):
        """Validate optimization request."""
        # Check time horizon
        time_horizon_hours = (request.end_time - request.start_time).total_seconds() / 3600
        if time_horizon_hours > self.settings.max_time_horizon_hours:
            raise ValueError(
                f"Time horizon ({time_horizon_hours}h) exceeds maximum "
                f"({self.settings.max_time_horizon_hours}h)"
            )
        
        # Check number of assets
        if len(request.assets) > self.settings.max_assets:
            raise ValueError(
                f"Number of assets ({len(request.assets)}) exceeds maximum "
                f"({self.settings.max_assets})"
            )
        
        # Check solver availability
        if not self.solver_manager.is_solver_available(request.solver.value):
            raise ValueError(f"Solver '{request.solver.value}' is not available")
    
    def _optimize_battery_dispatch(self, request: OptimizeRequest) -> OptimizeResponse:
        """
        Optimize battery charge/discharge schedule to minimize energy costs.
        
        Decision variables:
        - Battery charge power (kW) at each time step
        - Battery discharge power (kW) at each time step
        - Grid import power (kW) at each time step
        - Grid export power (kW) at each time step
        
        Objective:
        - Minimize total cost (energy purchase - energy sales + battery degradation)
        
        Constraints:
        - Energy balance at each time step
        - Battery capacity limits
        - Battery SOC limits
        - Charge/discharge power limits
        - Grid connection limits
        """
        logger.info("building_battery_dispatch_model")
        
        # Find battery and grid assets
        battery_asset = next((a for a in request.assets if a.asset_type == AssetType.BATTERY), None)
        grid_asset = next((a for a in request.assets if a.asset_type == AssetType.GRID_CONNECTION), None)
        
        if not battery_asset or not battery_asset.battery:
            raise ValueError("Battery asset required for battery dispatch optimization")
        if not grid_asset or not grid_asset.grid:
            raise ValueError("Grid connection required for battery dispatch optimization")
        
        battery = battery_asset.battery
        grid = grid_asset.grid
        
        # Generate time steps
        time_steps = self._generate_time_steps(request)
        T = len(time_steps)
        
        # Get prices and forecasts
        import_prices = self._get_import_prices(request, time_steps)
        export_prices = self._get_export_prices(request, time_steps)
        load_forecast = self._get_load_forecast(request, time_steps)
        
        # Create Pyomo model
        model = ConcreteModel()
        
        # Sets
        model.T = Set(initialize=range(T))
        
        # Parameters
        model.import_price = Param(model.T, initialize=dict(enumerate(import_prices)))
        model.export_price = Param(model.T, initialize=dict(enumerate(export_prices)))
        model.demand = Param(model.T, initialize=dict(enumerate(load_forecast)))
        model.dt = Param(initialize=request.time_step_minutes / 60.0)  # Time step in hours
        
        # Battery parameters
        model.battery_capacity = Param(initialize=battery.capacity_kwh)
        model.battery_efficiency = Param(initialize=battery.efficiency)
        model.max_charge = Param(initialize=battery.max_charge_kw)
        model.max_discharge = Param(initialize=battery.max_discharge_kw)
        model.initial_soc = Param(initialize=battery.initial_soc * battery.capacity_kwh)
        model.min_soc = Param(initialize=battery.min_soc * battery.capacity_kwh)
        model.max_soc = Param(initialize=battery.max_soc * battery.capacity_kwh)
        model.degradation_cost = Param(initialize=battery.degradation_cost_per_kwh)
        
        # Grid parameters
        model.max_import = Param(initialize=grid.max_import_kw)
        model.max_export = Param(initialize=grid.max_export_kw)
        
        # Decision variables
        model.battery_charge = Var(model.T, domain=NonNegativeReals, bounds=(0, battery.max_charge_kw))
        model.battery_discharge = Var(model.T, domain=NonNegativeReals, bounds=(0, battery.max_discharge_kw))
        model.battery_soc = Var(model.T, domain=NonNegativeReals, bounds=(battery.min_soc * battery.capacity_kwh, 
                                                                           battery.max_soc * battery.capacity_kwh))
        model.grid_import = Var(model.T, domain=NonNegativeReals, bounds=(0, grid.max_import_kw))
        model.grid_export = Var(model.T, domain=NonNegativeReals, bounds=(0, grid.max_export_kw))
        
        # Objective: Minimize total cost
        def objective_rule(m):
            energy_cost = sum(m.grid_import[t] * m.import_price[t] * m.dt for t in m.T)
            energy_revenue = sum(m.grid_export[t] * m.export_price[t] * m.dt for t in m.T)
            degradation = sum((m.battery_charge[t] + m.battery_discharge[t]) * m.degradation_cost * m.dt 
                            for t in m.T)
            return energy_cost - energy_revenue + degradation
        
        model.objective = Objective(rule=objective_rule, sense=minimize)
        
        # Constraints
        
        # Energy balance
        def energy_balance_rule(m, t):
            return m.grid_import[t] + m.battery_discharge[t] == m.demand[t] + m.battery_charge[t] + m.grid_export[t]
        model.energy_balance = Constraint(model.T, rule=energy_balance_rule)
        
        # Battery SOC dynamics
        def soc_dynamics_rule(m, t):
            if t == 0:
                return m.battery_soc[t] == m.initial_soc + \
                       (m.battery_charge[t] * m.battery_efficiency - m.battery_discharge[t]) * m.dt
            else:
                return m.battery_soc[t] == m.battery_soc[t-1] + \
                       (m.battery_charge[t] * m.battery_efficiency - m.battery_discharge[t]) * m.dt
        model.soc_dynamics = Constraint(model.T, rule=soc_dynamics_rule)
        
        # Solve model
        solver = self.solver_manager.get_solver_factory(request.solver.value)
        solver.options['seconds'] = request.time_limit_seconds
        
        if request.solver.value in ['highs', 'cbc', 'gurobi', 'cplex']:
            solver.options['mipgap'] = request.mip_gap
        
        logger.info("solving_model", solver=request.solver.value, variables=T*5, constraints=T*2)
        results = solver.solve(model, tee=False)
        
        # Extract results
        schedule = []
        total_cost = 0
        energy_cost = 0
        degradation_cost = 0
        
        for t in range(T):
            charge = value(model.battery_charge[t])
            discharge = value(model.battery_discharge[t])
            soc = value(model.battery_soc[t])
            grid_imp = value(model.grid_import[t])
            grid_exp = value(model.grid_export[t])
            
            step_cost = (
                grid_imp * import_prices[t] * model.dt.value -
                grid_exp * export_prices[t] * model.dt.value +
                (charge + discharge) * battery.degradation_cost_per_kwh * model.dt.value
            )
            
            schedule.append(SchedulePoint(
                timestamp=time_steps[t],
                battery_charge_kw=charge,
                battery_discharge_kw=discharge,
                battery_soc=soc / battery.capacity_kwh,
                grid_import_kw=grid_imp,
                grid_export_kw=grid_exp,
                load_kw=load_forecast[t],
                cost=step_cost
            ))
            
            total_cost += step_cost
            energy_cost += grid_imp * import_prices[t] * model.dt.value - grid_exp * export_prices[t] * model.dt.value
            degradation_cost += (charge + discharge) * battery.degradation_cost_per_kwh * model.dt.value
        
        # Solver info
        solver_info = SolverInfo(
            solver_name=request.solver.value,
            status=str(results.solver.termination_condition),
            objective_value=value(model.objective),
            solve_time_seconds=0.0  # Will be updated by caller
        )
        
        return OptimizeResponse(
            optimization_id=UUID(int=0),  # Will be set by caller
            status=OptimizationStatus.COMPLETED,
            optimization_type=OptimizationType.BATTERY_DISPATCH,
            created_at=datetime.utcnow(),
            schedule=schedule,
            objective_value=total_cost,
            total_cost=total_cost,
            energy_cost=energy_cost,
            degradation_cost=degradation_cost,
            solver_info=solver_info
        )
    
    def _optimize_unit_commitment(self, request: OptimizeRequest) -> OptimizeResponse:
        """
        Optimize generator on/off schedule (unit commitment problem).
        
        This is a simplified implementation. For production use, consider
        more sophisticated formulations with ramping constraints, reserves, etc.
        """
        logger.info("building_unit_commitment_model")
        
        # Find generator assets
        generators = [a for a in request.assets if a.asset_type == AssetType.GENERATOR and a.generator]
        
        if not generators:
            raise ValueError("At least one generator required for unit commitment optimization")
        
        # For simplicity, implement single generator case
        # Multi-generator would require indexed variables
        generator_asset = generators[0]
        gen = generator_asset.generator
        
        # Generate time steps
        time_steps = self._generate_time_steps(request)
        T = len(time_steps)
        
        # Get load forecast
        load_forecast = self._get_load_forecast(request, time_steps)
        
        # Create model
        model = ConcreteModel()
        model.T = Set(initialize=range(T))
        
        # Parameters
        model.demand = Param(model.T, initialize=dict(enumerate(load_forecast)))
        model.dt = Param(initialize=request.time_step_minutes / 60.0)
        
        # Generator parameters
        model.max_output = Param(initialize=gen.capacity_kw)
        model.min_output = Param(initialize=gen.min_output_kw)
        model.fuel_cost = Param(initialize=gen.fuel_cost_per_kwh)
        model.startup_cost = Param(initialize=gen.startup_cost)
        
        # Variables
        model.output = Var(model.T, domain=NonNegativeReals, bounds=(0, gen.capacity_kw))
        model.status = Var(model.T, domain=Binary)  # 1 if on, 0 if off
        model.startup = Var(model.T, domain=Binary)  # 1 if starting up
        
        # Objective: Minimize cost
        def objective_rule(m):
            fuel = sum(m.output[t] * m.fuel_cost * m.dt for t in m.T)
            startup = sum(m.startup[t] * m.startup_cost for t in m.T)
            return fuel + startup
        
        model.objective = Objective(rule=objective_rule, sense=minimize)
        
        # Constraints
        
        # Meet load
        def load_constraint_rule(m, t):
            return m.output[t] >= m.demand[t]
        model.load_constraint = Constraint(model.T, rule=load_constraint_rule)
        
        # Output limits when on
        def min_output_rule(m, t):
            return m.output[t] >= m.min_output * m.status[t]
        model.min_output_constraint = Constraint(model.T, rule=min_output_rule)
        
        def max_output_rule(m, t):
            return m.output[t] <= m.max_output * m.status[t]
        model.max_output_constraint = Constraint(model.T, rule=max_output_rule)
        
        # Startup detection
        def startup_rule(m, t):
            if t == 0:
                return m.startup[t] >= m.status[t]
            else:
                return m.startup[t] >= m.status[t] - m.status[t-1]
        model.startup_constraint = Constraint(model.T, rule=startup_rule)
        
        # Solve
        solver = self.solver_manager.get_solver_factory(request.solver.value)
        solver.options['seconds'] = request.time_limit_seconds
        results = solver.solve(model, tee=False)
        
        # Extract results
        schedule = []
        total_cost = 0
        fuel_cost = 0
        startup_cost_total = 0
        
        for t in range(T):
            output = value(model.output[t])
            status = bool(value(model.status[t]))
            startup = bool(value(model.startup[t]))
            
            step_fuel_cost = output * gen.fuel_cost_per_kwh * model.dt.value
            step_startup_cost = gen.startup_cost if startup else 0
            step_cost = step_fuel_cost + step_startup_cost
            
            schedule.append(SchedulePoint(
                timestamp=time_steps[t],
                generator_output_kw=output,
                generator_status=status,
                load_kw=load_forecast[t],
                cost=step_cost
            ))
            
            total_cost += step_cost
            fuel_cost += step_fuel_cost
            startup_cost_total += step_startup_cost
        
        solver_info = SolverInfo(
            solver_name=request.solver.value,
            status=str(results.solver.termination_condition),
            objective_value=value(model.objective),
            solve_time_seconds=0.0
        )
        
        return OptimizeResponse(
            optimization_id=UUID(int=0),
            status=OptimizationStatus.COMPLETED,
            optimization_type=OptimizationType.UNIT_COMMITMENT,
            created_at=datetime.utcnow(),
            schedule=schedule,
            objective_value=total_cost,
            total_cost=total_cost,
            fuel_cost=fuel_cost,
            startup_cost=startup_cost_total,
            solver_info=solver_info
        )
    
    def _optimize_procurement(self, request: OptimizeRequest) -> OptimizeResponse:
        """Optimize energy procurement from grid."""
        logger.info("procurement_optimization_not_fully_implemented")
        # Simplified: Use battery dispatch logic
        return self._optimize_battery_dispatch(request)
    
    def _optimize_self_consumption(self, request: OptimizeRequest) -> OptimizeResponse:
        """Maximize self-consumption of renewable energy."""
        logger.info("self_consumption_optimization_not_fully_implemented")
        # Simplified: Use battery dispatch logic
        return self._optimize_battery_dispatch(request)
    
    def _optimize_peak_shaving(self, request: OptimizeRequest) -> OptimizeResponse:
        """Minimize peak demand charges."""
        logger.info("peak_shaving_optimization_not_fully_implemented")
        # Simplified: Use battery dispatch logic
        return self._optimize_battery_dispatch(request)
    
    def _generate_time_steps(self, request: OptimizeRequest) -> List[datetime]:
        """Generate list of timestamps for optimization horizon."""
        time_steps = []
        current = request.start_time
        delta = timedelta(minutes=request.time_step_minutes)
        
        while current <= request.end_time:
            time_steps.append(current)
            current += delta
        
        return time_steps
    
    def _get_import_prices(self, request: OptimizeRequest, time_steps: List[datetime]) -> List[float]:
        """Get import prices for each time step."""
        if request.import_prices:
            # Interpolate provided prices to time steps
            return self._interpolate_timeseries(
                request.import_prices.timestamps,
                request.import_prices.values,
                time_steps
            )
        else:
            # Default constant price
            return [0.20] * len(time_steps)  # 20 cents/kWh
    
    def _get_export_prices(self, request: OptimizeRequest, time_steps: List[datetime]) -> List[float]:
        """Get export prices for each time step."""
        if request.export_prices:
            return self._interpolate_timeseries(
                request.export_prices.timestamps,
                request.export_prices.values,
                time_steps
            )
        else:
            # Default: export price = 50% of import price
            import_prices = self._get_import_prices(request, time_steps)
            return [p * 0.5 for p in import_prices]
    
    def _get_load_forecast(self, request: OptimizeRequest, time_steps: List[datetime]) -> List[float]:
        """Get load forecast for each time step."""
        if request.load_forecast:
            return self._interpolate_timeseries(
                request.load_forecast.timestamps,
                request.load_forecast.values,
                time_steps
            )
        else:
            # Default constant load
            return [100.0] * len(time_steps)  # 100 kW
    
    def _interpolate_timeseries(
        self,
        source_timestamps: List[datetime],
        source_values: List[float],
        target_timestamps: List[datetime]
    ) -> List[float]:
        """Interpolate time series to target timestamps."""
        # Convert to pandas for easy interpolation
        df_source = pd.DataFrame({
            'value': source_values
        }, index=pd.DatetimeIndex(source_timestamps))
        
        df_target = pd.DataFrame(index=pd.DatetimeIndex(target_timestamps))
        df_merged = df_target.join(df_source, how='left')
        df_merged['value'] = df_merged['value'].interpolate(method='linear').fillna(method='bfill').fillna(method='ffill')
        
        return df_merged['value'].tolist()
