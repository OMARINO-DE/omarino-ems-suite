-- Asset Management System Database Schema
-- OMARINO EMS Suite
-- Version: 1.0
-- Description: Comprehensive schema for managing energy assets

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- CORE ASSET TABLES
-- =====================================================

-- Main assets table
CREATE TABLE IF NOT EXISTS assets (
    asset_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_type VARCHAR(50) NOT NULL CHECK (asset_type IN (
        'battery', 'generator', 'grid_connection', 
        'solar_pv', 'wind_turbine', 'load', 'ev_charger'
    )),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    location VARCHAR(255),
    site_id UUID,  -- Reference to sites table (for multi-site management)
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN (
        'active', 'inactive', 'maintenance', 'decommissioned'
    )),
    installation_date DATE,
    commissioning_date DATE,
    warranty_expiry_date DATE,
    manufacturer VARCHAR(255),
    model VARCHAR(255),
    serial_number VARCHAR(255),
    metadata JSONB,  -- Flexible field for additional data
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    CONSTRAINT unique_serial_number UNIQUE (serial_number)
);

-- Sites table (for multi-site asset management)
CREATE TABLE IF NOT EXISTS sites (
    site_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_name VARCHAR(255) NOT NULL,
    site_code VARCHAR(50) UNIQUE,
    address TEXT,
    city VARCHAR(100),
    state_province VARCHAR(100),
    country VARCHAR(100),
    postal_code VARCHAR(20),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    timezone VARCHAR(50),
    site_type VARCHAR(50) CHECK (site_type IN (
        'commercial', 'industrial', 'residential', 'utility'
    )),
    total_capacity_kw DOUBLE PRECISION,
    status VARCHAR(20) DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- =====================================================
-- BATTERY ENERGY STORAGE SYSTEMS (BESS)
-- =====================================================

CREATE TABLE IF NOT EXISTS battery_specs (
    asset_id UUID PRIMARY KEY REFERENCES assets(asset_id) ON DELETE CASCADE,
    
    -- Capacity specifications
    capacity_kwh DOUBLE PRECISION NOT NULL CHECK (capacity_kwh > 0),
    usable_capacity_kwh DOUBLE PRECISION CHECK (usable_capacity_kwh > 0),
    rated_power_kw DOUBLE PRECISION NOT NULL CHECK (rated_power_kw > 0),
    
    -- Charge/discharge limits
    max_charge_kw DOUBLE PRECISION NOT NULL CHECK (max_charge_kw > 0),
    max_discharge_kw DOUBLE PRECISION NOT NULL CHECK (max_discharge_kw > 0),
    continuous_charge_kw DOUBLE PRECISION,
    continuous_discharge_kw DOUBLE PRECISION,
    
    -- Efficiency
    round_trip_efficiency DOUBLE PRECISION NOT NULL DEFAULT 0.95 CHECK (round_trip_efficiency > 0 AND round_trip_efficiency <= 1),
    charge_efficiency DOUBLE PRECISION DEFAULT 0.975 CHECK (charge_efficiency > 0 AND charge_efficiency <= 1),
    discharge_efficiency DOUBLE PRECISION DEFAULT 0.975 CHECK (discharge_efficiency > 0 AND discharge_efficiency <= 1),
    
    -- State of Charge (SOC) limits
    min_soc DOUBLE PRECISION NOT NULL DEFAULT 0.1 CHECK (min_soc >= 0 AND min_soc <= 1),
    max_soc DOUBLE PRECISION NOT NULL DEFAULT 0.9 CHECK (max_soc >= 0 AND max_soc <= 1),
    initial_soc DOUBLE PRECISION DEFAULT 0.5 CHECK (initial_soc >= 0 AND initial_soc <= 1),
    target_soc DOUBLE PRECISION CHECK (target_soc >= 0 AND target_soc <= 1),
    
    -- Battery chemistry and characteristics
    chemistry VARCHAR(50) CHECK (chemistry IN (
        'lithium_ion', 'lithium_iron_phosphate', 'lead_acid', 
        'nickel_metal_hydride', 'sodium_sulfur', 'flow_battery', 'other'
    )),
    cell_voltage DOUBLE PRECISION,
    number_of_cells INTEGER,
    
    -- Thermal management
    operating_temp_min_celsius DOUBLE PRECISION,
    operating_temp_max_celsius DOUBLE PRECISION,
    optimal_temp_celsius DOUBLE PRECISION,
    cooling_type VARCHAR(50) CHECK (cooling_type IN (
        'air_cooled', 'liquid_cooled', 'passive', 'none'
    )),
    
    -- Degradation and lifecycle
    cycle_life INTEGER,  -- Expected number of full cycles
    calendar_life_years INTEGER,  -- Expected calendar life in years
    degradation_rate_per_cycle DOUBLE PRECISION,
    degradation_cost_per_kwh DOUBLE PRECISION NOT NULL DEFAULT 0.01 CHECK (degradation_cost_per_kwh >= 0),
    current_cycle_count INTEGER DEFAULT 0,
    current_health_percentage DOUBLE PRECISION DEFAULT 100.0 CHECK (current_health_percentage >= 0 AND current_health_percentage <= 100),
    
    -- Ramp rates (kW per second)
    ramp_up_rate_kw_per_sec DOUBLE PRECISION,
    ramp_down_rate_kw_per_sec DOUBLE PRECISION,
    
    -- Response time
    response_time_ms INTEGER,  -- Milliseconds to respond to dispatch signal
    
    -- Auxiliary power consumption
    auxiliary_load_kw DOUBLE PRECISION DEFAULT 0,  -- Standby power consumption
    
    -- Cost information
    capital_cost DOUBLE PRECISION,
    installation_cost DOUBLE PRECISION,
    maintenance_cost_per_year DOUBLE PRECISION,
    
    -- Communication and control
    communication_protocol VARCHAR(50),
    control_mode VARCHAR(50) CHECK (control_mode IN (
        'manual', 'automatic', 'remote', 'hybrid'
    )),
    
    -- Metadata
    metadata JSONB,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT battery_soc_limits CHECK (min_soc < max_soc),
    CONSTRAINT battery_usable_capacity CHECK (usable_capacity_kwh IS NULL OR usable_capacity_kwh <= capacity_kwh)
);

-- =====================================================
-- GRID CONNECTIONS
-- =====================================================

CREATE TABLE IF NOT EXISTS grid_connection_specs (
    asset_id UUID PRIMARY KEY REFERENCES assets(asset_id) ON DELETE CASCADE,
    
    -- Connection capacity
    max_import_kw DOUBLE PRECISION NOT NULL CHECK (max_import_kw >= 0),
    max_export_kw DOUBLE PRECISION NOT NULL CHECK (max_export_kw >= 0),
    rated_capacity_kw DOUBLE PRECISION,
    
    -- Import/export settings
    import_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    export_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Connection details
    connection_type VARCHAR(50) CHECK (connection_type IN (
        'low_voltage', 'medium_voltage', 'high_voltage', 'transmission'
    )),
    voltage_level_kv DOUBLE PRECISION,
    frequency_hz DOUBLE PRECISION DEFAULT 50.0,
    phases INTEGER CHECK (phases IN (1, 3)),
    
    -- Transformer specifications
    transformer_capacity_kva DOUBLE PRECISION,
    transformer_losses_kw DOUBLE PRECISION,
    
    -- Power factor requirements
    min_power_factor DOUBLE PRECISION CHECK (min_power_factor >= -1 AND min_power_factor <= 1),
    max_power_factor DOUBLE PRECISION CHECK (max_power_factor >= -1 AND max_power_factor <= 1),
    
    -- Reactive power capabilities
    max_reactive_import_kvar DOUBLE PRECISION,
    max_reactive_export_kvar DOUBLE PRECISION,
    
    -- Grid codes and compliance
    grid_code VARCHAR(100),  -- e.g., "IEEE 1547", "VDE-AR-N 4110"
    fault_ride_through_capable BOOLEAN DEFAULT FALSE,
    
    -- Connection point
    utility_company VARCHAR(255),
    meter_id VARCHAR(100),
    connection_point_id VARCHAR(100),
    
    -- Tariff information
    tariff_type VARCHAR(50) CHECK (tariff_type IN (
        'flat_rate', 'time_of_use', 'real_time_pricing', 'demand_charge'
    )),
    demand_charge_applicable BOOLEAN DEFAULT FALSE,
    
    -- Ramp rates
    ramp_up_rate_kw_per_sec DOUBLE PRECISION,
    ramp_down_rate_kw_per_sec DOUBLE PRECISION,
    
    -- Cost information
    connection_fee DOUBLE PRECISION,
    monthly_service_charge DOUBLE PRECISION,
    
    -- Metadata
    metadata JSONB,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- =====================================================
-- GENERATORS (Diesel, Gas, etc.)
-- =====================================================

CREATE TABLE IF NOT EXISTS generator_specs (
    asset_id UUID PRIMARY KEY REFERENCES assets(asset_id) ON DELETE CASCADE,
    
    -- Capacity
    rated_capacity_kw DOUBLE PRECISION NOT NULL CHECK (rated_capacity_kw > 0),
    max_output_kw DOUBLE PRECISION NOT NULL CHECK (max_output_kw > 0),
    min_output_kw DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (min_output_kw >= 0),
    
    -- Generator type
    generator_type VARCHAR(50) CHECK (generator_type IN (
        'diesel', 'natural_gas', 'biogas', 'dual_fuel', 'gasoline', 'propane', 'other'
    )),
    prime_mover VARCHAR(50) CHECK (prime_mover IN (
        'reciprocating_engine', 'gas_turbine', 'micro_turbine', 'fuel_cell', 'steam_turbine'
    )),
    
    -- Fuel specifications
    fuel_type VARCHAR(50),
    fuel_tank_capacity_liters DOUBLE PRECISION,
    fuel_consumption_liters_per_kwh DOUBLE PRECISION,
    fuel_cost_per_liter DOUBLE PRECISION,
    fuel_cost_per_kwh DOUBLE PRECISION NOT NULL CHECK (fuel_cost_per_kwh >= 0),
    
    -- Operating costs
    startup_cost DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (startup_cost >= 0),
    shutdown_cost DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (shutdown_cost >= 0),
    maintenance_cost_per_hour DOUBLE PRECISION DEFAULT 0,
    variable_om_cost_per_kwh DOUBLE PRECISION DEFAULT 0,
    
    -- Operating constraints
    min_uptime_hours INTEGER NOT NULL DEFAULT 1 CHECK (min_uptime_hours >= 0),
    min_downtime_hours INTEGER NOT NULL DEFAULT 1 CHECK (min_downtime_hours >= 0),
    startup_time_minutes INTEGER,
    shutdown_time_minutes INTEGER,
    
    -- Efficiency
    efficiency_at_rated_load DOUBLE PRECISION CHECK (efficiency_at_rated_load > 0 AND efficiency_at_rated_load <= 1),
    efficiency_at_min_load DOUBLE PRECISION CHECK (efficiency_at_min_load > 0 AND efficiency_at_min_load <= 1),
    heat_rate_btu_per_kwh DOUBLE PRECISION,
    
    -- Ramp rates
    ramp_up_rate_kw_per_min DOUBLE PRECISION,
    ramp_down_rate_kw_per_min DOUBLE PRECISION,
    
    -- Emissions
    co2_emissions_kg_per_kwh DOUBLE PRECISION NOT NULL DEFAULT 0.5 CHECK (co2_emissions_kg_per_kwh >= 0),
    nox_emissions_kg_per_kwh DOUBLE PRECISION,
    sox_emissions_kg_per_kwh DOUBLE PRECISION,
    particulate_emissions_kg_per_kwh DOUBLE PRECISION,
    
    -- Thermal characteristics
    waste_heat_recovery_capable BOOLEAN DEFAULT FALSE,
    waste_heat_capacity_kw DOUBLE PRECISION,
    
    -- Operating hours and maintenance
    operating_hours INTEGER DEFAULT 0,
    maintenance_interval_hours INTEGER,
    next_maintenance_hours INTEGER,
    
    -- Environmental
    noise_level_db DOUBLE PRECISION,
    requires_permit BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    metadata JSONB,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT generator_output_limits CHECK (min_output_kw <= max_output_kw)
);

-- =====================================================
-- SOLAR PV SYSTEMS
-- =====================================================

CREATE TABLE IF NOT EXISTS solar_pv_specs (
    asset_id UUID PRIMARY KEY REFERENCES assets(asset_id) ON DELETE CASCADE,
    
    -- Capacity
    rated_capacity_kw DOUBLE PRECISION NOT NULL CHECK (rated_capacity_kw > 0),
    dc_capacity_kw DOUBLE PRECISION,
    ac_capacity_kw DOUBLE PRECISION,
    
    -- Panel specifications
    panel_type VARCHAR(50) CHECK (panel_type IN (
        'monocrystalline', 'polycrystalline', 'thin_film', 'bifacial', 'other'
    )),
    number_of_panels INTEGER,
    panel_capacity_w DOUBLE PRECISION,  -- Capacity per panel
    panel_efficiency DOUBLE PRECISION CHECK (panel_efficiency > 0 AND panel_efficiency <= 1),
    panel_area_m2 DOUBLE PRECISION,
    temperature_coefficient_per_celsius DOUBLE PRECISION,  -- Typically negative
    
    -- Installation parameters
    tilt_angle_degrees DOUBLE PRECISION CHECK (tilt_angle_degrees >= 0 AND tilt_angle_degrees <= 90),
    azimuth_degrees DOUBLE PRECISION CHECK (azimuth_degrees >= 0 AND azimuth_degrees < 360),
    tracking_type VARCHAR(50) CHECK (tracking_type IN (
        'fixed', 'single_axis', 'dual_axis', 'none'
    )),
    
    -- Inverter specifications
    inverter_type VARCHAR(50) CHECK (inverter_type IN (
        'string_inverter', 'micro_inverter', 'central_inverter', 'hybrid_inverter'
    )),
    inverter_efficiency DOUBLE PRECISION CHECK (inverter_efficiency > 0 AND inverter_efficiency <= 1),
    inverter_capacity_kw DOUBLE PRECISION,
    number_of_inverters INTEGER,
    
    -- Performance characteristics
    performance_ratio DOUBLE PRECISION CHECK (performance_ratio > 0 AND performance_ratio <= 1),
    degradation_rate_per_year DOUBLE PRECISION DEFAULT 0.005,
    system_losses_percentage DOUBLE PRECISION DEFAULT 14.0,
    
    -- Environmental factors
    installation_type VARCHAR(50) CHECK (installation_type IN (
        'ground_mount', 'rooftop', 'carport', 'floating', 'building_integrated'
    )),
    shading_factor DOUBLE PRECISION DEFAULT 1.0 CHECK (shading_factor >= 0 AND shading_factor <= 1),
    soiling_factor DOUBLE PRECISION DEFAULT 0.98 CHECK (soiling_factor >= 0 AND soiling_factor <= 1),
    
    -- Grid connection
    grid_tied BOOLEAN DEFAULT TRUE,
    has_battery_storage BOOLEAN DEFAULT FALSE,
    battery_asset_id UUID REFERENCES assets(asset_id),
    
    -- Cost information
    capital_cost DOUBLE PRECISION,
    installation_cost DOUBLE PRECISION,
    maintenance_cost_per_year DOUBLE PRECISION,
    
    -- Performance monitoring
    expected_annual_production_kwh DOUBLE PRECISION,
    actual_annual_production_kwh DOUBLE PRECISION,
    capacity_factor DOUBLE PRECISION CHECK (capacity_factor >= 0 AND capacity_factor <= 1),
    
    -- Metadata
    metadata JSONB,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- =====================================================
-- WIND TURBINES
-- =====================================================

CREATE TABLE IF NOT EXISTS wind_turbine_specs (
    asset_id UUID PRIMARY KEY REFERENCES assets(asset_id) ON DELETE CASCADE,
    
    -- Capacity
    rated_capacity_kw DOUBLE PRECISION NOT NULL CHECK (rated_capacity_kw > 0),
    
    -- Turbine type
    turbine_type VARCHAR(50) CHECK (turbine_type IN (
        'horizontal_axis', 'vertical_axis'
    )),
    turbine_class VARCHAR(10),  -- IEC wind turbine class (e.g., 'I', 'II', 'III', 'IV')
    
    -- Physical specifications
    rotor_diameter_m DOUBLE PRECISION NOT NULL CHECK (rotor_diameter_m > 0),
    hub_height_m DOUBLE PRECISION NOT NULL CHECK (hub_height_m > 0),
    swept_area_m2 DOUBLE PRECISION,
    number_of_blades INTEGER,
    blade_length_m DOUBLE PRECISION,
    
    -- Operating wind speeds
    cut_in_wind_speed_mps DOUBLE PRECISION NOT NULL CHECK (cut_in_wind_speed_mps >= 0),
    rated_wind_speed_mps DOUBLE PRECISION NOT NULL CHECK (rated_wind_speed_mps > 0),
    cut_out_wind_speed_mps DOUBLE PRECISION NOT NULL CHECK (cut_out_wind_speed_mps > 0),
    survival_wind_speed_mps DOUBLE PRECISION,
    
    -- Performance
    power_coefficient DOUBLE PRECISION CHECK (power_coefficient > 0 AND power_coefficient <= 0.59),  -- Betz limit
    capacity_factor DOUBLE PRECISION CHECK (capacity_factor >= 0 AND capacity_factor <= 1),
    
    -- Generator specifications
    generator_type VARCHAR(50) CHECK (generator_type IN (
        'synchronous', 'asynchronous', 'doubly_fed_induction', 'permanent_magnet'
    )),
    
    -- Control system
    pitch_control BOOLEAN DEFAULT FALSE,
    yaw_control BOOLEAN DEFAULT FALSE,
    variable_speed BOOLEAN DEFAULT FALSE,
    
    -- Grid connection
    grid_tied BOOLEAN DEFAULT TRUE,
    voltage_regulation_capable BOOLEAN DEFAULT FALSE,
    reactive_power_control BOOLEAN DEFAULT FALSE,
    
    -- Ramp rates
    ramp_up_rate_kw_per_sec DOUBLE PRECISION,
    ramp_down_rate_kw_per_sec DOUBLE PRECISION,
    
    -- Environmental
    noise_level_db DOUBLE PRECISION,
    shadow_flicker_hours_per_year DOUBLE PRECISION,
    
    -- Cost information
    capital_cost DOUBLE PRECISION,
    installation_cost DOUBLE PRECISION,
    maintenance_cost_per_year DOUBLE PRECISION,
    
    -- Performance monitoring
    expected_annual_production_kwh DOUBLE PRECISION,
    actual_annual_production_kwh DOUBLE PRECISION,
    
    -- Operating hours
    operating_hours INTEGER DEFAULT 0,
    availability_percentage DOUBLE PRECISION,
    
    -- Metadata
    metadata JSONB,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT wind_speed_order CHECK (cut_in_wind_speed_mps < rated_wind_speed_mps AND rated_wind_speed_mps < cut_out_wind_speed_mps)
);

-- =====================================================
-- EV CHARGERS
-- =====================================================

CREATE TABLE IF NOT EXISTS ev_charger_specs (
    asset_id UUID PRIMARY KEY REFERENCES assets(asset_id) ON DELETE CASCADE,
    
    -- Charger type
    charger_level VARCHAR(20) CHECK (charger_level IN (
        'level_1', 'level_2', 'dc_fast', 'ultra_fast'
    )),
    connector_type VARCHAR(50) CHECK (connector_type IN (
        'type_1', 'type_2', 'ccs', 'chademo', 'tesla', 'gbt'
    )),
    
    -- Capacity
    max_power_kw DOUBLE PRECISION NOT NULL CHECK (max_power_kw > 0),
    number_of_ports INTEGER NOT NULL DEFAULT 1,
    simultaneous_charging BOOLEAN DEFAULT FALSE,
    
    -- Voltage and current
    voltage_v DOUBLE PRECISION,
    max_current_a DOUBLE PRECISION,
    
    -- Smart features
    smart_charging_capable BOOLEAN DEFAULT FALSE,
    v2g_capable BOOLEAN DEFAULT FALSE,  -- Vehicle-to-Grid
    load_balancing BOOLEAN DEFAULT FALSE,
    
    -- Network and communication
    networked BOOLEAN DEFAULT FALSE,
    communication_protocol VARCHAR(50),
    ocpp_version VARCHAR(20),  -- Open Charge Point Protocol
    
    -- Usage and cost
    usage_fee_per_kwh DOUBLE PRECISION,
    idle_fee_per_minute DOUBLE PRECISION,
    session_fee DOUBLE PRECISION,
    
    -- Operating constraints
    max_session_duration_minutes INTEGER,
    reservation_capable BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    metadata JSONB,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- =====================================================
-- LOAD PROFILES
-- =====================================================

CREATE TABLE IF NOT EXISTS load_specs (
    asset_id UUID PRIMARY KEY REFERENCES assets(asset_id) ON DELETE CASCADE,
    
    -- Load characteristics
    load_type VARCHAR(50) CHECK (load_type IN (
        'residential', 'commercial', 'industrial', 'agricultural', 'critical', 'flexible'
    )),
    rated_load_kw DOUBLE PRECISION NOT NULL CHECK (rated_load_kw > 0),
    average_load_kw DOUBLE PRECISION,
    peak_load_kw DOUBLE PRECISION,
    min_load_kw DOUBLE PRECISION,
    
    -- Load flexibility
    is_flexible BOOLEAN DEFAULT FALSE,
    is_critical BOOLEAN DEFAULT FALSE,
    is_sheddable BOOLEAN DEFAULT FALSE,
    priority_level INTEGER CHECK (priority_level >= 1 AND priority_level <= 10),
    
    -- Curtailment parameters
    max_curtailment_percentage DOUBLE PRECISION CHECK (max_curtailment_percentage >= 0 AND max_curtailment_percentage <= 100),
    curtailment_response_time_sec INTEGER,
    max_curtailment_duration_minutes INTEGER,
    min_recovery_time_minutes INTEGER,
    
    -- Load factor
    load_factor DOUBLE PRECISION CHECK (load_factor >= 0 AND load_factor <= 1),
    
    -- Power quality requirements
    voltage_tolerance_percentage DOUBLE PRECISION,
    frequency_tolerance_hz DOUBLE PRECISION,
    
    -- Operating schedule
    operating_hours_per_day DOUBLE PRECISION,
    operating_days_per_week INTEGER,
    seasonal_variation BOOLEAN DEFAULT FALSE,
    
    -- Cost information
    electricity_cost_per_kwh DOUBLE PRECISION,
    demand_charge_per_kw DOUBLE PRECISION,
    interruption_cost_per_kwh DOUBLE PRECISION,
    
    -- Metadata
    metadata JSONB,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- =====================================================
-- ASSET RELATIONSHIPS AND GROUPING
-- =====================================================

-- Asset groups (for organizing assets into systems)
CREATE TABLE IF NOT EXISTS asset_groups (
    group_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_name VARCHAR(255) NOT NULL,
    group_type VARCHAR(50) CHECK (group_type IN (
        'microgrid', 'vpp', 'portfolio', 'system', 'custom'
    )),
    description TEXT,
    site_id UUID REFERENCES sites(site_id),
    parent_group_id UUID REFERENCES asset_groups(group_id),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Many-to-many relationship between assets and groups
CREATE TABLE IF NOT EXISTS asset_group_members (
    asset_id UUID REFERENCES assets(asset_id) ON DELETE CASCADE,
    group_id UUID REFERENCES asset_groups(group_id) ON DELETE CASCADE,
    role VARCHAR(100),  -- Role of asset in the group
    priority INTEGER,
    added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (asset_id, group_id)
);

-- Asset dependencies (e.g., solar panel depends on inverter)
CREATE TABLE IF NOT EXISTS asset_dependencies (
    asset_id UUID REFERENCES assets(asset_id) ON DELETE CASCADE,
    depends_on_asset_id UUID REFERENCES assets(asset_id) ON DELETE CASCADE,
    dependency_type VARCHAR(50) CHECK (dependency_type IN (
        'requires', 'feeds', 'controls', 'monitors', 'backup_for'
    )),
    is_critical BOOLEAN DEFAULT FALSE,
    
    PRIMARY KEY (asset_id, depends_on_asset_id),
    CONSTRAINT no_self_dependency CHECK (asset_id != depends_on_asset_id)
);

-- =====================================================
-- ASSET TELEMETRY AND MONITORING
-- =====================================================

-- Real-time asset status (latest state)
CREATE TABLE IF NOT EXISTS asset_status (
    asset_id UUID PRIMARY KEY REFERENCES assets(asset_id) ON DELETE CASCADE,
    online BOOLEAN DEFAULT FALSE,
    operational_status VARCHAR(50) CHECK (operational_status IN (
        'online', 'offline', 'standby', 'fault', 'maintenance'
    )),
    current_power_kw DOUBLE PRECISION,
    current_soc DOUBLE PRECISION CHECK (current_soc >= 0 AND current_soc <= 1),  -- For batteries
    fault_code VARCHAR(50),
    alarm_level VARCHAR(20) CHECK (alarm_level IN ('none', 'info', 'warning', 'error', 'critical')),
    alarm_message TEXT,
    last_communication TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- =====================================================
-- MAINTENANCE AND SERVICE
-- =====================================================

CREATE TABLE IF NOT EXISTS maintenance_records (
    record_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
    maintenance_type VARCHAR(50) CHECK (maintenance_type IN (
        'preventive', 'corrective', 'predictive', 'condition_based', 'emergency'
    )),
    scheduled_date DATE,
    completed_date DATE,
    duration_hours DOUBLE PRECISION,
    performed_by VARCHAR(255),
    service_provider VARCHAR(255),
    description TEXT,
    work_performed TEXT,
    parts_replaced JSONB,
    cost DOUBLE PRECISION,
    downtime_hours DOUBLE PRECISION,
    next_maintenance_date DATE,
    status VARCHAR(20) CHECK (status IN (
        'scheduled', 'in_progress', 'completed', 'cancelled', 'overdue'
    )),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- =====================================================
-- ASSET PERFORMANCE METRICS
-- =====================================================

CREATE TABLE IF NOT EXISTS asset_performance (
    performance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Energy metrics
    total_energy_generated_kwh DOUBLE PRECISION,
    total_energy_consumed_kwh DOUBLE PRECISION,
    total_energy_charged_kwh DOUBLE PRECISION,
    total_energy_discharged_kwh DOUBLE PRECISION,
    
    -- Efficiency metrics
    average_efficiency DOUBLE PRECISION,
    capacity_factor DOUBLE PRECISION,
    availability_percentage DOUBLE PRECISION,
    
    -- Financial metrics
    total_revenue DOUBLE PRECISION,
    total_cost DOUBLE PRECISION,
    net_profit DOUBLE PRECISION,
    
    -- Environmental metrics
    co2_avoided_kg DOUBLE PRECISION,
    co2_emitted_kg DOUBLE PRECISION,
    
    -- Operational metrics
    operating_hours DOUBLE PRECISION,
    number_of_starts INTEGER,
    number_of_faults INTEGER,
    downtime_hours DOUBLE PRECISION,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- =====================================================
-- INDICES FOR PERFORMANCE
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);
CREATE INDEX IF NOT EXISTS idx_assets_site_id ON assets(site_id);
CREATE INDEX IF NOT EXISTS idx_assets_created_at ON assets(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_sites_status ON sites(status);
CREATE INDEX IF NOT EXISTS idx_sites_type ON sites(site_type);

CREATE INDEX IF NOT EXISTS idx_asset_status_operational ON asset_status(operational_status);
CREATE INDEX IF NOT EXISTS idx_asset_status_online ON asset_status(online);

CREATE INDEX IF NOT EXISTS idx_maintenance_asset ON maintenance_records(asset_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_status ON maintenance_records(status);
CREATE INDEX IF NOT EXISTS idx_maintenance_scheduled_date ON maintenance_records(scheduled_date);

CREATE INDEX IF NOT EXISTS idx_performance_asset ON asset_performance(asset_id);
CREATE INDEX IF NOT EXISTS idx_performance_period ON asset_performance(period_start, period_end);

CREATE INDEX IF NOT EXISTS idx_group_members_asset ON asset_group_members(asset_id);
CREATE INDEX IF NOT EXISTS idx_group_members_group ON asset_group_members(group_id);

-- =====================================================
-- TRIGGERS FOR AUTOMATIC TIMESTAMP UPDATES
-- =====================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all relevant tables
CREATE TRIGGER update_assets_updated_at BEFORE UPDATE ON assets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sites_updated_at BEFORE UPDATE ON sites
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_battery_specs_updated_at BEFORE UPDATE ON battery_specs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_grid_connection_specs_updated_at BEFORE UPDATE ON grid_connection_specs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_generator_specs_updated_at BEFORE UPDATE ON generator_specs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_solar_pv_specs_updated_at BEFORE UPDATE ON solar_pv_specs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_wind_turbine_specs_updated_at BEFORE UPDATE ON wind_turbine_specs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ev_charger_specs_updated_at BEFORE UPDATE ON ev_charger_specs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_load_specs_updated_at BEFORE UPDATE ON load_specs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_asset_groups_updated_at BEFORE UPDATE ON asset_groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_asset_status_updated_at BEFORE UPDATE ON asset_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_maintenance_records_updated_at BEFORE UPDATE ON maintenance_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- SAMPLE DATA (Optional - for development/testing)
-- =====================================================

-- Note: Sample data can be inserted here for development purposes
-- This will be in a separate seed file

-- =====================================================
-- VIEWS FOR COMMON QUERIES
-- =====================================================

-- View for all assets with their basic specs
CREATE OR REPLACE VIEW assets_overview AS
SELECT 
    a.asset_id,
    a.asset_type,
    a.name,
    a.location,
    a.status,
    a.site_id,
    s.site_name,
    CASE 
        WHEN a.asset_type = 'battery' THEN b.capacity_kwh
        WHEN a.asset_type = 'generator' THEN g.rated_capacity_kw
        WHEN a.asset_type = 'solar_pv' THEN sp.rated_capacity_kw
        WHEN a.asset_type = 'wind_turbine' THEN wt.rated_capacity_kw
        WHEN a.asset_type = 'grid_connection' THEN gc.max_import_kw
        WHEN a.asset_type = 'ev_charger' THEN ev.max_power_kw
        WHEN a.asset_type = 'load' THEN l.rated_load_kw
    END as capacity_or_rating,
    ast.operational_status,
    ast.online,
    a.created_at
FROM assets a
LEFT JOIN sites s ON a.site_id = s.site_id
LEFT JOIN battery_specs b ON a.asset_id = b.asset_id
LEFT JOIN generator_specs g ON a.asset_id = g.asset_id
LEFT JOIN solar_pv_specs sp ON a.asset_id = sp.asset_id
LEFT JOIN wind_turbine_specs wt ON a.asset_id = wt.asset_id
LEFT JOIN grid_connection_specs gc ON a.asset_id = gc.asset_id
LEFT JOIN ev_charger_specs ev ON a.asset_id = ev.asset_id
LEFT JOIN load_specs l ON a.asset_id = l.asset_id
LEFT JOIN asset_status ast ON a.asset_id = ast.asset_id;

-- =====================================================
-- END OF SCHEMA
-- =====================================================
