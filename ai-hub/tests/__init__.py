"""
AI Hub Service Test Suite.

Test organization:
- test_health.py: Health check endpoint tests
- test_forecast.py: Forecast generation tests
- test_anomaly.py: Anomaly detection tests
- test_explain.py: Model explainability tests
- test_auth.py: Authentication and authorization tests (TODO)
- integration/: Integration tests (TODO)

Test markers:
- @pytest.mark.unit: Unit tests (fast, isolated)
- @pytest.mark.integration: Integration tests (slower, external dependencies)
- @pytest.mark.slow: Slow tests (can be skipped with -m "not slow")
- @pytest.mark.auth: Authentication-related tests
- @pytest.mark.ml: Machine learning model tests

Run tests:
    pytest                          # Run all tests
    pytest -v                       # Verbose output
    pytest -m "not slow"            # Skip slow tests
    pytest -m unit                  # Run only unit tests
    pytest --cov=app                # With coverage
    pytest tests/test_health.py     # Specific file
"""

__version__ = "0.1.0"
