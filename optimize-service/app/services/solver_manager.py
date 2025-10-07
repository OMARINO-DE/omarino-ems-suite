"""
Solver manager for checking and configuring optimization solvers.
"""
from typing import List, Optional
import structlog

logger = structlog.get_logger()


class SolverManager:
    """Manage optimization solvers."""
    
    def __init__(self):
        self._available_solvers: Optional[List[str]] = None
    
    def get_available_solvers(self) -> List[str]:
        """
        Check which solvers are available.
        
        Returns:
            List of available solver names
        """
        if self._available_solvers is not None:
            return self._available_solvers
        
        available = []
        
        # Check HiGHS (via Pyomo)
        try:
            from pyomo.environ import SolverFactory
            solver = SolverFactory('highs')
            if solver.available():
                available.append("highs")
                logger.info("solver_available", solver="highs")
            else:
                logger.warning("solver_not_available", solver="highs", reason="solver_factory_unavailable")
        except Exception as e:
            logger.warning("solver_not_available", solver="highs", error=str(e))
        
        # Check CBC (via Pyomo)
        try:
            from pyomo.environ import SolverFactory
            solver = SolverFactory('cbc')
            if solver.available():
                available.append("cbc")
                logger.info("solver_available", solver="cbc")
        except Exception as e:
            logger.warning("solver_not_available", solver="cbc", error=str(e))
        
        # Check GLPK
        try:
            from pyomo.environ import SolverFactory
            solver = SolverFactory('glpk')
            if solver.available():
                available.append("glpk")
                logger.info("solver_available", solver="glpk")
        except Exception as e:
            logger.warning("solver_not_available", solver="glpk", error=str(e))
        
        # Check Gurobi (commercial, requires license)
        try:
            from pyomo.environ import SolverFactory
            solver = SolverFactory('gurobi')
            if solver.available():
                available.append("gurobi")
                logger.info("solver_available", solver="gurobi")
        except Exception:
            pass  # Don't warn about commercial solvers
        
        # Check CPLEX (commercial, requires license)
        try:
            from pyomo.environ import SolverFactory
            solver = SolverFactory('cplex')
            if solver.available():
                available.append("cplex")
                logger.info("solver_available", solver="cplex")
        except Exception:
            pass
        
        self._available_solvers = available
        return available
    
    def is_solver_available(self, solver_name: str) -> bool:
        """Check if a specific solver is available."""
        return solver_name in self.get_available_solvers()
    
    def get_solver_factory(self, solver_name: str):
        """Get Pyomo solver factory for specified solver."""
        from pyomo.environ import SolverFactory
        
        if not self.is_solver_available(solver_name):
            raise ValueError(f"Solver '{solver_name}' is not available")
        
        return SolverFactory(solver_name)
