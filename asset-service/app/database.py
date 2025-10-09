"""
Database client for Asset Management Service using asyncpg.
"""
import asyncpg
import structlog
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from uuid import UUID
import json

from app.config import get_settings
from app.models import (
    AssetType, AssetStatus, AssetCreate, AssetUpdate,
    BatterySpecCreate, BatterySpecUpdate,
    GeneratorSpecCreate, GridConnectionSpecCreate, SolarPVSpecCreate,
    AssetStatusUpdate
)

logger = structlog.get_logger()


class AssetDatabase:
    """Database client for asset management operations."""
    
    def __init__(self):
        """Initialize database client."""
        self.pool: Optional[asyncpg.Pool] = None
        settings = get_settings()
        self.database_url = settings.database_url
        self.min_size = settings.db_min_pool_size
        self.max_size = settings.db_max_pool_size
        self.command_timeout = settings.db_command_timeout
    
    async def connect(self):
        """Create database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.min_size,
                max_size=self.max_size,
                command_timeout=self.command_timeout
            )
            logger.info("asset_database_connected")
        except Exception as e:
            logger.error("asset_database_connection_failed", error=str(e))
            raise
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("asset_database_closed")
    
    # =====================================================
    # ASSET OPERATIONS
    # =====================================================
    
    async def create_asset(
        self,
        asset_id: UUID,
        asset_data: AssetCreate,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new asset."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO assets (
                        asset_id, asset_type, name, description, location, site_id,
                        manufacturer, model, serial_number, installation_date,
                        status, metadata, created_by, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    RETURNING *
                    """,
                    asset_id,
                    asset_data.asset_type.value,
                    asset_data.name,
                    asset_data.description,
                    asset_data.location,
                    asset_data.site_id,
                    asset_data.manufacturer,
                    asset_data.model,
                    asset_data.serial_number,
                    asset_data.installation_date,
                    AssetStatus.ACTIVE.value,
                    json.dumps(asset_data.metadata) if asset_data.metadata else None,
                    created_by,
                    datetime.utcnow(),
                    datetime.utcnow()
                )
            
            logger.info("asset_created", asset_id=str(asset_id), asset_type=asset_data.asset_type.value)
            return dict(row)
        
        except Exception as e:
            logger.error("asset_creation_failed", error=str(e), asset_id=str(asset_id))
            raise
    
    async def get_asset(self, asset_id: UUID) -> Optional[Dict[str, Any]]:
        """Get asset by ID."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT a.*, s.site_name
                    FROM assets a
                    LEFT JOIN sites s ON a.site_id = s.site_id
                    WHERE a.asset_id = $1
                    """,
                    asset_id
                )
            
            if row:
                return dict(row)
            return None
        
        except Exception as e:
            logger.error("get_asset_failed", error=str(e), asset_id=str(asset_id))
            raise
    
    async def list_assets(
        self,
        asset_type: Optional[AssetType] = None,
        status: Optional[AssetStatus] = None,
        site_id: Optional[UUID] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Dict[str, Any]], int]:
        """List assets with filtering and pagination."""
        try:
            # Build query conditions
            conditions = []
            params = []
            param_num = 1
            
            if asset_type:
                conditions.append(f"a.asset_type = ${param_num}")
                params.append(asset_type.value)
                param_num += 1
            
            if status:
                conditions.append(f"a.status = ${param_num}")
                params.append(status.value)
                param_num += 1
            
            if site_id:
                conditions.append(f"a.site_id = ${param_num}")
                params.append(site_id)
                param_num += 1
            
            if search:
                conditions.append(f"(a.name ILIKE ${param_num} OR a.description ILIKE ${param_num})")
                params.append(f"%{search}%")
                param_num += 1
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            async with self.pool.acquire() as conn:
                # Get total count
                count_query = f"""
                    SELECT COUNT(*) FROM assets a {where_clause}
                """
                total = await conn.fetchval(count_query, *params)
                
                # Get assets
                params.extend([limit, offset])
                list_query = f"""
                    SELECT 
                        a.*,
                        s.site_name,
                        ast.online,
                        ast.operational_status
                    FROM assets a
                    LEFT JOIN sites s ON a.site_id = s.site_id
                    LEFT JOIN asset_status ast ON a.asset_id = ast.asset_id
                    {where_clause}
                    ORDER BY a.created_at DESC
                    LIMIT ${param_num} OFFSET ${param_num + 1}
                """
                rows = await conn.fetch(list_query, *params)
            
            assets = [dict(row) for row in rows]
            return assets, total
        
        except Exception as e:
            logger.error("list_assets_failed", error=str(e))
            raise
    
    async def update_asset(
        self,
        asset_id: UUID,
        asset_data: AssetUpdate,
        updated_by: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update asset information."""
        try:
            # Build update fields
            update_fields = []
            params = []
            param_num = 1
            
            if asset_data.name is not None:
                update_fields.append(f"name = ${param_num}")
                params.append(asset_data.name)
                param_num += 1
            
            if asset_data.description is not None:
                update_fields.append(f"description = ${param_num}")
                params.append(asset_data.description)
                param_num += 1
            
            if asset_data.location is not None:
                update_fields.append(f"location = ${param_num}")
                params.append(asset_data.location)
                param_num += 1
            
            if asset_data.status is not None:
                update_fields.append(f"status = ${param_num}")
                params.append(asset_data.status.value)
                param_num += 1
            
            if asset_data.metadata is not None:
                update_fields.append(f"metadata = ${param_num}")
                params.append(json.dumps(asset_data.metadata))
                param_num += 1
            
            if not update_fields:
                return await self.get_asset(asset_id)
            
            update_fields.append(f"updated_at = ${param_num}")
            params.append(datetime.utcnow())
            param_num += 1
            
            if updated_by:
                update_fields.append(f"updated_by = ${param_num}")
                params.append(updated_by)
                param_num += 1
            
            params.append(asset_id)
            
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"""
                    UPDATE assets
                    SET {', '.join(update_fields)}
                    WHERE asset_id = ${param_num}
                    RETURNING *
                    """,
                    *params
                )
            
            if row:
                logger.info("asset_updated", asset_id=str(asset_id))
                return dict(row)
            return None
        
        except Exception as e:
            logger.error("update_asset_failed", error=str(e), asset_id=str(asset_id))
            raise
    
    async def delete_asset(self, asset_id: UUID) -> bool:
        """Delete asset (cascade to specifications)."""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM assets WHERE asset_id = $1",
                    asset_id
                )
            
            deleted = result.split()[-1] == "1"
            if deleted:
                logger.info("asset_deleted", asset_id=str(asset_id))
            return deleted
        
        except Exception as e:
            logger.error("delete_asset_failed", error=str(e), asset_id=str(asset_id))
            raise
    
    # =====================================================
    # BATTERY OPERATIONS
    # =====================================================
    
    async def create_battery_spec(
        self,
        asset_id: UUID,
        spec: BatterySpecCreate
    ) -> Dict[str, Any]:
        """Create battery specifications."""
        try:
            # Calculate rated_power_kw as minimum of max_charge and max_discharge
            rated_power_kw = min(spec.max_charge_kw, spec.max_discharge_kw)
            
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO battery_specs (
                        asset_id, capacity_kwh, usable_capacity_kwh, rated_power_kw,
                        max_charge_kw, max_discharge_kw,
                        round_trip_efficiency, min_soc, max_soc, initial_soc,
                        chemistry, degradation_cost_per_kwh, current_health_percentage,
                        updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    RETURNING *
                    """,
                    asset_id,
                    spec.capacity_kwh,
                    spec.usable_capacity_kwh,
                    rated_power_kw,
                    spec.max_charge_kw,
                    spec.max_discharge_kw,
                    spec.round_trip_efficiency,
                    spec.min_soc,
                    spec.max_soc,
                    spec.initial_soc,
                    spec.chemistry.value if spec.chemistry else None,
                    spec.degradation_cost_per_kwh,
                    spec.current_health_percentage,
                    datetime.utcnow()
                )
            
            logger.info("battery_spec_created", asset_id=str(asset_id))
            return dict(row)
        
        except Exception as e:
            logger.error("battery_spec_creation_failed", error=str(e), asset_id=str(asset_id))
            raise
    
    async def get_battery_spec(self, asset_id: UUID) -> Optional[Dict[str, Any]]:
        """Get battery specifications."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM battery_specs WHERE asset_id = $1",
                    asset_id
                )
            
            if row:
                return dict(row)
            return None
        
        except Exception as e:
            logger.error("get_battery_spec_failed", error=str(e), asset_id=str(asset_id))
            raise
    
    async def get_battery(self, asset_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a specific battery asset with all related information."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT 
                        a.*,
                        s.site_name,
                        b.*,
                        ast.online,
                        ast.operational_status
                    FROM assets a
                    INNER JOIN battery_specs b ON a.asset_id = b.asset_id
                    LEFT JOIN sites s ON a.site_id = s.site_id
                    LEFT JOIN asset_status ast ON a.asset_id = ast.asset_id
                    WHERE a.asset_id = $1 AND a.asset_type = 'battery'
                    """,
                    asset_id
                )
            
            if row:
                return dict(row)
            return None
        
        except Exception as e:
            logger.error("get_battery_failed", error=str(e), asset_id=str(asset_id))
            raise
    
    async def list_batteries(
        self,
        status_filter: Optional[str] = None,
        site_id: Optional[UUID] = None,
        chemistry: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Dict[str, Any]], int]:
        """List battery assets with specifications and optional filters."""
        try:
            # Build dynamic query with filters
            conditions = ["a.asset_type = 'battery'"]
            params = []
            param_idx = 1
            
            if status_filter:
                conditions.append(f"a.status = ${param_idx}")
                params.append(status_filter)
                param_idx += 1
            
            if site_id:
                conditions.append(f"a.site_id = ${param_idx}")
                params.append(site_id)
                param_idx += 1
            
            if chemistry:
                conditions.append(f"b.chemistry = ${param_idx}")
                params.append(chemistry)
                param_idx += 1
            
            if search:
                conditions.append(f"(a.name ILIKE ${param_idx} OR a.description ILIKE ${param_idx})")
                params.append(f"%{search}%")
                param_idx += 1
            
            where_clause = " AND ".join(conditions)
            
            async with self.pool.acquire() as conn:
                # Get total count with filters
                count_query = f"""
                    SELECT COUNT(*)
                    FROM assets a
                    INNER JOIN battery_specs b ON a.asset_id = b.asset_id
                    WHERE {where_clause}
                """
                total = await conn.fetchval(count_query, *params)
                
                # Get batteries with filters
                params.extend([limit, offset])
                query = f"""
                    SELECT 
                        a.asset_id, a.asset_type, a.name, a.description, a.location,
                        a.site_id, a.manufacturer, a.model, a.serial_number,
                        a.installation_date, a.status, a.metadata,
                        a.created_at, a.updated_at as asset_updated_at,
                        s.site_name,
                        b.capacity_kwh, b.usable_capacity_kwh, b.max_charge_kw,
                        b.max_discharge_kw, b.round_trip_efficiency, b.min_soc,
                        b.max_soc, b.initial_soc, b.chemistry,
                        b.degradation_cost_per_kwh, b.current_health_percentage,
                        b.continuous_charge_kw, b.continuous_discharge_kw,
                        b.charge_efficiency, b.discharge_efficiency,
                        b.target_soc, b.cycle_life, b.current_cycle_count,
                        b.ramp_up_rate_kw_per_sec, b.ramp_down_rate_kw_per_sec,
                        b.updated_at as battery_updated_at,
                        ast.online, ast.operational_status
                    FROM assets a
                    INNER JOIN battery_specs b ON a.asset_id = b.asset_id
                    LEFT JOIN sites s ON a.site_id = s.site_id
                    LEFT JOIN asset_status ast ON a.asset_id = ast.asset_id
                    WHERE {where_clause}
                    ORDER BY a.created_at DESC
                    LIMIT ${param_idx} OFFSET ${param_idx + 1}
                """
                rows = await conn.fetch(query, *params)
            
            # Restructure data to match BatteryAsset model with nested battery field
            batteries = []
            for row in rows:
                row_dict = dict(row)
                battery_data = {
                    "asset_id": str(row_dict["asset_id"]),
                    "asset_type": row_dict["asset_type"],
                    "name": row_dict["name"],
                    "description": row_dict["description"],
                    "location": row_dict["location"],
                    "site_id": str(row_dict["site_id"]) if row_dict.get("site_id") else None,
                    "manufacturer": row_dict["manufacturer"],
                    "model": row_dict["model"],
                    "serial_number": row_dict["serial_number"],
                    "installation_date": row_dict["installation_date"].isoformat() if row_dict.get("installation_date") else None,
                    "status": row_dict["status"],
                    "metadata": row_dict["metadata"],
                    "created_at": row_dict["created_at"].isoformat(),
                    "updated_at": row_dict["asset_updated_at"].isoformat(),
                    "site_name": row_dict.get("site_name"),
                    "online": row_dict.get("online"),
                    "battery": {
                        "asset_id": str(row_dict["asset_id"]),
                        "capacity_kwh": float(row_dict["capacity_kwh"]),
                        "usable_capacity_kwh": float(row_dict["usable_capacity_kwh"]) if row_dict.get("usable_capacity_kwh") else None,
                        "max_charge_kw": float(row_dict["max_charge_kw"]),
                        "max_discharge_kw": float(row_dict["max_discharge_kw"]),
                        "round_trip_efficiency": float(row_dict["round_trip_efficiency"]),
                        "min_soc": float(row_dict["min_soc"]),
                        "max_soc": float(row_dict["max_soc"]),
                        "initial_soc": float(row_dict["initial_soc"]),
                        "chemistry": row_dict.get("chemistry"),
                        "degradation_cost_per_kwh": float(row_dict["degradation_cost_per_kwh"]) if row_dict.get("degradation_cost_per_kwh") else None,
                        "current_health_percentage": float(row_dict["current_health_percentage"]) if row_dict.get("current_health_percentage") else None,
                        "continuous_charge_kw": float(row_dict["continuous_charge_kw"]) if row_dict.get("continuous_charge_kw") else None,
                        "continuous_discharge_kw": float(row_dict["continuous_discharge_kw"]) if row_dict.get("continuous_discharge_kw") else None,
                        "charge_efficiency": float(row_dict["charge_efficiency"]) if row_dict.get("charge_efficiency") else None,
                        "discharge_efficiency": float(row_dict["discharge_efficiency"]) if row_dict.get("discharge_efficiency") else None,
                        "target_soc": float(row_dict["target_soc"]) if row_dict.get("target_soc") else None,
                        "cycle_life": row_dict.get("cycle_life"),
                        "current_cycle_count": row_dict.get("current_cycle_count"),
                        "ramp_up_rate_kw_per_sec": float(row_dict["ramp_up_rate_kw_per_sec"]) if row_dict.get("ramp_up_rate_kw_per_sec") else None,
                        "ramp_down_rate_kw_per_sec": float(row_dict["ramp_down_rate_kw_per_sec"]) if row_dict.get("ramp_down_rate_kw_per_sec") else None,
                        "updated_at": row_dict["battery_updated_at"].isoformat(),
                    }
                }
                batteries.append(battery_data)
            
            return batteries, total
        
        except Exception as e:
            logger.error("list_batteries_failed", error=str(e))
            raise
    
    # =====================================================
    # GENERATOR OPERATIONS
    # =====================================================
    
    async def create_generator_spec(
        self,
        asset_id: UUID,
        spec: GeneratorSpecCreate
    ) -> Dict[str, Any]:
        """Create generator specifications."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO generator_specs (
                        asset_id, rated_capacity_kw, max_output_kw, min_output_kw,
                        generator_type, fuel_cost_per_kwh, startup_cost, shutdown_cost,
                        min_uptime_hours, min_downtime_hours, co2_emissions_kg_per_kwh,
                        updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    RETURNING *
                    """,
                    asset_id,
                    spec.rated_capacity_kw,
                    spec.max_output_kw,
                    spec.min_output_kw,
                    spec.generator_type.value if spec.generator_type else None,
                    spec.fuel_cost_per_kwh,
                    spec.startup_cost,
                    spec.shutdown_cost,
                    spec.min_uptime_hours,
                    spec.min_downtime_hours,
                    spec.co2_emissions_kg_per_kwh,
                    datetime.utcnow()
                )
            
            logger.info("generator_spec_created", asset_id=str(asset_id))
            return dict(row)
        
        except Exception as e:
            logger.error("generator_spec_creation_failed", error=str(e), asset_id=str(asset_id))
            raise
    
    async def get_generator(self, asset_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a specific generator asset with all related information."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT 
                        a.*,
                        s.site_name,
                        g.*,
                        ast.online,
                        ast.operational_status
                    FROM assets a
                    INNER JOIN generator_specs g ON a.asset_id = g.asset_id
                    LEFT JOIN sites s ON a.site_id = s.site_id
                    LEFT JOIN asset_status ast ON a.asset_id = ast.asset_id
                    WHERE a.asset_id = $1 AND a.asset_type = 'generator'
                    """,
                    asset_id
                )
            
            if row:
                return dict(row)
            return None
        
        except Exception as e:
            logger.error("get_generator_failed", error=str(e), asset_id=str(asset_id))
            raise
    
    async def list_generators(
        self,
        status_filter: Optional[str] = None,
        site_id: Optional[UUID] = None,
        generator_type: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Dict[str, Any]], int]:
        """List generator assets with specifications and optional filters."""
        try:
            # Build dynamic query with filters
            conditions = ["a.asset_type = 'generator'"]
            params = []
            param_idx = 1
            
            if status_filter:
                conditions.append(f"a.status = ${param_idx}")
                params.append(status_filter)
                param_idx += 1
            
            if site_id:
                conditions.append(f"a.site_id = ${param_idx}")
                params.append(site_id)
                param_idx += 1
            
            if generator_type:
                conditions.append(f"g.generator_type = ${param_idx}")
                params.append(generator_type)
                param_idx += 1
            
            if search:
                conditions.append(f"(a.name ILIKE ${param_idx} OR a.description ILIKE ${param_idx})")
                params.append(f"%{search}%")
                param_idx += 1
            
            where_clause = " AND ".join(conditions)
            
            async with self.pool.acquire() as conn:
                # Get total count with filters
                count_query = f"""
                    SELECT COUNT(*)
                    FROM assets a
                    INNER JOIN generator_specs g ON a.asset_id = g.asset_id
                    WHERE {where_clause}
                """
                total = await conn.fetchval(count_query, *params)
                
                # Get generators with filters
                params.extend([limit, offset])
                query = f"""
                    SELECT 
                        a.asset_id, a.asset_type, a.name, a.description, a.location,
                        a.site_id, a.manufacturer, a.model, a.serial_number,
                        a.installation_date, a.status, a.metadata,
                        a.created_at, a.updated_at as asset_updated_at,
                        s.site_name,
                        g.rated_capacity_kw, g.max_output_kw, g.min_output_kw,
                        g.generator_type, g.fuel_cost_per_kwh, g.startup_cost,
                        g.shutdown_cost, g.min_uptime_hours, g.min_downtime_hours,
                        g.co2_emissions_kg_per_kwh, g.fuel_type, g.efficiency_at_rated_load,
                        g.ramp_up_rate_kw_per_min, g.ramp_down_rate_kw_per_min, g.operating_hours,
                        g.updated_at as generator_updated_at,
                        ast.online, ast.operational_status
                    FROM assets a
                    INNER JOIN generator_specs g ON a.asset_id = g.asset_id
                    LEFT JOIN sites s ON a.site_id = s.site_id
                    LEFT JOIN asset_status ast ON a.asset_id = ast.asset_id
                    WHERE {where_clause}
                    ORDER BY a.created_at DESC
                    LIMIT ${param_idx} OFFSET ${param_idx + 1}
                """
                rows = await conn.fetch(query, *params)
            
            # Restructure data to match GeneratorAsset model with nested generator field
            generators = []
            for row in rows:
                row_dict = dict(row)
                generator_data = {
                    "asset_id": str(row_dict["asset_id"]),
                    "asset_type": row_dict["asset_type"],
                    "name": row_dict["name"],
                    "description": row_dict["description"],
                    "location": row_dict["location"],
                    "site_id": str(row_dict["site_id"]) if row_dict.get("site_id") else None,
                    "manufacturer": row_dict["manufacturer"],
                    "model": row_dict["model"],
                    "serial_number": row_dict["serial_number"],
                    "installation_date": row_dict["installation_date"].isoformat() if row_dict.get("installation_date") else None,
                    "status": row_dict["status"],
                    "metadata": row_dict["metadata"],
                    "created_at": row_dict["created_at"].isoformat(),
                    "updated_at": row_dict["asset_updated_at"].isoformat(),
                    "site_name": row_dict.get("site_name"),
                    "online": row_dict.get("online"),
                    "generator": {
                        "asset_id": str(row_dict["asset_id"]),
                        "rated_capacity_kw": float(row_dict["rated_capacity_kw"]),
                        "max_output_kw": float(row_dict["max_output_kw"]),
                        "min_output_kw": float(row_dict["min_output_kw"]) if row_dict.get("min_output_kw") else None,
                        "generator_type": row_dict.get("generator_type"),
                        "fuel_cost_per_kwh": float(row_dict["fuel_cost_per_kwh"]),
                        "startup_cost": float(row_dict["startup_cost"]) if row_dict.get("startup_cost") else None,
                        "shutdown_cost": float(row_dict["shutdown_cost"]) if row_dict.get("shutdown_cost") else None,
                        "min_uptime_hours": float(row_dict["min_uptime_hours"]) if row_dict.get("min_uptime_hours") else None,
                        "min_downtime_hours": float(row_dict["min_downtime_hours"]) if row_dict.get("min_downtime_hours") else None,
                        "co2_emissions_kg_per_kwh": float(row_dict["co2_emissions_kg_per_kwh"]) if row_dict.get("co2_emissions_kg_per_kwh") else None,
                        "fuel_type": row_dict.get("fuel_type"),
                        "efficiency_at_rated_load": float(row_dict["efficiency_at_rated_load"]) if row_dict.get("efficiency_at_rated_load") else None,
                        "ramp_up_rate_kw_per_min": float(row_dict["ramp_up_rate_kw_per_min"]) if row_dict.get("ramp_up_rate_kw_per_min") else None,
                        "ramp_down_rate_kw_per_min": float(row_dict["ramp_down_rate_kw_per_min"]) if row_dict.get("ramp_down_rate_kw_per_min") else None,
                        "operating_hours": row_dict.get("operating_hours"),
                        "updated_at": row_dict["generator_updated_at"].isoformat(),
                    }
                }
                generators.append(generator_data)
            
            return generators, total
        
        except Exception as e:
            logger.error("list_generators_failed", error=str(e))
            raise
    
    # =====================================================
    # ASSET STATUS OPERATIONS
    # =====================================================
    
    async def upsert_asset_status(
        self,
        asset_id: UUID,
        status: AssetStatusUpdate
    ) -> Dict[str, Any]:
        """Create or update asset status."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO asset_status (
                        asset_id, online, operational_status, current_power_kw,
                        current_soc, fault_code, alarm_level, alarm_message,
                        last_communication, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (asset_id) DO UPDATE SET
                        online = EXCLUDED.online,
                        operational_status = EXCLUDED.operational_status,
                        current_power_kw = EXCLUDED.current_power_kw,
                        current_soc = EXCLUDED.current_soc,
                        fault_code = EXCLUDED.fault_code,
                        alarm_level = EXCLUDED.alarm_level,
                        alarm_message = EXCLUDED.alarm_message,
                        last_communication = EXCLUDED.last_communication,
                        updated_at = EXCLUDED.updated_at
                    RETURNING *
                    """,
                    asset_id,
                    status.online,
                    status.operational_status.value,
                    status.current_power_kw,
                    status.current_soc,
                    status.fault_code,
                    status.alarm_level.value,
                    status.alarm_message,
                    datetime.utcnow(),
                    datetime.utcnow()
                )
            
            logger.info("asset_status_updated", asset_id=str(asset_id))
            return dict(row)
        
        except Exception as e:
            logger.error("asset_status_update_failed", error=str(e), asset_id=str(asset_id))
            raise
    
    async def get_asset_status(self, asset_id: UUID) -> Optional[Dict[str, Any]]:
        """Get asset status."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM asset_status WHERE asset_id = $1",
                    asset_id
                )
            
            if row:
                return dict(row)
            return None
        
        except Exception as e:
            logger.error("get_asset_status_failed", error=str(e), asset_id=str(asset_id))
            raise
