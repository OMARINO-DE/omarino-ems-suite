"""
Ray cluster lifecycle management service.

Manages Ray cluster operations including:
- Cluster initialization and configuration
- Worker scaling (add/remove workers)
- Health monitoring and status tracking
- Fault tolerance and recovery
- Resource allocation and optimization
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

try:
    import ray
    from ray.cluster_utils import Cluster
    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False
    class Cluster:
        pass

logger = logging.getLogger(__name__)


class ClusterStatus(str, Enum):
    """Ray cluster status."""
    NOT_INITIALIZED = "not_initialized"
    INITIALIZING = "initializing"
    RUNNING = "running"
    SCALING = "scaling"
    DEGRADED = "degraded"
    FAILED = "failed"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"


class RayCluster:
    """
    Ray cluster lifecycle manager.
    
    Provides cluster management including initialization, scaling,
    monitoring, and cleanup.
    """
    
    def __init__(self, name: str = "training-cluster"):
        """
        Initialize RayCluster manager.
        
        Args:
            name: Cluster name identifier
        """
        if not RAY_AVAILABLE:
            raise ImportError(
                "Ray is not installed. Install with: pip install ray[default]"
            )
        
        self.name = name
        self.status = ClusterStatus.NOT_INITIALIZED
        self._cluster: Optional[Cluster] = None
        self._config: Optional[Dict[str, Any]] = None
        self._start_time: Optional[datetime] = None
        self._health_check_task: Optional[asyncio.Task] = None
        
    async def start_cluster(
        self,
        num_cpus: int = 4,
        num_gpus: int = 0,
        memory_gb: int = 16,
        object_store_memory_gb: int = 8,
        dashboard_host: str = "127.0.0.1",
        dashboard_port: int = 8265,
    ) -> Dict[str, Any]:
        """
        Start Ray cluster.
        
        Args:
            num_cpus: Total CPUs for cluster
            num_gpus: Total GPUs for cluster
            memory_gb: Total memory in GB
            object_store_memory_gb: Object store memory in GB
            dashboard_host: Dashboard host
            dashboard_port: Dashboard port
            
        Returns:
            Cluster information dictionary
        """
        if self.status != ClusterStatus.NOT_INITIALIZED and self.status != ClusterStatus.SHUTDOWN:
            logger.warning(f"Cluster already in state: {self.status}")
            return self.get_cluster_info()
        
        self.status = ClusterStatus.INITIALIZING
        logger.info(f"Starting Ray cluster '{self.name}'")
        
        try:
            # Store configuration
            self._config = {
                "num_cpus": num_cpus,
                "num_gpus": num_gpus,
                "memory_gb": memory_gb,
                "object_store_memory_gb": object_store_memory_gb,
                "dashboard_host": dashboard_host,
                "dashboard_port": dashboard_port,
            }
            
            # Initialize Ray
            ray.init(
                num_cpus=num_cpus,
                num_gpus=num_gpus if num_gpus > 0 else None,
                _memory=memory_gb * 1024 * 1024 * 1024,
                object_store_memory=object_store_memory_gb * 1024 * 1024 * 1024,
                dashboard_host=dashboard_host,
                dashboard_port=dashboard_port,
                ignore_reinit_error=True,
                logging_level=logging.INFO,
            )
            
            self._start_time = datetime.utcnow()
            self.status = ClusterStatus.RUNNING
            
            # Start health monitoring
            self._health_check_task = asyncio.create_task(
                self._health_check_loop()
            )
            
            logger.info(f"Ray cluster '{self.name}' started successfully")
            
            return self.get_cluster_info()
            
        except Exception as e:
            self.status = ClusterStatus.FAILED
            logger.error(f"Failed to start cluster: {e}")
            raise
    
    async def shutdown_cluster(self, force: bool = False) -> None:
        """
        Shutdown Ray cluster.
        
        Args:
            force: Force shutdown even if tasks are running
        """
        if self.status == ClusterStatus.SHUTDOWN:
            logger.info("Cluster already shut down")
            return
        
        self.status = ClusterStatus.SHUTTING_DOWN
        logger.info(f"Shutting down cluster '{self.name}'")
        
        try:
            # Stop health monitoring
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Check for running tasks
            if not force:
                running_tasks = self._get_running_tasks()
                if running_tasks > 0:
                    logger.warning(
                        f"Cluster has {running_tasks} running tasks. "
                        f"Use force=True to shutdown anyway."
                    )
                    self.status = ClusterStatus.RUNNING
                    return
            
            # Shutdown Ray
            ray.shutdown()
            
            self.status = ClusterStatus.SHUTDOWN
            self._cluster = None
            self._start_time = None
            
            logger.info(f"Cluster '{self.name}' shut down successfully")
            
        except Exception as e:
            logger.error(f"Error shutting down cluster: {e}")
            self.status = ClusterStatus.FAILED
            raise
    
    async def scale_workers(
        self,
        target_cpus: int,
        target_gpus: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Scale cluster resources.
        
        Note: In local mode, this is simulated. In production, this would
        integrate with autoscaling systems (K8s, AWS, etc.).
        
        Args:
            target_cpus: Target number of CPUs
            target_gpus: Target number of GPUs (optional)
            
        Returns:
            Updated cluster information
        """
        if self.status != ClusterStatus.RUNNING:
            raise RuntimeError(f"Cannot scale cluster in state: {self.status}")
        
        old_status = self.status
        self.status = ClusterStatus.SCALING
        
        logger.info(
            f"Scaling cluster '{self.name}' to {target_cpus} CPUs"
            + (f", {target_gpus} GPUs" if target_gpus is not None else "")
        )
        
        try:
            # Get current resources
            current_resources = ray.cluster_resources()
            current_cpus = int(current_resources.get("CPU", 0))
            
            if target_cpus == current_cpus:
                logger.info("Cluster already at target size")
                self.status = old_status
                return self.get_cluster_info()
            
            # In local mode, we can't dynamically add resources
            # In production, this would call cloud provider APIs
            logger.warning(
                "Dynamic scaling not supported in local mode. "
                "Restart cluster with new configuration to change resources."
            )
            
            self.status = old_status
            
            return self.get_cluster_info()
            
        except Exception as e:
            logger.error(f"Error scaling cluster: {e}")
            self.status = ClusterStatus.DEGRADED
            raise
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """
        Get cluster information and status.
        
        Returns:
            Dictionary with cluster details
        """
        if self.status == ClusterStatus.NOT_INITIALIZED or self.status == ClusterStatus.SHUTDOWN:
            return {
                "name": self.name,
                "status": self.status.value,
                "message": "Cluster not running",
            }
        
        try:
            # Get resource information
            total_resources = ray.cluster_resources()
            available_resources = ray.available_resources()
            
            # Calculate utilization
            cpu_total = total_resources.get("CPU", 0)
            cpu_available = available_resources.get("CPU", 0)
            cpu_used = cpu_total - cpu_available
            cpu_utilization = (cpu_used / cpu_total * 100) if cpu_total > 0 else 0
            
            memory_total = total_resources.get("memory", 0)
            memory_available = available_resources.get("memory", 0)
            memory_used = memory_total - memory_available
            memory_utilization = (memory_used / memory_total * 100) if memory_total > 0 else 0
            
            # Get nodes
            nodes = ray.nodes()
            alive_nodes = [n for n in nodes if n["Alive"]]
            
            # Calculate uptime
            uptime_seconds = None
            if self._start_time:
                uptime_seconds = (datetime.utcnow() - self._start_time).total_seconds()
            
            return {
                "name": self.name,
                "status": self.status.value,
                "config": self._config,
                "resources": {
                    "total": {
                        "cpu": cpu_total,
                        "memory_gb": memory_total / (1024**3),
                        "gpu": total_resources.get("GPU", 0),
                    },
                    "available": {
                        "cpu": cpu_available,
                        "memory_gb": memory_available / (1024**3),
                        "gpu": available_resources.get("GPU", 0),
                    },
                    "utilization": {
                        "cpu_percent": round(cpu_utilization, 2),
                        "memory_percent": round(memory_utilization, 2),
                    },
                },
                "nodes": {
                    "total": len(nodes),
                    "alive": len(alive_nodes),
                    "dead": len(nodes) - len(alive_nodes),
                },
                "uptime_seconds": uptime_seconds,
                "dashboard_url": self._get_dashboard_url(),
            }
            
        except Exception as e:
            logger.error(f"Error getting cluster info: {e}")
            return {
                "name": self.name,
                "status": ClusterStatus.FAILED.value,
                "error": str(e),
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on cluster.
        
        Returns:
            Health check result
        """
        if self.status not in [ClusterStatus.RUNNING, ClusterStatus.DEGRADED]:
            return {
                "healthy": False,
                "status": self.status.value,
                "message": "Cluster not in operational state",
            }
        
        try:
            # Check if Ray is responsive
            @ray.remote
            def health_check_task():
                return True
            
            # Run health check task with timeout
            try:
                result = await asyncio.wait_for(
                    asyncio.wrap_future(health_check_task.remote()),
                    timeout=5.0,
                )
            except asyncio.TimeoutError:
                logger.error("Health check task timed out")
                self.status = ClusterStatus.DEGRADED
                return {
                    "healthy": False,
                    "status": self.status.value,
                    "message": "Cluster not responding",
                }
            
            # Check node health
            nodes = ray.nodes()
            dead_nodes = [n for n in nodes if not n["Alive"]]
            
            if dead_nodes:
                logger.warning(f"Found {len(dead_nodes)} dead nodes")
                self.status = ClusterStatus.DEGRADED
                return {
                    "healthy": False,
                    "status": self.status.value,
                    "message": f"{len(dead_nodes)} dead nodes",
                    "dead_nodes": dead_nodes,
                }
            
            # Check resource availability
            available = ray.available_resources()
            if available.get("CPU", 0) < 0.1:
                logger.warning("Low CPU availability")
                return {
                    "healthy": True,
                    "status": self.status.value,
                    "warning": "Low CPU availability",
                }
            
            # All checks passed
            if self.status == ClusterStatus.DEGRADED:
                self.status = ClusterStatus.RUNNING
            
            return {
                "healthy": True,
                "status": self.status.value,
                "message": "Cluster healthy",
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.status = ClusterStatus.DEGRADED
            return {
                "healthy": False,
                "status": self.status.value,
                "error": str(e),
            }
    
    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                await self.health_check()
            except asyncio.CancelledError:
                logger.info("Health check loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    def _get_running_tasks(self) -> int:
        """
        Get number of currently running tasks.
        
        Returns:
            Number of running tasks
        """
        try:
            # Get task information from Ray
            # Note: This is a simplified check
            resources = ray.available_resources()
            total_resources = ray.cluster_resources()
            
            cpu_used = total_resources.get("CPU", 0) - resources.get("CPU", 0)
            
            # Estimate tasks based on CPU usage
            # (Assuming each task uses ~1 CPU)
            return int(cpu_used)
            
        except Exception as e:
            logger.error(f"Error getting running tasks: {e}")
            return 0
    
    def _get_dashboard_url(self) -> Optional[str]:
        """
        Get Ray dashboard URL.
        
        Returns:
            Dashboard URL or None
        """
        if not self._config:
            return None
        
        host = self._config.get("dashboard_host", "127.0.0.1")
        port = self._config.get("dashboard_port", 8265)
        
        return f"http://{host}:{port}"
    
    def handle_node_failure(self, node_id: str) -> Dict[str, Any]:
        """
        Handle node failure.
        
        Args:
            node_id: Failed node ID
            
        Returns:
            Recovery action result
        """
        logger.error(f"Node failure detected: {node_id}")
        
        # Mark cluster as degraded
        if self.status == ClusterStatus.RUNNING:
            self.status = ClusterStatus.DEGRADED
        
        # In production, this would:
        # 1. Mark failed tasks for retry
        # 2. Request replacement node from autoscaler
        # 3. Redistribute work to healthy nodes
        
        return {
            "action": "failure_handled",
            "node_id": node_id,
            "status": self.status.value,
            "message": "Failure handling not fully implemented in local mode",
        }
    
    async def restart_cluster(self) -> Dict[str, Any]:
        """
        Restart the cluster.
        
        Returns:
            New cluster information
        """
        logger.info(f"Restarting cluster '{self.name}'")
        
        # Shutdown
        await self.shutdown_cluster(force=True)
        
        # Wait for cleanup
        await asyncio.sleep(2)
        
        # Start with same configuration
        if self._config:
            return await self.start_cluster(**self._config)
        else:
            return await self.start_cluster()
