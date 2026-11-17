"""Skip SDK-dependent test modules when the ``diffbot`` SDK is not installed.

GitHub CI cannot reach the unreleased local SDK (see requirements-dev.txt), so there
only the SDK-independent policy tests run. TODO: once diffbot 3.2.0/3.3.0 is on PyPI,
pin it in diffbot/requirements.txt and delete this file so every test runs in CI.
"""

try:
    import diffbot  # noqa: F401
except ImportError:
    collect_ignore = ["test_tools_http.py", "test_sdk_wiring.py"]
    print("diffbot SDK not installed: skipping SDK-dependent tests (see tests/conftest.py)")
