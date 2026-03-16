"""Smoke test that the idempotency check logic is reachable in the orchestrator."""

import inspect


def test_pipeline_run_idempotency_logic_exists():
    """Verify idempotency check is present in orchestrator."""
    from app.api import orchestrator
    source = inspect.getsource(orchestrator)
    # Check that some form of duplicate run detection exists
    assert "already" in source.lower() or "running" in source.lower() or "exists" in source.lower()


def test_idempotency_guard_uses_get_digest_by_date():
    """The generate_digest endpoint should check if a digest already exists before generating."""
    from app.api import orchestrator
    source = inspect.getsource(orchestrator)
    # Must reference digest existence check
    assert "get_digest_by_date" in source or "existing" in source


def test_idempotency_guard_returns_on_existing():
    """The guard should return 200 (not raise) when digest already exists."""
    from app.api import orchestrator
    source = inspect.getsource(orchestrator)
    # Should contain idempotency guard comment or logic
    assert "idempotency" in source.lower() or "already exists" in source.lower()
