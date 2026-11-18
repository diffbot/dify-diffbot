# Changelog

## 0.1.0 - 2026-11-17

Plugin version stays 0.1.0. It is not on the Dify Marketplace.

### Changed

- Pin `diffbot==3.4.0rc0` in `diffbot/requirements.txt` and `diffbot/pyproject.toml` so CI can verify the SDK release candidate. Switch to `==3.4.0` for the unison publish.
- Remove the editable `/workspace/diffbot-python` path from `requirements-dev.txt`.
- CI installs the pin from PyPI and runs the SDK-dependent tests (the skip in `tests/conftest.py` is gone).

This repo does not publish to npm or PyPI. Shipping is a Dify Marketplace pull request, which is separate from merging this branch. Feature-detect fallbacks in `diffbot/tools/sdk.py` are still in the tree for that submission.
