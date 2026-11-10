# Diffbot

Search the public web and the Diffbot Knowledge Graph from a Dify agent or workflow.

Diffbot structures pages and keeps a knowledge graph of organizations, people, and articles. This plugin exposes a small v1 of that API: web search, page extraction, organization and people lookup, news search, entity enhancement, and named-entity resolution. A free token from [app.diffbot.com/get-started](https://app.diffbot.com/get-started) is enough to authenticate.

Published by Diffbot. Source: https://github.com/diffbot/dify-diffbot. Support: support@diffbot.com.

## Tools

| Tool | What it calls | Use it for |
| --- | --- | --- |
| Web search | `GET https://llm.diffbot.com/api/v1/web_search` | Ranked pages with a score, URL, date, and passage. A query that is only `url:https://...` reads the indexed copy. |
| Extract page | `GET https://api.diffbot.com/v3/analyze` or a typed extract path | Live extraction of one public page. `article` is the usual choice for news and blogs. |
| Search organizations | `GET https://kg.diffbot.com/kg/v3/dql` | Companies by name, homepage, category, headquarters, headcount, revenue, or public status. |
| Search people | same DQL endpoint | Public professional profiles by name, employer, title, or location. |
| Search news | same DQL endpoint | Articles by mentioned entity, phrase, publisher, language, or date. |
| Enhance entity | `GET https://kg.diffbot.com/kg/v3/enhance` | Best Knowledge Graph match for a person or organization from a name, URL, or employer. |
| Resolve entities | `POST https://nl.diffbot.com/v1/` | Names in a passage, linked to Knowledge Graph ids when Diffbot can match them. |

Crawl, raw DQL, ontology lookup, places, and deals are not in this version. Industry filters must already be exact category names such as `Software Companies`. The plugin does not resolve free text onto the taxonomy.

## Credentials

1. Create a token at [app.diffbot.com/get-started](https://app.diffbot.com/get-started).
2. In Dify, open Plugins, install this package, and choose Diffbot.
3. Paste the token into **Diffbot token**.

Dify stores the value as a secret. The plugin sends it only to the Diffbot hosts listed in `manifest.yaml`. Web Search uses `Authorization: Bearer`. The other calls use the `token` query parameter, which is how those APIs authenticate. Saving the credential calls `GET https://api.diffbot.com/v4/account` with `days=1` and does not show the account payload.

The token needs access to Extract, Web Search, Knowledge Graph, Enhance, and Natural Language. A free plan may not include every product. If a call returns an authorization error after the account check succeeds, confirm that product is enabled for the token.

## Use the tools

In an Agent, add the Diffbot tools and ask for a company, a news topic, or a URL. In a Workflow, add a tool node and pick one action. Required fields are marked on each tool. Limits are small on purpose: at most 10 search rows, 3 enhance matches, and 20,000 characters of text for entity resolution.

Extract accepts only `http` and `https` URLs. Localhost, link-local, and private literal addresses are rejected before the request is sent.

## Install the package locally

From the repository root, with the [Dify plugin CLI](https://github.com/langgenius/dify-plugin-daemon/releases) installed:

```bash
dify plugin package ./diffbot -o dist/diffbot-0.1.0.difypkg
```

In Dify, open Plugins and install the `.difypkg` from a local file. Self-hosted Dify verifies signatures by default. Either install on a server that trusts a key you control, or sign the file:

```bash
dify signature generate -f your_key_pair
dify signature sign dist/diffbot-0.1.0.difypkg -p your_key_pair.private.pem
dify signature verify dist/diffbot-0.1.0.signed.difypkg -p your_key_pair.public.pem
```

Keep the private key off this repository. Marketplace publication signs with Dify's key after review, so a third-party signature is only for Community Edition installs outside the marketplace. See [third-party signature verification](https://docs.dify.ai/en/develop-plugin/publishing/standards/third-party-signature-verification).

Remote debugging uses `.env.example`. Copy it to `.env`, fill in the debug host and key from Dify's plugin page, and run `python -m main` from this directory. Do not put the Diffbot token in `.env`.

## Connection requirements

Outbound HTTPS to:

- `api.diffbot.com`
- `kg.diffbot.com`
- `llm.diffbot.com`
- `nl.diffbot.com`

No database, filesystem, or browser is required. The plugin does not call any host other than those four.

## Source repository and support

- Source repository: https://github.com/diffbot/dify-diffbot
- Issues: https://github.com/diffbot/dify-diffbot/issues
- Support contact: support@diffbot.com

## Privacy

See [PRIVACY.md](PRIVACY.md). Queries, URLs, and passage text are sent to Diffbot. The plugin does not store them.
