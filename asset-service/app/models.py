"""
Pydantic models for Asset Management Service.
"""
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, field_validator


# =====================================================
# ENUMS
# =====================================================

class AssetType(str, Enum):
    """Asset type enumeration."""
    BATTERY = "battery"
    GENERATOR = "generator"
    GRID_CONNECTION = "grid_connection"
    SOLAR_PV = "solar_pv"
    WIND_TURBINE = "wind_turbine"
    LOAD = "load"
    EV_CHARGER = "ev_charger"


class AssetStatus(str, Enum):
    """Asset status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class OperationalStatus(str, Enum):
    """Operational status enumeration."""
    ONLINE = "online"
    OFFLINE = "offline"
    STANDBY = "standby"
    FAULT = "fault"
    MAINTENANCE = "maintenance"


class AlarmLevel(str, Enum):
    """Alarm level enumeration."""
    NONE = "none"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class BatteryChemistry(str, Enum):
    """Battery chemistry types."""
    LITHIUM_ION = "lithium_ion"
    LITHIUM_IRON_PHOSPHATE = "lithium_iron_phosphate"
    LEAD_ACID = "lead_acid"
    NICKEL_METAL_HYDRIDE = "nickel_metal_hydride"
    SODIUM_SULFUR = "sodium_sulfur"
    FLOW_BATTERY = "flow_battery"
    OTHER = "other"


class GeneratorType(str, Enum):
    """Generator type enumeration."""
    DIESEL = "diesel"
    NATURAL_GAS = "natural_gas"
    BIOGAS = "biogas"
    DUAL_FUEL = "dual_fuel"
    GASOLINE = "gasoline"
    PROPANE = "propane"
    OTHER = "other"


class SolarPanelType(str, Enum):
    """Solar panel type enumeration."""
    MONOCRYSTALLINE = "monocrystalline"
    POLYCRYSTALLINE = "polycrystalline"
    THIN_FILM = "thin_film"
    BIFACIAL = "bifacial"
    OTHER = "other"


class TrackingType(str, Enum):
    """Solar tracking type."""
    FIXED = "fixed"
    SINGLE_AXIS = "single_axis"
    DUAL_AXIS = "dual_axis"
    NONE = "none"


# =====================================================
# BASE MODELS
# =====================================================

class AssetBase(BaseModel):
    """Base asset model."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    site_id: Optional[UUID] = None
    manufacturer: Optional[str] = Field(None, max_length=255)
    model: Optional[str] = Field(None, max_length=255)
    serial_number: Optional[str] = Field(None, max_length=255)
    installation_date: Optional[date] = None
    metadata: Optional[Dict[str, Any]] = None


class AssetCreate(AssetBase):
    """Model for creating an asset."""
    asset_type: AssetType


class AssetUpdate(BaseModel):
    """Model for updating an asset."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    location: Optional[str] = None
    status: Optional[AssetStatus] = None
    metadata: Optional[Dict[str, Any]] = None


class AssetSummary(AssetBase):
    """Summary model for listing assets."""
    asset_id: UUID
    asset_type: AssetType
    status: AssetStatus
    site_name: Optional[str] = None
    capacity_rating: Optional[float] = None
    online: Optional[bool] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class Asset(AssetSummary):
    """Full asset model."""
    commissioning_date: Optional[date] = None
    warranty_expiry_date: Optional[date] = None
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


# =====================================================
# BATTERY MODELS
# =====================================================

class BatterySpecBase(BaseModel):
    """Base battery specification model."""
    capacity_kwh: float = Field(..., gt=0)
    usable_capacity_kwh: Optional[float] = Field(None, gt=0)
    max_charge_kw: float = Field(..., gt=0)
    max_discharge_kw: float = Field(..., gt=0)
    round_trip_efficiency: float = Field(0.95, gt=0, le=1)
    min_soc: float = Field(0.1, ge=0, le=1)
    max_soc: float = Field(0.9, ge=0, le=1)
    initial_soc: float = Field(0.5, ge=0, le=1)
    chemistry: Optional[BatteryChemistry] = None
    degradation_cost_per_kwh: float = Field(0.01, ge=0)
    current_health_percentage: float = Field(100.0, ge=0, le=100)
    
    @field_validator('usable_capacity_kwh')
    @classmethod
    def validate_usable_capacity(cls, v, info):
        """Ensure usable capacity doesn't exceed total capacity."""
        capacity = info.data.get('capacity_kwh')
        if v is not None and capacity is not None and v > capacity:
            raise ValueError('usable_capacity_kwh cannot exceed capacity_kwh')
        return v
    
    @field_validator('max_soc')
    @classmethod
    def validate_soc_limits(cls, v, info):
        """Ensure max_soc > min_soc."""
        min_soc = info.data.get('min_soc')
        if min_soc is not None and v <= min_soc:
            raise ValueError('max_soc must be greater than min_soc')
        return v


class BatterySpecCreate(BatterySpecBase):
    """Model for creating battery specifications."""
    pass


class BatterySpecUpdate(BaseModel):
    """Model for updating battery specifications."""
    capacity_kwh: Optional[float] = Field(None, gt=0)
    max_charge_kw: Optional[float] = Field(None, gt=0)
    max_discharge_kw: Optional[float] = Field(None, gt=0)
    current_health_percentage: Optional[float] = Field(None, ge=0, le=100)


class BatterySpec(BatterySpecBase):
    """Full battery specification model."""
    asset_id: UUID
    continuous_charge_kw: Optional[float] = None
    continuous_discharge_kw: Optional[float] = None
    charge_efficiency: Optional[float] = None
    discharge_efficiency: Optional[float] = None
    target_soc: Optional[float] = None
    cycle_life: Optional[int] = None
    current_cycle_count: int = 0
    ramp_up_rate_kw_per_sec: Optional[float] = None
    ramp_down_rate_kw_per_sec: Optional[float] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BatteryAssetCreate(AssetBase):
    """Model for creating a battery asset."""
    battery: BatterySpecCreate


class BatteryAsset(Asset):
    """Full battery asset with specifications."""
    battery: BatterySpec


# =====================================================
# GENERATOR MODELS
# =====================================================

class GeneratorSpecBase(BaseModel):
    """Base generator specification model."""
    rated_capacity_kw: float = Field(..., gt=0)
    max_output_kw: float = Field(..., gt=0)
    min_output_kw: float = Field(0, ge=0)
    generator_type: Optional[GeneratorType] = None
    fuel_cost_per_kwh: float = Field(..., ge=0)
    startup_cost: float = Field(0, ge=0)
    shutdown_cost: float = Field(0, ge=0)
    min_uptime_hours: int = Field(1, ge=0)
    min_downtime_hours: int = Field(1, ge=0)
    co2_emissions_kg_per_kwh: float = Field(0.5, ge=0)


class GeneratorSpecCreate(GeneratorSpecBase):
    """Model for creating generator specifications."""
    pass


class GeneratorSpec(GeneratorSpecBase):
    """Full generator specification model."""
    asset_id: UUID
    fuel_type: Optional[str] = None
    efficiency_at_rated_load: Optional[float] = None
    ramp_up_rate_kw_per_min: Optional[float] = None
    ramp_down_rate_kw_per_min: Optional[float] = None
    operating_hours: int = 0
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GeneratorAssetCreate(AssetBase):
    """Model for creating a generator asset."""
    generator: GeneratorSpecCreate


class GeneratorAsset(Asset):
    """Full generator asset with specifications."""
    generator: GeneratorSpec


# =====================================================
# GRID CONNECTION MODELS
# =====================================================

class GridConnectionSpecBase(BaseModel):
    """Base grid connection specification model."""
    max_import_kw: float = Field(..., ge=0)
    max_export_kw: float = Field(..., ge=0)
    import_enabled: bool = True
    export_enabled: bool = True


class GridConnectionSpecCreate(GridConnectionSpecBase):
    """Model for creating grid connection specifications."""
    pass


class GridConnectionSpec(GridConnectionSpecBase):
    """Full grid connection specification model."""
    asset_id: UUID
    connection_type: Optional[str] = None
    voltage_level_kv: Optional[float] = None
    utility_company: Optional[str] = None
    meter_id: Optional[str] = None
    tariff_type: Optional[str] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GridConnectionAssetCreate(AssetBase):
    """Model for creating a grid connection asset."""
    grid: GridConnectionSpecCreate


class GridConnectionAsset(Asset):
    """Full grid connection asset with specifications."""
    grid: GridConnectionSpec


# =====================================================
# SOLAR PV MODELS
# =====================================================

class SolarPVSpecBase(BaseModel):
    """Base solar PV specification model."""
    rated_capacity_kw: float = Field(..., gt=0)
    panel_type: Optional[SolarPanelType] = None
    tilt_angle_degrees: Optional[float] = Field(None, ge=0, le=90)
    azimuth_degrees: Optional[float] = Field(None, ge=0, lt=360)
    tracking_type: Optional[TrackingType] = None
    inverter_efficiency: Optional[float] = Field(None, gt=0, le=1)


class SolarPVSpecCreate(SolarPVSpecBase):
    """Model for creating solar PV specifications."""
    pass


class SolarPVSpec(SolarPVSpecBase):
    """Full solar PV specification model."""
    asset_id: UUID
    dc_capacity_kw: Optional[float] = None
    number_of_panels: Optional[int] = None
    panel_efficiency: Optional[float] = None
    performance_ratio: Optional[float] = None
    degradation_rate_per_year: float = 0.005
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SolarPVAssetCreate(AssetBase):
    """Model for creating a solar PV asset."""
    solar: SolarPVSpecCreate


class SolarPVAsset(Asset):
    """Full solar PV asset with specifications."""
    solar: SolarPVSpec


# =====================================================
# ASSET STATUS MODELS
# =====================================================

class AssetStatusBase(BaseModel):
    """Base asset status model."""
    online: bool = False
    operational_status: OperationalStatus = OperationalStatus.OFFLINE
    current_power_kw: Optional[float] = None
    current_soc: Optional[float] = Field(None, ge=0, le=1)
    fault_code: Optional[str] = None
    alarm_level: AlarmLevel = AlarmLevel.NONE
    alarm_message: Optional[str] = None


class AssetStatusUpdate(AssetStatusBase):
    """Model for updating asset status."""
    pass


class AssetStatusResponse(AssetStatusBase):
    """Asset status response model."""
    asset_id: UUID
    last_communication: Optional[datetime] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True


# =====================================================
# RESPONSE MODELS
# =====================================================

class AssetListResponse(BaseModel):
    """Response model for asset list."""
    assets: List[AssetSummary]
    total: int
    limit: int
    offset: int


class BatteryListResponse(BaseModel):
    """Response model for battery list."""
    batteries: List[BatteryAsset]
    total: int
    limit: int
    offset: int


class GeneratorListResponse(BaseModel):
    """Response model for generator list."""
    generators: List[GeneratorAsset]
    total: int
    limit: int
    offset: int


class GridConnectionListResponse(BaseModel):
    """Response model for grid connection list."""
    grid_connections: List[GridConnectionAsset]
    total: int
    limit: int
    offset: int


class SolarPVListResponse(BaseModel):
    """Response model for solar PV list."""
    solar_systems: List[SolarPVAsset]
    total: int
    limit: int
    offset: int


# =====================================================
# ERROR MODELS
# =====================================================

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    asset_id: Optional[str] = None


class ValidationErrorDetail(BaseModel):
    """Validation error detail."""
    field: str
    message: str


class ValidationErrorResponse(BaseModel):
    """Validation error response."""
    error: str
    validation_errors: List[ValidationErrorDetail]
