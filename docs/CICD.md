# CI/CD Documentation

Comprehensive guide to the CI/CD pipelines for OMARINO EMS Suite.

## 📋 Table of Contents

- [Overview](#overview)
- [GitHub Actions Workflows](#github-actions-workflows)
- [Service-Specific Pipelines](#service-specific-pipelines)
- [Container Registry](#container-registry)
- [Deployment Environments](#deployment-environments)
- [Secrets and Configuration](#secrets-and-configuration)
- [Monitoring and Notifications](#monitoring-and-notifications)

---

## 🎯 Overview

The OMARINO EMS Suite uses GitHub Actions for continuous integration and deployment. Each microservice has its own dedicated CI pipeline that:

1. **Builds** the service
2. **Tests** the code (unit, integration)
3. **Lints** for code quality
4. **Scans** for security vulnerabilities
5. **Builds** Docker images
6. **Pushes** to GitHub Container Registry
7. **Deploys** to staging/production

## 🔄 GitHub Actions Workflows

### Service Pipelines

| Workflow | Service | Language/Framework | Triggers |
|----------|---------|-------------------|----------|
| `ci-timeseries.yml` | timeseries-service | .NET 8 | Changes to service, PRs |
| `ci-forecast.yml` | forecast-service | Python 3.11 | Changes to service, PRs |
| `ci-optimize.yml` | optimize-service | Python 3.11 | Changes to service, PRs |
| `ci-gateway.yml` | api-gateway | .NET 8 | Changes to service, PRs |
| `ci-scheduler.yml` | scheduler-service | .NET 8 | Changes to service, PRs |
| `ci-webapp.yml` | webapp | Node.js 20 | Changes to service, PRs |

### Special Workflows

| Workflow | Purpose | Triggers |
|----------|---------|----------|
| `ci-e2e.yml` | End-to-end testing | All pushes, PRs, daily cron, manual |
| `release.yml` | Production releases | Git tags (`v*.*.*`) |

---

## 🏗️ Service-Specific Pipelines

### .NET Services (timeseries, gateway, scheduler)

**Jobs:**
1. **build-and-test**
   - Setup .NET 8
   - Restore NuGet packages (with caching)
   - Build in Release mode
   - Run tests with code coverage
   - Upload coverage to Codecov

2. **lint**
   - Run `dotnet format` to check code formatting
   - Run code analysis with warnings as errors

3. **docker**
   - Build Docker image with Buildx
   - Push to GitHub Container Registry
   - Use GitHub Actions cache for layers

4. **deploy-staging** (on develop branch)
   - Deploy to staging environment
   - Update service with new image

**Example:**
```yaml
# Triggered on:
- Push to main/develop branches
- Pull requests to main/develop
- Changes to service files

# Output:
- Test results
- Code coverage reports
- Docker images tagged with:
  - Branch name (main, develop)
  - Git SHA (main-abc123)
  - Semantic version (1.2.3)
  - Latest (for main branch)
```

### Python Services (forecast, optimize)

**Jobs:**
1. **build-and-test**
   - Setup Python 3.11
   - Install dependencies (with pip caching)
   - Install system dependencies (solvers for optimize)
   - Run pytest with coverage
   - Upload coverage to Codecov

2. **lint**
   - Run Ruff for fast linting
   - Check code formatting with Black
   - Check import sorting with isort
   - Run mypy for type checking

3. **security**
   - Run Safety to check for vulnerable dependencies
   - Run Bandit for security issues in code

4. **docker**
   - Build Docker image
   - Push to registry
   - Use layer caching

5. **deploy-staging** (on develop branch)
   - Deploy to staging environment

**Example:**
```yaml
# Additional features:
- Security scanning (Safety, Bandit)
- Type checking (mypy)
- Stricter code quality checks

# Dependencies cached:
- ~/.cache/pip
- Pre-installed packages
```

### Node.js Service (webapp)

**Jobs:**
1. **build-and-test**
   - Setup Node.js 20
   - Install dependencies (npm ci with caching)
   - Run ESLint
   - Run TypeScript type checking
   - Run tests with coverage
   - Build Next.js application
   - Upload coverage to Codecov

2. **lint**
   - Run ESLint
   - Check Prettier formatting
   - Run TypeScript compiler

3. **docker**
   - Build optimized production image
   - Push to registry

4. **deploy-staging** (on develop branch)
   - Deploy to staging environment

**Example:**
```yaml
# Build-time environment variables:
NEXT_PUBLIC_API_URL: https://api.omarino-ems.com

# Cached:
- node_modules (via package-lock.json hash)
- Next.js build cache
```

---

## 🧪 End-to-End Testing Workflow

**File:** `.github/workflows/ci-e2e.yml`

**Purpose:** Comprehensive system testing across all services

**Triggers:**
- Push to main/develop
- Pull requests
- **Daily at 2 AM UTC** (cron: `0 2 * * *`)
- Manual trigger via GitHub UI

**Process:**
1. **Setup Environment**
   - Create `.env` from template
   - Start all services with `docker-compose up -d`
   - Wait for services to be healthy (up to 3 minutes)

2. **Health Checks**
   - Verify each service responds
   - Check `/health` endpoints

3. **Import Sample Data**
   - Setup Python 3.11
   - Install requests library
   - Run `import-sample-data.py`

4. **Run Test Suite**
   - Execute `e2e-test.sh`
   - 12 comprehensive tests:
     1. Authentication
     2. Health checks
     3. Create meter
     4. Ingest time series
     5. Query time series
     6. List forecast models
     7. Run forecast
     8. List optimization types
     9. Create optimization
     10. Create workflow
     11. Prometheus metrics
     12. Grafana health

5. **On Failure**
   - Collect logs from all services
   - Upload as artifacts

6. **Cleanup**
   - Stop and remove containers
   - Clean up volumes

**Timeout:** 30 minutes

---

## 🚀 Release Workflow

**File:** `.github/workflows/release.yml`

**Trigger:** Git tags matching `v*.*.*` (e.g., `v1.0.0`)

**Process:**

### 1. Create GitHub Release
- Generate changelog from commits
- Create release notes
- List Docker image tags
- Include deployment instructions

### 2. Build and Push Release Images
- Matrix strategy builds all 6 services in parallel
- Tags images with:
  - Full version (`1.2.3`)
  - Major version (`1`)
  - Minor version (`1.2`)
  - `latest`

### 3. Deploy to Production
- Uses GitHub Environment: `production`
- Requires manual approval
- Runs deployment script
- Verifies deployment

**Example Release:**
```bash
# Create a release
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# This triggers:
# 1. GitHub Release creation
# 2. Docker images built and pushed
# 3. Production deployment (with approval)
```

**Docker Images Published:**
```
ghcr.io/YOUR_USERNAME/omarino-ems-suite/timeseries-service:1.0.0
ghcr.io/YOUR_USERNAME/omarino-ems-suite/timeseries-service:1
ghcr.io/YOUR_USERNAME/omarino-ems-suite/timeseries-service:1.0
ghcr.io/YOUR_USERNAME/omarino-ems-suite/timeseries-service:latest
```

---

## 📦 Container Registry

**Registry:** GitHub Container Registry (ghcr.io)

**Image Naming:**
```
ghcr.io/<username>/<repo>/<service>:<tag>
```

**Image Tags:**

| Tag Pattern | Example | Description |
|------------|---------|-------------|
| `main` | `main` | Latest from main branch |
| `develop` | `develop` | Latest from develop branch |
| `<branch>-<sha>` | `main-abc1234` | Specific commit |
| `<version>` | `1.2.3` | Semantic version |
| `<major>.<minor>` | `1.2` | Minor version |
| `<major>` | `1` | Major version |
| `latest` | `latest` | Latest release |

**Pulling Images:**
```bash
# Pull latest development
docker pull ghcr.io/YOUR_USERNAME/omarino-ems-suite/timeseries-service:develop

# Pull specific version
docker pull ghcr.io/YOUR_USERNAME/omarino-ems-suite/timeseries-service:1.0.0

# Pull latest release
docker pull ghcr.io/YOUR_USERNAME/omarino-ems-suite/timeseries-service:latest
```

**Authentication:**
```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# For CI/CD, use GITHUB_TOKEN secret (automatic)
```

---

## 🌍 Deployment Environments

### Staging

**Branch:** `develop`  
**URL:** `https://staging.omarino-ems.com`  
**Auto-deploy:** Yes (on successful CI)

**Services:**
- API Gateway: `https://staging-api.omarino-ems.com`
- Web UI: `https://staging.omarino-ems.com`

**Purpose:**
- Integration testing
- QA validation
- Demo environment
- Pre-production verification

### Production

**Branch:** `main`  
**URL:** `https://omarino-ems.com`  
**Deploy:** Manual approval required

**Services:**
- API Gateway: `https://api.omarino-ems.com`
- Web UI: `https://omarino-ems.com`

**Process:**
1. Create release tag (e.g., `v1.0.0`)
2. Release workflow builds images
3. Manual approval in GitHub
4. Deployment to production
5. Health check verification
6. Notification sent

---

## 🔐 Secrets and Configuration

### Required GitHub Secrets

| Secret | Purpose | Used By |
|--------|---------|---------|
| `GITHUB_TOKEN` | Container registry authentication | All workflows (automatic) |
| `CODECOV_TOKEN` | Upload code coverage | All service workflows |
| `STAGING_DEPLOY_KEY` | SSH key for staging deployment | Staging jobs |
| `PROD_DEPLOY_KEY` | SSH key for production deployment | Release workflow |
| `SLACK_WEBHOOK_URL` | Notifications | Release workflow |

### Setting Secrets

1. Go to repository **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add each secret with its value

### Environment Variables

**Development (.env):**
```bash
# See .env.example for all variables
POSTGRES_PASSWORD=dev_password
REDIS_PASSWORD=dev_redis_password
JWT_SECRET_KEY=dev_jwt_secret_32_chars_minimum
```

**Production:**
- Managed via CI/CD deployment scripts
- Stored in deployment platform (Kubernetes secrets, AWS Secrets Manager, etc.)
- Never committed to repository

---

## 📊 Monitoring and Notifications

### Code Coverage

**Provider:** Codecov  
**Reports:** Uploaded after every test run

**View Coverage:**
- Badge in README shows overall coverage
- Detailed reports at `https://codecov.io/gh/YOUR_USERNAME/omarino-ems-suite`

**Coverage by Service:**
- timeseries-service (flag: `timeseries-service`)
- forecast-service (flag: `forecast-service`)
- optimize-service (flag: `optimize-service`)
- api-gateway (flag: `api-gateway`)
- scheduler-service (flag: `scheduler-service`)
- webapp (flag: `webapp`)

### Workflow Status

**View Status:**
- Repository → **Actions** tab
- Status badges in README
- Email notifications (configure in GitHub profile)

**Notifications:**
- Failed workflows send email to committer
- Can integrate with Slack/Discord/Teams
- Status checks on PRs

### Build Times

**Typical CI Times:**

| Service | Build + Test | Docker Build | Total |
|---------|-------------|--------------|-------|
| timeseries-service | 2-3 min | 2-3 min | 5-6 min |
| forecast-service | 3-4 min | 4-5 min | 8-10 min |
| optimize-service | 4-5 min | 4-5 min | 9-11 min |
| api-gateway | 2-3 min | 2-3 min | 5-6 min |
| scheduler-service | 2-3 min | 2-3 min | 5-6 min |
| webapp | 3-4 min | 3-4 min | 7-9 min |
| E2E tests | 10-15 min | N/A | 10-15 min |

**Optimization:**
- Dependency caching (NuGet, pip, npm)
- Docker layer caching
- Parallel job execution
- Matrix builds for releases

---

## 🛠️ Maintenance

### Updating Dependencies

**Automated (Dependabot):**
- GitHub automatically creates PRs for dependency updates
- CI runs on each PR
- Merge after review

**Manual:**
```bash
# .NET services
dotnet outdated
dotnet add package <PackageName> --version <Version>

# Python services
pip list --outdated
pip install --upgrade <package>

# Node.js
npm outdated
npm update
```

### Cache Management

**Clear Caches:**
1. Repository → **Actions** → **Caches**
2. Delete old caches
3. Next workflow run will rebuild cache

**Cache Keys:**
- NuGet: `${{ runner.os }}-nuget-${{ hashFiles('**/packages.lock.json') }}`
- pip: Automatic via `actions/setup-python@v5`
- npm: Automatic via `actions/setup-node@v4`
- Docker: GitHub Actions cache (`type=gha`)

### Workflow Optimization

**Best Practices:**
1. **Use matrix builds** for parallel execution
2. **Cache dependencies** to speed up builds
3. **Limit triggers** to relevant paths
4. **Use self-hosted runners** for faster builds (if needed)
5. **Optimize Docker builds** with multi-stage builds

---

## 📝 Troubleshooting

### Common Issues

#### Build Failing

**Problem:** Build fails on CI but works locally

**Solutions:**
1. Check dependency versions match
2. Verify environment variables
3. Review build logs in GitHub Actions
4. Test in clean environment locally:
   ```bash
   # Clean build
   git clean -fdx
   docker-compose down -v
   docker-compose up --build
   ```

#### Tests Failing

**Problem:** Tests pass locally but fail on CI

**Solutions:**
1. Check for timing issues (use proper waits)
2. Verify test isolation (no shared state)
3. Check environment-specific configurations
4. Run tests with verbose output:
   ```bash
   dotnet test --verbosity detailed
   pytest -vv
   npm test -- --verbose
   ```

#### Docker Build Slow

**Problem:** Docker builds taking too long

**Solutions:**
1. Check cache is working:
   - View cache in Actions → Caches
   - Verify cache keys are consistent
2. Optimize Dockerfile:
   - Order layers by change frequency
   - Use multi-stage builds
   - Minimize layers
3. Use BuildKit:
   ```yaml
   env:
     DOCKER_BUILDKIT: 1
   ```

#### E2E Tests Timeout

**Problem:** E2E tests timing out

**Solutions:**
1. Increase timeout in workflow (default: 30min)
2. Check service startup times:
   ```bash
   docker-compose logs --tail=100
   ```
3. Increase wait times in `e2e-test.sh`
4. Check resource allocation for CI runners

---

## 🔄 Workflow Examples

### Run E2E Tests Manually

```bash
# Via GitHub CLI
gh workflow run ci-e2e.yml

# Via GitHub UI
# 1. Go to Actions tab
# 2. Select "CI - End-to-End Tests"
# 3. Click "Run workflow"
```

### Create a Release

```bash
# 1. Create and push tag
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0

# 2. Release workflow runs automatically
# 3. Approve production deployment in GitHub UI
# 4. Verify deployment
curl https://api.omarino-ems.com/health
```

### Debug Failed Workflow

```bash
# 1. Download artifacts
gh run download <run-id>

# 2. View logs
gh run view <run-id> --log

# 3. Re-run failed jobs
gh run rerun <run-id> --failed
```

---

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build GitHub Action](https://github.com/docker/build-push-action)
- [Codecov Documentation](https://docs.codecov.com/)
- [OMARINO EMS Architecture](./ARCHITECTURE.md)
- [Infrastructure Guide](./INFRASTRUCTURE.md)
- [Operational Runbook](./RUNBOOK.md)

---

**Document Version:** 1.0  
**Last Updated:** October 2025  
**Maintainer:** OMARINO EMS Team
