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
| Knowledge Graph query | `POST https://kg.diffbot.com/kg/v3/dql` (raw DQL; JSON/jsonl scrubbed, csv/xls/xlsx exports not) |
| Knowledge Graph ontology | `GET https://kg.diffbot.com/kg/ontology` (no token; 24 h in-memory cache) |
| Ask Diffbot | `POST https://llm.diffbot.com/rag/v1/chat/completions` (bearer token; undocumented endpoint) |
| Natural language analysis | `POST https://nl.diffbot.com/v1/` |
| Account usage | `GET https://api.diffbot.com/v4/account` |

Saving the credential checks `GET https://api.diffbot.com/v4/account?days=1`. Get a free token at [app.diffbot.com/get-started](https://app.diffbot.com/get-started).

The plugin covers the `diffbot` 3.4.1 sync client. Enhance, Bulk Extract, Custom API management, crawl pause/restart, and the file-writing ontology refresh are not included. See SUBMISSION.md.

All HTTP goes through the [Diffbot Python SDK](https://github.com/diffbot/diffbot-python) (`diffbot.Diffbot`), behind a transport that refuses private, loopback, and cloud-metadata hosts.

## Run the tests

Python 3.12+:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt   # dify_plugin, pytest, and diffbot==3.4.1
pytest -q
```

`diffbot/requirements.txt` pins `diffbot==3.4.1`, which is on PyPI. `requirements-dev.txt` does not contain a machine-local path.

The tests serve every request from `httpx.MockTransport` and make no Diffbot calls. The wiring tests run against the pinned SDK (`diffbot==3.4.1`) and its native `verify_token`, `crawl_download`, and extract options.

GitHub CI (`.github/workflows/test.yml`) installs `diffbot/requirements.txt`, including `diffbot==3.4.1`, and runs the full suite.

## Release

The official package is built by CI, not by hand. `.github/workflows/release.yml` runs when a `vX.Y.Z` tag is pushed:

1. `verify`: the tag must equal `version` in `diffbot/manifest.yaml`, which must equal `[project] version` in `diffbot/pyproject.toml`, and `CHANGELOG.md` must have a `## [X.Y.Z]` section.
2. `gates`: the same offline `pytest -q` as `test.yml`.
3. `package`: `dify plugin package ./diffbot -o diffbot-X.Y.Z.difypkg` with a pinned, checksum-verified dify CLI (currently 0.6.15), plus size and content checks. The package is uploaded as the `difypkg` workflow artifact.
4. `github-release`: creates the GitHub Release for the tag with the CHANGELOG section as notes and the `.difypkg` attached. A version containing `-` (for example `0.2.1-rc.0`) is marked Pre-release and may reuse the base `## [0.2.1]` section.

To cut a release, bump `version` in `diffbot/manifest.yaml` and `diffbot/pyproject.toml` and add the `## [X.Y.Z] - YYYY-MM-DD` CHANGELOG section in a PR, merge it, then tag the merge commit and push the tag:

```bash
git fetch origin && git tag vX.Y.Z origin/main && git push origin vX.Y.Z
```

`gh workflow run release.yml --repo diffbot/dify-diffbot --ref <branch>` is a dry run: it runs verify, gates and package and uploads the `difypkg` artifact, and never creates a GitHub Release, even on a tag ref.

Dify's "Install plugin from GitHub" reads these Releases: enter `https://github.com/diffbot/dify-diffbot`, pick the version, and pick `diffbot-X.Y.Z.difypkg`.

The workflow does not sign the package and does not submit it to the Dify Marketplace. Marketplace submission is a separate manual step (SUBMISSION.md). Do not commit a `.difypkg` or attach a hand-built one to a Release.

## Package locally (development)

For local testing, install the Dify plugin CLI from [langgenius/dify-plugin-daemon](https://github.com/langgenius/dify-plugin-daemon) and run from the repository root:

```bash
dify plugin package ./diffbot -o dist/diffbot-0.2.0.difypkg
dify plugin checksum dist/diffbot-0.2.0.difypkg
```

`dist/` is ignored by git. The package is unsigned, whether built locally or by the release workflow; Dify signs marketplace builds after review. Self-hosted Dify rejects unsigned installs (local file or GitHub) unless an administrator trusts a signature or turns off verification. Signing commands are in `diffbot/README.md`. Never commit a private key.

Marketplace validation is `validator/validate-difypkg.py` from [langgenius/dify-marketplace-toolkit](https://github.com/langgenius/dify-marketplace-toolkit). The last result is recorded in SUBMISSION.md.
