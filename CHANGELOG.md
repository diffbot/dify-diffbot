# Changelog

## Unreleased (still plugin 0.1.0)

- Removed the `client.request()` fallbacks in `diffbot/tools/sdk.py` for `verify_token`, `crawl_download`, and extract options, and the local response TypedDicts in `tools/sdk_types.py`. `diffbot==3.4.0` has all of them natively. No behavior change.
- Reran the marketplace validator on the rebuilt package; results are in SUBMISSION.md.

## 0.1.0 - 2026-11-17

Plugin version stays 0.1.0. It is not on the Dify Marketplace.

### Changed

- Pin `diffbot==3.4.0` in `diffbot/requirements.txt` and `diffbot/pyproject.toml`.
- Remove the editable `/workspace/diffbot-python` path from `requirements-dev.txt`.
- CI installs the pin from PyPI and runs the SDK-dependent tests (the skip in `tests/conftest.py` is gone).

This repo does not publish to npm or PyPI. Shipping is a Dify Marketplace pull request, which is separate from merging this branch. The feature-detect fallbacks in `diffbot/tools/sdk.py` were removed afterwards (see below).
