# Contributing to OMARINO EMS Suite

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the behavior
- **Expected vs. actual behavior**
- **Environment details** (OS, Docker version, service versions)
- **Logs and error messages**
- **Screenshots** if applicable

Use the bug report issue template.

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide detailed description** of the proposed functionality
- **Explain why this enhancement would be useful**
- **List any alternative solutions** you've considered

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Follow the coding standards** (see below)
3. **Write or update tests** as appropriate
4. **Update documentation** if you're changing functionality
5. **Ensure CI passes** (linting, tests, builds)
6. **Fill out the PR template** completely
7. **Link related issues** in the PR description

## Development Workflow

### Setting Up Development Environment

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/omarino-ems-suite.git
cd omarino-ems-suite

# Open in Dev Container (recommended)
# Or install dependencies manually:
# - .NET 8 SDK
# - Python 3.11
# - Node.js 20
# - Docker Desktop

# Copy environment file
cp .env.example .env

# Start infrastructure
docker-compose up -d postgres redis

# Run tests
make test
```

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation only
- `refactor/description` - Code refactoring
- `test/description` - Test improvements

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

**Examples:**
```
feat(forecast): add N-HiTS neural forecasting model

Implements N-HiTS deep learning model with:
- Multi-horizon forecasting
- Quantile prediction
- Model checkpointing

Closes #42

---

fix(timeseries): handle DST transitions correctly

Fixes timezone handling during daylight saving transitions
by using NodaTime for all temporal operations.

Fixes #89
```

## Coding Standards

### C# (.NET)

- Follow [Microsoft C# Coding Conventions](https://learn.microsoft.com/en-us/dotnet/csharp/fundamentals/coding-style/coding-conventions)
- Use `dotnet format` before committing
- Enable nullable reference types
- Use async/await consistently
- Write XML documentation comments for public APIs

```csharp
/// <summary>
/// Ingests time-series data points in bulk.
/// </summary>
/// <param name="points">Collection of data points to ingest.</param>
/// <param name="cancellationToken">Cancellation token.</param>
/// <returns>Number of points ingested successfully.</returns>
public async Task<int> IngestAsync(
    IEnumerable<TimeSeriesPoint> points,
    CancellationToken cancellationToken = default)
{
    // Implementation
}
```

### Python

- Follow [PEP 8](https://pep8.org/)
- Use `ruff` for linting and `black` for formatting
- Type hints for all function signatures
- Docstrings for public functions (Google style)

```python
def forecast_series(
    series_id: str,
    horizon: int,
    model: ForecastModel,
) -> ForecastResult:
    """Generate forecast for a time series.
    
    Args:
        series_id: Unique identifier for the series
        horizon: Number of periods to forecast
        model: Forecasting model to use
        
    Returns:
        Forecast result with point and quantile predictions
        
    Raises:
        ValueError: If series_id is not found
        ModelError: If forecasting fails
    """
    # Implementation
```

### TypeScript/JavaScript

- Follow [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- Use ESLint and Prettier (configs provided)
- Prefer functional components and hooks (React)
- Export types alongside implementations

```typescript
interface ForecastRequest {
  seriesId: string;
  horizon: number;
  granularity: string;
}

export async function requestForecast(
  request: ForecastRequest
): Promise<ForecastResponse> {
  // Implementation
}
```

## Testing Requirements

### Unit Tests

- **Coverage**: Aim for ≥80% for critical business logic
- **C#**: xUnit with FluentAssertions
- **Python**: pytest with pytest-cov
- **TypeScript**: Jest or Vitest

### Integration Tests

- Use Testcontainers for database tests
- Test API contracts with real HTTP calls
- Mock external services

### E2E Tests

- Playwright for web UI tests
- Test critical user journeys
- Run in CI before merge

### Running Tests Locally

```bash
# All tests
make test

# Specific service
cd timeseries-service
dotnet test

cd forecast-service
pytest

cd webapp
pnpm test
```

## Documentation

- Update `docs/` when adding features
- Include API examples with curl/httpie
- Add ADRs for significant decisions
- Keep README.md current

## Review Process

1. **Automated checks** must pass (CI)
2. **Code review** by at least one maintainer
3. **Documentation review** if applicable
4. **Testing verification** - reviewer may run locally
5. **Approval and merge** - squash or rebase as appropriate

## Performance Guidelines

- Profile before optimizing
- Benchmark critical paths
- Document performance characteristics
- Consider scalability impact

## Security Guidelines

- **Never commit secrets** (use `.env.example` as template)
- **Validate all inputs** at API boundaries
- **Use parameterized queries** (no SQL injection)
- **Sanitize user content** in web UI
- **Report security issues privately** via SECURITY.md

## Getting Help

- **GitHub Discussions**: Ask questions, share ideas
- **Issue Comments**: Discuss specific bugs/features
- **Code Comments**: Explain complex logic inline

## Recognition

Contributors will be recognized in:
- Release notes
- CONTRIBUTORS.md file
- GitHub contributors graph

Thank you for helping make OMARINO EMS Suite better! 🎉
