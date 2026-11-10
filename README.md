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
| Search organizations | `GET https://kg.diffbot.com/kg/v3/dql` |
| Search people | same DQL endpoint, public professional profiles only |
| Search news | same DQL endpoint, newest publication date first via `sortBy:date` |
| Enhance entity | `GET https://kg.diffbot.com/kg/v3/enhance` |
| Resolve entities | `POST https://nl.diffbot.com/v1/` |

Saving the credential checks `GET https://api.diffbot.com/v4/account?days=1`. Get a free token at [app.diffbot.com/get-started](https://app.diffbot.com/get-started).

Crawl, raw DQL, ontology lookup, places, and deals are not in v0.1. See SUBMISSION.md for why.

## Run the tests

Python 3.12:

```bash
pip install -r diffbot/requirements.txt pytest
pytest
```

The tests mock HTTP and make no Diffbot calls. `diffbot/requirements.txt` pins `dify_plugin==0.11.0` and `requests==2.34.2`.

## Package

Install the Dify plugin CLI from [langgenius/dify-plugin-daemon](https://github.com/langgenius/dify-plugin-daemon) and run from the repository root:

```bash
dify plugin package ./diffbot -o dist/diffbot-0.1.0.difypkg
dify plugin checksum dist/diffbot-0.1.0.difypkg
```

`dist/` is ignored by git. The package is unsigned; Dify signs marketplace builds after review. Self-hosted Dify rejects unsigned local installs unless an administrator trusts a signature or turns off verification. Signing commands are in `diffbot/README.md`. Never commit a private key.

Marketplace validation is `validator/validate-difypkg.py` from [langgenius/dify-marketplace-toolkit](https://github.com/langgenius/dify-marketplace-toolkit). The last result is recorded in SUBMISSION.md.
