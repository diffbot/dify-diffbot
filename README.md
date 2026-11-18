# Diffbot plugin for Dify

A [Dify](https://dify.ai/) tool plugin that brings Diffbot web search, page extraction, and Knowledge Graph lookups into Dify agents and workflows.

The installable plugin is in [`diffbot/`](diffbot/). Its [README](diffbot/README.md) covers setup, credentials, and each tool, and [PRIVACY.md](diffbot/PRIVACY.md) is the plugin privacy policy. Marketplace publishing steps are in [SUBMISSION.md](SUBMISSION.md).

- Source: https://github.com/diffbot/dify-diffbot
- Support: support@diffbot.com
- License: [MIT](LICENSE)

## Tools

| Tool | Diffbot API |
| --- | --- |
| Web search | `GET https://llm.diffbot.com/api/v1/web_search` (bearer token) |
| Extract page | `GET https://api.diffbot.com/v3/{analyze\|article\|product\|discussion\|image\|video\|list\|event}` (`token` query parameter) |
| Search organizations | `POST https://kg.diffbot.com/kg/v3/dql` |
| Search people | same DQL endpoint, public professional profiles only |
| Search news | same DQL endpoint, newest publication date first via `sortBy:date` |
| Start crawl | `GET https://api.diffbot.com/v3/crawl` (create only; returns a job name) |
| Crawl jobs | list / status / results / **delete (destructive)** on `/v3/crawl` and `/v3/crawl/data` |
| Resolve entities | `POST https://nl.diffbot.com/v1/` |

Saving the credential checks `GET https://api.diffbot.com/v4/account?days=1`. Get a free token at [app.diffbot.com/get-started](https://app.diffbot.com/get-started).

Raw DQL, ontology lookup, Ask, places, and deals are not in this version. See SUBMISSION.md for why.

All HTTP goes through the [Diffbot Python SDK](https://github.com/diffbot/diffbot-python) (`diffbot.Diffbot`), behind a transport that refuses private, loopback, and cloud-metadata hosts.

## Run the tests

Python 3.12+:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt   # dify_plugin, pytest, and the local SDK checkout
pytest -q
```

The plugin imports the `diffbot` SDK, which is not released at the needed version yet (3.2.0, then 3.3.0). `diffbot/requirements.txt` therefore pins only `dify_plugin==0.11.0` and carries a TODO for the `diffbot` pin. `requirements-dev.txt` installs the local, unpushed SDK checkout editable (`-e /workspace/diffbot-python`); edit that path if your checkout lives elsewhere.

The tests serve every request from `httpx.MockTransport` and make no Diffbot calls. The wiring tests run against the SDK as installed and against a copy with the 3.3.0 methods removed, which covers the plugin's `client.request()` fallbacks (`verify_token`, `crawl_download`, extract options).

GitHub CI (`.github/workflows/test.yml`) cannot see the local path. Until `diffbot` is released it does not install the SDK, and `tests/conftest.py` skips the SDK-dependent modules (the DQL and URL-policy tests still run). The TODOs in both files say what to delete after release.

## Package

Install the Dify plugin CLI from [langgenius/dify-plugin-daemon](https://github.com/langgenius/dify-plugin-daemon) and run from the repository root:

```bash
dify plugin package ./diffbot -o dist/diffbot-0.1.0.difypkg
dify plugin checksum dist/diffbot-0.1.0.difypkg
```

`dist/` is ignored by git. The package is unsigned; Dify signs marketplace builds after review. Self-hosted Dify rejects unsigned local installs unless an administrator trusts a signature or turns off verification. Signing commands are in `diffbot/README.md`. Never commit a private key.

Marketplace validation is `validator/validate-difypkg.py` from [langgenius/dify-marketplace-toolkit](https://github.com/langgenius/dify-marketplace-toolkit). The last result is recorded in SUBMISSION.md.
