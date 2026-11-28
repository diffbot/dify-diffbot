# Changelog

## [0.2.0] - 2026-11-27

Pins `diffbot==3.4.1` (exact).

### Added

- `kg_query`: raw DQL with count-only, `size` 0 to 100, offset, and the SDK's named options (`type`, `col`, `filter`, `filter_exclude`, `exportspec`, `exportseparator`, `jsonmode`, `non_canonical_facts`, `no_dedup_articles`, `cluster`, `format`). JSON and jsonl are scrubbed of `emails`, `phoneNumbers`, and `html` and capped at 200,000 characters (`truncated` flag). csv, xls and xlsx come back as files and are not scrubbed.
- `kg_ontology`: types, composites, enums, taxonomies, fields, taxonomy values, enum values, name search, and a raw ontology file. One in-memory copy per ontology URL, 24 hour TTL, stale copy served on a failed refresh, five minute back-off.
- `ask`: Diffbot's LLM with text (streamed), JSON, or JSON-schema output.
- `nlp`: single-document NLP with selectable fields, language, format, document type, and summary length.
- `account_usage`: plan, status and daily usage only. Never the token, child tokens, or email.
- Advanced credential fields `api_base`, `kg_base`, `llm_base`, `nlp_base`. https on `diffbot.com` hosts only.
- `search_web`: up to five queries.
- `search_organizations`, `search_people`, `search_news`: `count_only`. The organization `industry` is matched against the `OrganizationCategory` taxonomy, with suggestions on a miss.
- `extract`: the `job` page type and an optional Custom API name.
- `crawl_start`: `url_crawl_regex`, `url_process_regex`, `page_process_pattern`, per-subdomain limits, `notify_webhook`, `notify_email`, and multi-line `custom_headers`.

### Changed

- Crawl robots.txt, proxy and canonical settings are now three-way selects (`obey_robots_mode`, `use_proxies_mode`, `use_canonical_mode`): Diffbot default (parameter omitted), on, off (`0`). On SDK 3.4.1 an explicit `False` is sent as `0`, so the old boolean fields, which Dify saves as `false`, would have made existing nodes ignore robots.txt. The old field names are no longer read.
- Plugin version 0.2.0 (`manifest.yaml` and `pyproject.toml`). The memory limit stays at 64 MB.
- Marketplace validator results in SUBMISSION.md are for the 3.4.0 / 0.1.0 package and are stale until rerun on 0.2.0.

## Earlier, still plugin 0.1.0

- Removed the `client.request()` fallbacks in `diffbot/tools/sdk.py` for `verify_token`, `crawl_download`, and extract options, and the local response TypedDicts in `tools/sdk_types.py`. `diffbot==3.4.0` has all of them natively. No behavior change.
- Reran the marketplace validator on the rebuilt package; results are in SUBMISSION.md.

## [0.1.0] - 2026-11-17

Plugin version stays 0.1.0. It is not on the Dify Marketplace.

### Changed

- Pin `diffbot==3.4.0` in `diffbot/requirements.txt` and `diffbot/pyproject.toml`.
- Remove the editable `/workspace/diffbot-python` path from `requirements-dev.txt`.
- CI installs the pin from PyPI and runs the SDK-dependent tests (the skip in `tests/conftest.py` is gone).

This repo does not publish to npm or PyPI. Shipping is a Dify Marketplace pull request, which is separate from merging this branch. The feature-detect fallbacks in `diffbot/tools/sdk.py` were removed afterwards (see below).
