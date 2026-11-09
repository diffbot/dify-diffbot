# Diffbot plugin for Dify

Prototype of a Dify tool plugin that calls Diffbot. Nothing in this repository has been submitted to the Dify Marketplace, and no pull request was opened against `langgenius/dify-plugins`.

The installable plugin is `diffbot/`. Marketplace steps, review expectations, and open questions are in [SUBMISSION.md](SUBMISSION.md).

## What v1 implements

| Tool | Diffbot API |
| --- | --- |
| Web search | `GET https://llm.diffbot.com/api/v1/web_search` (bearer token) |
| Extract page | `GET https://api.diffbot.com/v3/{analyze\|article\|product\|discussion\|image\|video\|list\|event}` (`token` query parameter) |
| Search organizations | `GET https://kg.diffbot.com/kg/v3/dql` |
| Search people | same DQL endpoint, public professional profiles only |
| Search news | same DQL endpoint, newest publication date first via `revSortBy:date` |
| Enhance entity | `GET https://kg.diffbot.com/kg/v3/enhance` |
| Resolve entities | `POST https://nl.diffbot.com/v1/` |

Credential save checks `GET https://api.diffbot.com/v4/account?days=1`. There is no live token in this environment, so tests mock HTTP and do not show live Diffbot results.

Crawl, raw DQL, ontology lookup, places, and deals are left out of v1. See SUBMISSION.md for why.

## Run the tests

Python 3.12:

```bash
pip install -r diffbot/requirements.txt pytest
pytest
```

`diffbot/requirements.txt` pins `dify_plugin==0.11.0` and `requests==2.34.2`, which is the set these tests ran against.

## Package

Install the Dify plugin CLI from the [0.6.15 release](https://github.com/langgenius/dify-plugin-daemon/releases/tag/0.6.15) (`dify-plugin-linux-amd64` was used here) and from the repository root:

```bash
dify plugin package ./diffbot -o dist/diffbot-0.1.0.difypkg
dify plugin checksum dist/diffbot-0.1.0.difypkg
```

The unsigned package checked into `dist/` matches the last local build. Self-hosted Dify rejects unsigned local installs unless an administrator trusts a signature or changes verification. Signing commands are in `diffbot/README.md`. Do not commit the private key.

Marketplace validation, separate from `dify plugin package`, is `langgenius/dify-marketplace-toolkit` `validator/validate-difypkg.py`. The last run of that validator is recorded in SUBMISSION.md.
