# ADR-0001: Microservices Architecture with Polyglot Technology Stack

**Status:** Accepted

**Date:** 2025-10-02

**Deciders:** Omar Zaror (Project Lead)

**Context:**
## Context

We need to design the architecture for OMARINO EMS Suite, an open-source platform for energy management systems. The system must handle time-series data ingestion, forecasting, optimization, and workflow orchestration for energy management systems.

## Decision
We will implement a **microservices architecture** using a **polyglot technology stack** with the following design principles:

### Architecture Style
- **Microservices**: Each domain capability (timeseries, forecast, optimize, scheduler) runs as an independent service
- **Monorepo**: All services in one repository for easier coordination during initial development
- **Containerized**: Docker containers for all services, orchestrated via Docker Compose (with optional Kubernetes support)

### Technology Choices

#### Backend Services
1. **ASP.NET Core 8** for:
   - API Gateway (authentication, routing, rate limiting)
   - Time Series Service (high-performance I/O, EF Core integration)
   - Scheduler Service (Quartz.NET integration)
   
   **Rationale:**
   - Excellent async/await performance for I/O-bound operations
   - Native OpenTelemetry support
   - Strong typing with C# 12
   - Mature ecosystem for enterprise applications
   - Built-in dependency injection

2. **Python 3.11 + FastAPI** for:
   - Forecast Service (ML/statistical models)
   - Optimize Service (mathematical optimization)
   
   **Rationale:**
   - Rich ecosystem for ML (scikit-learn, statsmodels, neuralforecast)
   - Optimization libraries (Pyomo, PuLP) with solver bindings
   - Fast development cycles for data science teams
   - Type hints with Pydantic for contracts
   - Automatic OpenAPI generation

#### Data Storage
- **PostgreSQL 16 + Timescale Extension**
  
  **Rationale:**
  - ACID compliance for transactional consistency
  - Timescale hypertables optimized for time-series workloads
  - Continuous aggregates for efficient rollups
  - Mature, well-understood, free and open-source
  - Excellent performance for analytical queries

#### Messaging & Caching
- **Redis**
  
  **Rationale:**
  - Simple setup for job queues (Scheduler)
  - Pub/sub for event notifications
  - Caching for forecast models and results
  - Low latency, high throughput
  - Optional Redis Streams for durable queuing

#### Frontend
- **Next.js 14 + TypeScript + React 18**
  
  **Rationale:**
  - Server-side rendering (SSR) and static generation for performance
  - TypeScript for type safety across full stack
  - Excellent developer experience with hot reload
  - Large ecosystem of React components
  - Built-in API routes for BFF pattern

#### Authentication & Authorization
- **OpenID Connect (OIDC) / OAuth2**
  
  **Rationale:**
  - Industry standard protocol
  - Compatible with Keycloak, Auth0, Azure AD, AWS Cognito
  - Token-based (JWT) for stateless validation
  - Supports various flows (authorization code, client credentials)

#### Observability
- **OpenTelemetry + Prometheus + Grafana**
  
  **Rationale:**
  - Vendor-neutral instrumentation
  - Distributed tracing across polyglot services
  - Standardized metrics collection
  - Free, open-source monitoring stack
  - Wide adoption and community support

### Service Communication
- **HTTP/REST** for synchronous client-facing APIs
- **HTTP** for inter-service communication (initially)
- **Redis Streams** for asynchronous job processing
- **Future:** gRPC for performance-critical internal calls (Phase 2)

### Data Model Strategy
- **Shared Schemas**: JSON Schema definitions in `/shared/schemas`
- **OpenAPI Contracts**: Auto-generated from code annotations
- **Client SDKs**: Generated TypeScript, Python, C# clients
- **Versioning**: API versioning via URL path (`/v1/forecast`)

## Consequences

### Positive
✅ **Best tool for each job**: Use .NET for I/O, Python for ML/optimization  
✅ **Independent scaling**: Scale CPU-intensive optimize service separately  
✅ **Team autonomy**: Teams can work on services independently  
✅ **Technology flexibility**: Swap implementations without affecting others  
✅ **Polyglot skills**: Developers learn multiple modern stacks  
✅ **Open-source**: No vendor lock-in, no licensing costs  
✅ **Strong typing**: C#, Python type hints, TypeScript ensure correctness  

### Negative
❌ **Operational complexity**: More services to deploy and monitor  
❌ **Network latency**: Inter-service calls add overhead  
❌ **Distributed debugging**: Harder to trace requests across services  
❌ **Polyglot challenges**: Teams need expertise in multiple languages  
❌ **Data consistency**: Need careful design for distributed transactions  

### Mitigations
- **Dev Container**: Unified development environment with all tools
- **OpenTelemetry**: Distributed tracing to debug across services
- **Docker Compose**: Simple local orchestration for development
- **Saga Pattern**: For distributed workflows requiring coordination
- **Health checks**: Liveness/readiness probes for all services
- **Documentation**: Clear runbooks and architecture diagrams

## Alternatives Considered

### 1. Monolithic .NET Application
**Pros:** Simpler deployment, easier debugging, single language  
**Cons:** Python ML libraries not available, harder to scale components independently  
**Rejected:** Python ML/optimization ecosystem is critical

### 2. Pure Python Stack (Django/Flask)
**Pros:** Single language, rich data science ecosystem  
**Cons:** Lower I/O performance, weaker typing, less enterprise tooling  
**Rejected:** .NET provides better performance and type safety for APIs

### 3. Node.js + TypeScript for All Services
**Pros:** Single language, full-stack JavaScript, async I/O  
**Cons:** Limited ML/optimization libraries, less mature for enterprise backends  
**Rejected:** Python's ML ecosystem is unmatched

### 4. Apache Kafka for Messaging
**Pros:** Better for high-throughput event streaming  
**Cons:** Overkill for initial requirements, more operational overhead  
**Deferred:** Consider for Phase 3 if ingestion volume warrants it

## Implementation Plan

### Phase 1: Foundation (v0.1.0)
- Scaffold all services with basic endpoints
- Implement shared schemas and contracts
- Docker Compose orchestration
- Basic CI/CD with GitHub Actions

### Phase 2: Core Features (v0.2.0)
- Complete time-series ingestion and querying
- Implement baseline forecast models
- Basic optimization solver integration
- DAG-based scheduler

### Phase 3: Production Readiness (v0.3.0)
- Advanced ML models (N-HiTS)
- Stochastic optimization
- Kubernetes manifests
- Performance optimization (gRPC, caching)

### Phase 4: Enterprise Features (v1.0.0)
- Multi-tenancy
- Advanced RBAC
- Compliance rule packs
- High availability setup

## References
- [C4 Model for Architecture Diagrams](https://c4model.com/)
- [Microservices Patterns](https://microservices.io/patterns/)
- [The Twelve-Factor App](https://12factor.net/)
- [OpenTelemetry Specification](https://opentelemetry.io/docs/specs/otel/)

---

**Next ADR:** ADR-0002: Time Series Data Model and Storage Strategy
