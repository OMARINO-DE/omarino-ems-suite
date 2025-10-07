# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: **omar@omarino.de**

You should receive a response within 48 hours. If for some reason you do not, please follow up to ensure we received your original message.

Please include the following information:

- **Type of issue** (e.g., SQL injection, authentication bypass, XSS)
- **Full paths** of source file(s) related to the issue
- **Location** of the affected source code (tag/branch/commit or direct URL)
- **Step-by-step instructions** to reproduce the issue
- **Proof-of-concept or exploit code** (if possible)
- **Impact** of the issue, including how an attacker might exploit it

This information will help us triage your report more quickly.

## Security Update Process

1. **Report received** - We acknowledge receipt within 48 hours
2. **Assessment** - We assess the severity and impact (1-7 days)
3. **Fix development** - We develop and test a fix (timeline depends on severity)
4. **Coordinated disclosure** - We coordinate disclosure with reporter
5. **Release** - We release patched version
6. **Public disclosure** - We publish security advisory

## Security Best Practices for Users

### Deployment

- **Always use HTTPS** in production
- **Enable authentication** (OIDC) - never deploy without auth
- **Use strong secrets** - generate with `openssl rand -base64 32`
- **Rotate secrets regularly** - at least every 90 days
- **Limit network exposure** - use firewalls, VPCs, security groups
- **Keep containers updated** - watch for security patches

### Configuration

```bash
# Strong PostgreSQL password
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# JWT signing key
JWT_SECRET_KEY=$(openssl rand -base64 64)

# Redis password
REDIS_PASSWORD=$(openssl rand -base64 32)
```

### Secrets Management

- **Never commit** `.env` files
- Use **Docker secrets** (Swarm) or **Kubernetes secrets** (K8s)
- Use **managed secret services** (AWS Secrets Manager, Azure Key Vault) in production
- **Encrypt secrets at rest** in your secret store

### Access Control

- **Enable RBAC** - assign minimum necessary roles
- **Audit access logs** - review regularly for suspicious activity
- **Disable default accounts** - create user-specific accounts
- **Use API keys** for service-to-service auth

### Database Security

- **Enable SSL/TLS** for PostgreSQL connections
- **Restrict network access** - allow only service IPs
- **Regular backups** - encrypted and tested
- **Patch regularly** - stay current with PostgreSQL releases

### Container Security

- **Run as non-root** - all our Dockerfiles specify non-root users
- **Scan images** - use `trivy` or similar tools
- **Minimal base images** - we use Alpine or distroless
- **Read-only filesystems** where possible

### Monitoring

- **Enable audit logging** - track authentication, authorization, data access
- **Monitor metrics** - watch for anomalies (failed auth, unusual traffic)
- **Set up alerts** - notify security team of suspicious events
- **Regular reviews** - analyze logs weekly

## Known Security Considerations

### Current Limitations (v0.1.x)

- **No built-in WAF** - deploy behind a web application firewall in production
- **Basic rate limiting** - consider additional DDoS protection
- **Local file storage** - outputs stored locally; consider object storage for production
- **No encryption at rest** - database encryption not enabled by default

### Planned Enhancements

- Field-level encryption for sensitive data
- Hardware security module (HSM) integration
- Advanced threat detection
- Compliance certifications (SOC 2, ISO 27001)

## Security Headers

API Gateway includes these security headers:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

## Dependency Management

- **Automated scanning** via GitHub Dependabot
- **Regular updates** - dependencies updated monthly
- **Security patches** - applied ASAP for critical vulnerabilities
- **Lock files** committed to ensure reproducible builds

## Audit Trail

All services log:
- Authentication attempts (success/failure)
- Authorization decisions
- Data access (read/write operations)
- Configuration changes
- Job executions

Logs are structured JSON with:
- Timestamp (ISO 8601)
- User/service identity
- Action performed
- Resource affected
- Outcome (success/error)

## Compliance

OMARINO EMS Suite is designed to support:

- **GDPR** - data minimization, right to deletion, audit logs
- **NIS2** (EU) - for critical infrastructure
- **NERC CIP** (US) - for bulk electric systems (with additional controls)

However, compliance certification is the responsibility of the deploying organization.

## Contact

- **Security issues**: omar@omarino.de
- **General inquiries**: GitHub Discussions
- **Commercial support**: (to be determined)

---

**Last updated**: October 2025
