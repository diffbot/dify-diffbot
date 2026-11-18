# Publishing the Diffbot plugin to the Dify Marketplace

This is the runbook for publishing the plugin from the Diffbot organization. The source is public at https://github.com/diffbot/dify-diffbot. The plugin described here is the `feat/sdk-3.x-wiring` branch: eight tools, including crawl, built on the `diffbot` Python SDK (pinned to `diffbot==3.4.0`) and httpx instead of `requests`. As of 17 November 2026 no pull request has been opened against `langgenius/dify-plugins`, and this version has not been installed in Dify Community Edition or Dify Cloud. It also has not been through the marketplace validator yet. `diffbot` 3.4.0 is not on PyPI yet, so a marketplace package still cannot be installed from the registry until that SDK release is up. Every validator result in this file that depends on that is marked `TODO(sdk-release): rerun marketplace validator`. The pre-SDK v0.1 results that used to be here no longer describe this package and have been removed.


Checked on 9 November 2026 against:

- [Tool plugin guide](https://docs.dify.ai/en/develop-plugin/dev-guides-and-walkthroughs/tool-plugin)
- [Manifest](https://docs.dify.ai/en/develop-plugin/features-and-specs/plugin-types/plugin-info-by-manifest)
- [Publish to the Marketplace](https://docs.dify.ai/en/develop-plugin/publishing/marketplace-listing/submit-plugin-to-marketplace)
- [Package as a local file](https://docs.dify.ai/en/develop-plugin/publishing/marketplace-listing/release-by-file)
- [Third-party signatures](https://docs.dify.ai/en/develop-plugin/publishing/standards/third-party-signature-verification)
- [Privacy guidelines](https://docs.dify.ai/en/develop-plugin/publishing/standards/privacy-protection-guidelines)
- [Plugin development guidelines](https://docs.dify.ai/en/develop-plugin/publishing/standards/contributor-covenant-code-of-conduct)
- [langgenius/dify-plugins submission requirements](https://github.com/langgenius/dify-plugins/blob/main/docs/plugin-submission-requirements.md) and [PR template](https://github.com/langgenius/dify-plugins/blob/main/.github/pull_request_template.md)
- Marketplace search API `POST https://marketplace.dify.ai/api/v1/plugins/search/advanced` and `POST https://marketplace.dify.ai/api/v1/plugins/batch`
- Diffbot docs at docs.diffbot.com and the public tool list in [diffbot/diffbot-mcp](https://github.com/diffbot/diffbot-mcp)


## Status before a PR

Done:

- Publisher: `author` in `manifest.yaml` and `provider/diffbot.yaml` is `diffbot`, matching the `diffbot` GitHub organization. The Marketplace docs say this has to match the GitHub handle that owns the listing.
- Public source: https://github.com/diffbot/dify-diffbot, linked from `manifest.yaml` `repo` and the plugin README.
- Contact: `support@diffbot.com` in `manifest.yaml`, the plugin README, PRIVACY.md, and the PR body.
- Icon: `_assets/icon.png` is the official 2026 Diffbot logomark, the green rounded-square tile (512×512 PNG).
- `meta.minimum_dify_version`: 1.14.0. The dify_plugin 0.11.0 README lists Dify 1.14.0 for SDK 0.8.1 and later. The plugin uses no later gated feature (OAuth, dynamic-select, multiple selects, reset_on_change).
- Unit tests: `pytest` reports 109 passed on 17 November 2026, with mocked HTTP, against `diffbot` 3.4.0. GitHub CI installs that pin from PyPI.

Still to do:

1. **Release `diffbot` 3.4.0 to PyPI.** The repo already pins `diffbot==3.4.0` in `diffbot/requirements.txt` and `diffbot/pyproject.toml`, and `requirements-dev.txt` no longer has an editable checkout path. Still delete the feature-detect fallbacks in `diffbot/tools/sdk.py` that 3.4.0 makes unnecessary (`verify_token`, `crawl_download`, extract options) before the marketplace pull request. Do not open that marketplace PR until the SDK is on PyPI and the validator has been rerun.
2. **TODO(sdk-release): rerun marketplace validator.** Repackage, record the new checksum, and run the toolkit validator with `--pr-body-file` and the OSV lookup. Fill in the "Local validation" and "Results for the current package" sections below with what it reports.
3. **Rerun the live smoke test, including crawl.** The 10 November 2026 live run was against the pre-SDK package and did not cover crawl. Run every tool against the real API, including `crawl_start` → `crawl_jobs` status → results → delete on a small job whose name is 30 characters or fewer.
4. Install the `.difypkg` on current Dify Community Edition and on Dify Cloud and record the version and result in the PR. The checklist asks for that test or a written limitation. Remote debugging (`python -m main` with a debug key from the Dify plugin page) is the quickest path.
5. **Update `diffbot/PRIVACY.md` for crawl.** Its "What is sent to Diffbot" table has no rows for seed URLs, crawl patterns, custom headers, or crawl results, and it does not say that crawl jobs and their data stay in the user's Diffbot account until someone deletes them. The privacy text has to match the package before submission.
7. Confirm that Diffbot is fine with its logo on the Dify Marketplace listing. Reviewers can ask for proof of the right to use a mark.
8. Have someone at Diffbot read `diffbot/PRIVACY.md` against the current Diffbot privacy policy and terms: user queries, page URLs, crawl seeds, and pasted text are sent to Diffbot, and organization, people, and news results can include personal data already on the public web.

## What the plugin is now

### Tools

`provider/diffbot.yaml` registers eight tools, one YAML and one Python file each under `diffbot/tools/`:

| Tool | Diffbot host | What it does |
| --- | --- | --- |
| `search_web` | llm.diffbot.com | Web search. 1 to 50 results (default 5), optional snippet length and token budget. A query that is only `url:<page>` returns the indexed copy of that page. |
| `extract` | api.diffbot.com | Diffbot fetches one public page and returns structured content (auto/analyze, article, product, discussion, image, video, list, event), as markdown or JSON, with optional Extract API options. |
| `search_organizations` | kg.diffbot.com | Knowledge Graph DQL built from typed fields: name, homepage, industry category, location, headcount and revenue bounds, public-company status. Up to 100 records. |
| `search_people` | kg.diffbot.com | Knowledge Graph search for people with a public professional presence, by name, employer, title, location. Up to 100 records. |
| `search_news` | kg.diffbot.com | Knowledge Graph article search by mentioned entity, phrase, publisher, language, and date, newest first. Up to 100 records. |
| `crawl_start` | api.diffbot.com (`/v3/crawl`) | Starts a background Diffbot crawl job on 1 to 20 public seed URLs and returns only the job name. |
| `crawl_jobs` | api.diffbot.com (`/v3/crawl`, `/v3/crawl/data`) | `list`, `status`, `results` (up to 1,000 rows, flagged when truncated), or `delete`. Delete is destructive. |
| `resolve_entities` | nl.diffbot.com | Finds entities in up to 20,000 characters of pasted text and links them to Knowledge Graph ids, with sentiment. |

The `enhance_entity` tool was removed (commit 7323b7b) so the tool set matches the Diffbot Python SDK surface. The plugin has no raw DQL tool.

### Crawl support

- **Background jobs.** `crawl_start` always calls the SDK with `watch=False` and returns as soon as Diffbot reports the job name. Polling would run past the plugin's 300-second call limit. The job keeps running on Diffbot after the Dify call returns, and it uses the account's crawl quota until it finishes or someone deletes it. The model is told to check `crawl_jobs` `status` and then fetch `results`.
- **Job names, 30 characters max.** Optional `job_name` may use letters, digits, `-`, `_`, and `.`, up to 30 characters. Leave it empty and Diffbot generates `crawl-<timestamp>`. The plugin checks the length itself because the crawler answers a longer name with HTTP 200 plus `errorCode` 505 and creates nothing.
- **Bounds.** Up to 20 seeds. `max_to_crawl` and `max_to_process` are 1 to 10,000 (default 100). `hops` is 0 to 10 (default 2). `restrict_domain` is on by default. `crawl_delay` is −1 to 3,600 seconds (−1 means the Diffbot default). Optional URL crawl and process patterns, `obey_robots` (form default off; see the robots.txt note under risks), `use_proxies` (default off), a custom request header, and an optional `api_url` for per-page extraction.
- **Delete is destructive.** `crawl_jobs` `delete` permanently removes the job and the data it collected. There is no undo. The tool, action label, and LLM description all say so, and the LLM description tells the model to delete only when the user explicitly asks. The plugin itself has no confirmation step, so an agent that ignores that instruction can still delete a job.
- **Account scope.** `list`, `status`, `results`, and `delete` work on every crawl job owned by the token's Diffbot account, including jobs made outside Dify. Nothing limits a Dify workspace to the jobs it started.
- **Results.** Up to 1,000 rows, string cells clipped to 500 characters. The plugin asks for one extra row so it can set `truncated`. `result_type: urls` returns the crawled-URL report (CSV, parsed to rows).

### Dependencies and transport

- `dify_plugin==0.11.0`.
- `diffbot==3.4.0`, the official Diffbot Python SDK. **Not pinned yet**: it goes into `requirements.txt` and `pyproject.toml` once 3.4.0 is on PyPI. Until then the tests run against a local editable checkout.
- `httpx` is the HTTP client. It comes in through the SDK (`httpx>=0.27.0`, along with the SDK's `click` and `rich`) and is not pinned directly by the plugin. `requests` is gone: it is no longer imported or listed, and the old `requests==2.34.2` pin was dropped.
- Every SDK call goes through `GuardedTransport` (`tools/sdk.py`). It is an httpx transport that refuses non-http(s) schemes and loopback, private, link-local, reserved, multicast, `localhost`, `*.local`/`*.internal`, and cloud-metadata hosts before a socket opens. The guard is always on; there is no credential to turn it off, and the plugin does not support self-hosted gateways or custom base URLs. It also honors `HTTP(S)_PROXY`/`ALL_PROXY`/`NO_PROXY` like the old `requests` client did, so proxied Dify deployments still work.
- Calls the SDK does not have yet go through the SDK's public `client.request()`, never its private attributes: token verification (`GET /v4/account?days=1`), crawl data download, and extract options. Each one feature-detects the native SDK method and uses it when present.
- The SDK sends the token as a `token` query parameter to api, kg, and nl.diffbot.com, and as `Authorization: Bearer` to llm.diffbot.com (Web Search). Errors are mapped to plugin-safe text and the token is redacted from them.

### Credential fields

From `provider/diffbot.yaml` `credentials_for_provider`:

| Field | Type | Required | Default | Purpose |
| --- | --- | --- | --- | --- |
| `diffbot_token` | secret-input | yes | none | Diffbot API token. Format-checked (16 to 256 characters of `A-Za-z0-9._~+-`) and verified with the Account API when the credential is saved. |
| `request_timeout` | text-input | no | `30` | Seconds per Diffbot call, 5 to 300. The 300 ceiling is dify_plugin's request limit. |

### Network domains

`manifest.yaml` `network.domains`, unchanged from v0.1:

- `api.diffbot.com` (Extract, Account, Crawl)
- `kg.diffbot.com` (Knowledge Graph DQL)
- `llm.diffbot.com` (Web Search)
- `nl.diffbot.com` (Natural Language)

The plugin process only talks to these four hosts. Neither credentials nor parameters can change the SDK base URLs. User-supplied URLs (extract `url`, crawl `seeds`, crawl `api_url`) go to Diffbot as parameters, and Diffbot's own infrastructure fetches them. The plugin does not.

## Package the file they will attach

From a checkout of the plugin, after `diffbot==3.4.0` is pinned, with the Dify plugin CLI (the v0.1 run used `dify-plugin-linux-amd64` 0.6.15; record the version you use):

```bash
dify plugin package ./diffbot -o dist/diffbot-0.1.0.difypkg
dify plugin checksum dist/diffbot-0.1.0.difypkg
python3 validator/validate-difypkg.py dist/diffbot-0.1.0.difypkg --output-dir ./validation-report
```

The validator lives in [langgenius/dify-marketplace-toolkit](https://github.com/langgenius/dify-marketplace-toolkit). Exit code 0 means no blocking package errors. Warnings still need an explanation in the PR. The PR body below has `TODO(sdk-release)` placeholders where the new run's summary goes.

`dify plugin package` produces an unsigned archive. Dify signs marketplace packages after merge. A third-party signature is only for Community Edition installs outside the marketplace:

```bash
dify signature generate -f your_key_pair
dify signature sign dist/diffbot-0.1.0.difypkg -p your_key_pair.private.pem -c community
dify signature verify dist/diffbot-0.1.0.signed.difypkg -p your_key_pair.public.pem
```

Keep the private key out of git. `dify signature verify` with no `-p` checks the Marketplace public key and will reject this package, which is expected before Dify signs it. Community Edition with `FORCE_VERIFYING_SIGNATURE=true` will also reject the unsigned file until an admin adds the matching public key. See the signature doc linked above.

## Pull request layout

Fork `langgenius/dify-plugins`, sync `main`, and branch. The current publishing guide wants exactly one new `.difypkg` in the PR. Suggested path:

```text
diffbot/diffbot/diffbot-0.1.0.difypkg
```

That is `<github-owner>/<plugin-name>/<plugin-name>-<version>.difypkg`. Owner, plugin name, and version must match `manifest.yaml` (`diffbot`, `diffbot`, `0.1.0`).

```bash
git clone https://github.com/<github-owner>/dify-plugins.git
cd dify-plugins
git remote add upstream https://github.com/langgenius/dify-plugins.git
git fetch upstream
git switch main
git merge --ff-only upstream/main
git switch -c add-diffbot-0.1.0
mkdir -p diffbot/diffbot
cp /path/to/diffbot-0.1.0.difypkg diffbot/diffbot/
git add diffbot/diffbot/diffbot-0.1.0.difypkg
git status --short
git diff --stat
git commit -m "add diffbot 0.1.0"
git push -u origin HEAD
```

Open the PR against `langgenius/dify-plugins:main`. Do not open it as a draft unless the package is unfinished. Do not open a second PR to fix review comments. Push to the same branch.

The repository README still says to commit plugin source next to the package. The current publish guide and the Exa resubmission (`langgenius/dify-plugins` #2692, merged 13 July 2026) say the opposite: CI must see one `.difypkg`, and source stays in the public repo linked from the manifest. Follow the current guide. If a reviewer asks for the source tree inside `dify-plugins`, add it only in the way they specify, in that same PR.

Later versions add a new file such as `diffbot/diffbot/diffbot-0.2.0.difypkg` and leave the old package in place unless a maintainer says to delete it. Bump `version` in `manifest.yaml`. Do not reuse `0.1.0`.

## PR body to paste

Fill this in from the live template. Keep every section. Check exactly one risk box: none, or more than one, gets the `risk: missing` label. Do not paste it as-is. Every `TODO(sdk-release)` line has to be replaced with real results first.

````markdown
# Plugin Submission

## Plugin information

- **Author**: diffbot
- **Plugin name**: diffbot
- **Version**: 0.1.0
- **Source repository**: https://github.com/diffbot/dify-diffbot
- **Contact**: support@diffbot.com

## Submission type

- [x] New plugin
- [ ] Version update

## What changed

New tool plugin for Diffbot, built on the official Diffbot Python SDK (`diffbot==3.4.0`). Eight tools:

- Web search on llm.diffbot.com
- Extract a page on api.diffbot.com (auto or a specific page type)
- Knowledge Graph search for organizations, people, and news
- Start a Diffbot crawl job, and list, check, fetch results of, or delete crawl jobs (delete is destructive)
- Resolve entities in pasted text to Knowledge Graph ids

Authentication is a Diffbot token (free at https://app.diffbot.com/get-started). The plugin calls the Account API to check the token when the credential is saved. One optional credential field sets the request timeout (5 to 300 seconds). The private-host guard is always on. The plugin has no raw DQL tool and takes no email, phone, or IP inputs.

## Risk level

- [ ] Low risk
- [ ] Medium risk
- [x] High risk

Extract and crawl both send user-supplied http(s) URLs to Diffbot, and Diffbot fetches them. A crawl follows links from up to 20 seeds, up to 10,000 pages, and keeps running in the background on the user's Diffbot account after the tool call returns. That falls under "proxy or crawl arbitrary URLs" in the high-risk definition. The crawl jobs tool can permanently delete a crawl job and its data. People search and entity resolution handle personal data from public profiles and from text the user pastes.

## Required checks

- [x] I have read and followed the [Marketplace submission requirements](https://github.com/langgenius/dify-plugins/blob/main/docs/plugin-submission-requirements.md).
- [x] I have read and comply with the [Plugin Development Guidelines](https://docs.dify.ai/en/develop-plugin/publishing/standards/contributor-covenant-code-of-conduct).
- [ ] I tested this plugin on Dify Community Edition and Dify Cloud, or documented any limitation below.
- [x] The package contains only files needed at runtime.
- [x] The package does not contain secrets, local credentials, `.env` files, `.git` directories, virtual environments, caches, logs, or IDE files.
- [x] The package does not contain executables or bundled binaries, or I explained why they are required below.
- [x] The plugin README includes setup steps, usage instructions, required APIs or credentials, connection requirements, and the source repository link.
- [x] The plugin includes `PRIVACY.md` or a hosted privacy policy, and `manifest.yaml` references it.
- [x] All user-facing text is primarily in English, with any localized README files following the [i18n guidance](https://docs.dify.ai/en/develop-plugin/features-and-specs/plugin-types/multilingual-readme).

<!-- Re-verify the package-content boxes against the rebuilt 3.4.0 package before submitting. -->

## Security and privacy notes

- Outbound hosts: the plugin process only calls api.diffbot.com, kg.diffbot.com, llm.diffbot.com, and nl.diffbot.com, through the Diffbot SDK over httpx. No credential or parameter changes those base URLs. A guarded httpx transport refuses non-http(s) schemes and private, loopback, link-local, and metadata hosts before connecting.
- User-supplied URLs: extract `url`, crawl `seeds`, and crawl `api_url` must be http(s), have no userinfo, be at most 2,048 characters, and not be a local name or a literal private, loopback, link-local, reserved, or metadata address. Bare domains get `https://`. The check is on the literal host only. The plugin does not resolve DNS, because Diffbot does the fetching from its own infrastructure.
- Crawling: crawl jobs run on Diffbot in the background and use the account's quota until they finish or are deleted. Limits: 20 seeds, 10,000 pages crawled and processed, 10 hops. The crawl stays on the seed domains by default. `obey_robots` is off in the form by default. When it is off the SDK leaves out `obeyRobots`, so the Diffbot crawler's own default applies. A custom request header can be set and is sent to the crawled sites, and the parameter text tells users not to put secrets there. Job names are at most 30 characters.
- Destructive action: `crawl_jobs` with `delete` permanently removes a crawl job and its collected data. The action is labeled destructive, and the model is told to delete only on an explicit user request. List, status, results, and delete cover every crawl job on the token's account, not only jobs started from Dify.
- Limits: each call has a configurable timeout of 5 to 300 seconds (default 30). Web search returns at most 50 results, and Knowledge Graph searches return at most 100 records. Crawl results return at most 1,000 rows with cells clipped to 500 characters. Entity resolution accepts up to 20,000 characters. Long text fields are clipped before they reach the model. Errors are rewritten so they never contain the token. Email and phone fields are removed from Knowledge Graph records.
- Personal data: people search and entity resolution process names, public profile fields, and location text. Neither tool accepts email, phone, or IP input. The Knowledge Graph cannot be filtered by age, so a public profile of a minor could come back. The privacy policy tells users not to send data about children.
- Financial data: organization search can return public revenue and headcount figures. The plugin does not move money.
- No command execution, code execution, shell, SQL against a customer database, SSH/SFTP, file operations, or browser automation.
- Queries, URLs, crawl settings, and pasted text go to Diffbot over HTTPS. The plugin stores none of it. Crawl jobs and their results are kept in the user's Diffbot account until deleted. See PRIVACY.md and https://www.diffbot.com/company/privacy.

## Local validation

```text
dify plugin package ./diffbot -o dist/diffbot-0.1.0.difypkg   # dify CLI <version>
dify plugin checksum dist/diffbot-0.1.0.difypkg
python3 validator/validate-difypkg.py dist/diffbot-0.1.0.difypkg --output-dir ./validation-report --pr-body-file pr-body.md
```

Checksum: TODO(sdk-release): rerun marketplace validator.

Validator: TODO(sdk-release): rerun marketplace validator. Report exit code, blocking failures, and each check, especially:
- dependency_vulnerabilities: expected pins are `dify_plugin==0.11.0` and `diffbot==3.4.0`. Record what OSV reports, including transitive `httpx`.
- access_domains: expected hosts are only api.diffbot.com, kg.diffbot.com, llm.diffbot.com, and nl.diffbot.com. The base URLs now sit inside the SDK, so record what the static scan actually finds.
- python_safety: record the result for the new SDK/httpx code (`tools/sdk.py`, crawl tools).

Unit tests: `pytest` 109 passed (mocked HTTP). Plugin start-up (`validator/test-plugin-install.py`, `INSTALL_METHOD=serverless`): TODO(sdk-release): rerun marketplace validator.

Live smoke test: TODO(sdk-release): rerun every tool, including a crawl start/status/results/delete cycle, against the Diffbot API with a real token.

## Reviewer notes

- Not yet installed on Dify Community Edition or Dify Cloud. Results from both will be added to this PR before it is marked ready for review.
- `meta.minimum_dify_version` is 1.14.0, taken from the dify_plugin 0.11.0 compatibility table (SDK 0.8.1 and later). The plugin uses no later gated feature.
- Crawl is asynchronous on purpose. A Dify tool call is capped at 300 seconds, so `crawl_start` returns a job name and the agent polls with `crawl_jobs`.
- Industry filter on organization search is an exact `categories.name`. Free text is not resolved through the ontology in this version.
- Job titles match profile text as written. `CEO` and `Chief Executive Officer` may return different people. The tool description tells the model to try both.
- The icon is Diffbot's own 2026 logomark, published by Diffbot.
````

Leave the "tested on Community Edition and Dify Cloud" box unchecked until that test has been done. Never check a box the package does not meet. Explain the gap under reviewer notes instead.

## What reviewers look for

From the submission requirements and the development guidelines:

- One `.difypkg`, runtime files only. No `.env`, `.git`, virtualenv, cache, logs, IDE files, or binaries.
- `manifest.yaml` author, name, version, type, runner, icon, privacy, repo, and contact agree with the README and the PR.
- English README with setup, credentials, usage, connection requirements, and a source link on an allowed forge (GitHub, GitLab.com, Bitbucket, Gitee, Codeberg, or git.sr.ht).
- `PRIVACY.md` (or a hosted policy) that says what is collected, stored, logged, or sent to third parties, including a link to Diffbot's policy. "We collect nothing" is only acceptable when it is true. It is not true here.
- `dify_plugin` at least 0.9.0, dependencies pinned, no git or raw URL installs. The validator queries OSV for known vulnerabilities.
- Declared `network.domains` matching the hosts the code calls.
- Exactly one risk level, and a higher level when two could apply. High-risk plugins get extra review. The sensitive-capability list in the template is part of that review.
- Unique name, behavior that matches the name, no Dify trademarks in the icon, no offensive content, no payment or asset-transfer features, and no duplicate of another plugin for the same API.
- A working support channel. Unmaintained plugins can be labeled and unpublished.

Automated CI runs when the PR is opened, updated, or marked ready. A green check is not approval. A blocking error is fixed on the same PR. A warning can still produce a change request. After merge, the repo validates again and uploads the package. The author does not upload the approved file separately.

There is no published review SLA. The guidelines say reviews aim to land in a reasonable window and that turnaround depends on volume and complexity. A low-risk Exa version update (`langgenius/dify-plugins` #2692) opened 12 July 2026 and merged 13 July 2026. That is one data point, not a forecast. A new high-risk plugin should expect a slower pass, especially if the icon, privacy text, or URL-fetch boundary needs a second look. The same Exa thread is a warning that a merged package is not the same as a marketplace listing: Exa reported an earlier package merged and never listed. After merge, check the Marketplace and Creator Center rather than assuming the listing exists.

When the listing is up, install counts and ratings show in Creator Center. To see them as an organization, the unique handle is the part of the plugin id before the slash (`diffbot` if the id is `diffbot/diffbot`). Claiming a plugin that was published from another GitHub account is a separate form and needs the original PR link.

## Comparable plugins

Install counts are from the public Marketplace API on 9 November 2026. They move.

| Plugin | Publisher | Version seen | Installs | Shape |
| --- | --- | --- | --- | --- |
| [Tavily](https://marketplace.dify.ai/plugin/langgenius/tavily) `langgenius/tavily` | langgenius | 0.1.13 | 461,993 | Search, extract, crawl, map, research. Official plugin under `tools/tavily` in `langgenius/dify-official-plugins`. |
| [Jina](https://marketplace.dify.ai/plugin/langgenius/jina_tool) `langgenius/jina_tool` | langgenius | 0.0.15 | 258,222 | Reader, search, tokenizer. |
| [Firecrawl](https://marketplace.dify.ai/plugin/langgenius/firecrawl) `langgenius/firecrawl` | langgenius | 0.2.4 | 214,482 | Search, scrape, crawl, map, monitors. |
| [Serper](https://marketplace.dify.ai/plugin/langgenius/serper) `langgenius/serper` | langgenius | 0.0.10 | 25,855 | Google SERP via Serper. Present. Smaller surface than Tavily. |
| [Exa](https://marketplace.dify.ai/plugin/yevanchen/exa) `yevanchen/exa` | yevanchen | 0.0.5 | 11,500 | Community search, contents, and answer-style tools. |
| `exa-labs/exa` and `exa-labs/exa_ai` | Exa Labs | not returned | not listed | A package was merged in `dify-plugins`. The batch API did not return either id on 9 November 2026. |
| Diffbot | none | none | 0 | Marketplace query `diffbot` returned total 0. |

Tavily, Firecrawl, Jina, and Serper are first-party `langgenius` plugins in `dify-official-plugins`, with `manifest.yaml`, `main.py`, `provider/*.yaml` plus `provider/*.py`, one YAML and one Python file per tool, `_assets/icon.svg`, and `requirements.txt` or `pyproject.toml`. This plugin follows that layout, with a PNG icon. Those official manifests often omit `privacy`, `repo`, and `contact`. The marketplace validator now requires all three, so this package includes them.

Brave (`langgenius/brave`, 29,817 installs, version 0.0.12) is another official search plugin, included only as a size comparison.

No Diffbot Dify plugin showed up in the Marketplace search, in the Diffbot GitHub organization repository list, or in public web search of `diffbot` plus `difypkg` / Dify. Diffbot already ships [diffbot-mcp](https://github.com/diffbot/diffbot-mcp), [diffbot-skills](https://github.com/diffbot/diffbot-skills), and the Python client. Those are not Dify packages. GitHub code search against `org:langgenius` returned 401 without a token, so that one index was not queried directly.

A third-party write-up of Marketplace tool installs on 16 October 2026 put Tavily, Jina, and Firecrawl in the same band (about 399k, 227k, and 204k). The 9 November API numbers above are higher and are the ones to cite.


## v1 tool choice

`diffbot-mcp` tools on 9 November 2026: `extract`, `search_web`, `crawl`, `resolve_entities`, `search_news`, `search_organizations`, `search_people`, `search_places`, `search_deals`, `dql`, `dql_probe`, `dql_ontology`. The October 2026 changelog removed MCP `enhance` in favor of `resolve_entities` plus the typed searches. This plugin dropped its `enhance_entity` tool for the same reason (commit 7323b7b), so it matches the Diffbot Python SDK surface.

v1 has what a Dify user expects from Tavily or Firecrawl: search, extract, and crawl. It adds the Knowledge Graph lookups that set Diffbot apart: organizations, people, news, and entity linking. There is no raw DQL tool, so a model cannot send an unbounded query. Crawl is in v1 because Tavily and Firecrawl both offer it. That decision moves the plugin into the "crawl arbitrary URLs" high-risk case. Places, deals, ontology browse, and hit-count probes can come in a later version once v1 has been installed for real.

The SDK handles authentication as the API docs describe. Extract, Account, Crawl, DQL, and Natural Language take `token` as a query parameter on `api.diffbot.com`, `kg.diffbot.com`, and `nl.diffbot.com`. Web Search on `llm.diffbot.com` uses `Authorization: Bearer`, so the token does not appear in that host's query string.

## Results for the current package

Unit tests, no network, 17 November 2026, against a local editable checkout of the unreleased SDK:

```text
pytest
109 passed
```

Package, checksum, archive size and file list: **TODO(sdk-release): rerun marketplace validator.** The package should hold the manifest, provider, eight tool YAML/Python pairs, the shared modules (`client.py`, `common.py`, `sdk.py`, `sdk_types.py`, `dql_builder.py`, `shape.py`), README, PRIVACY.md, icon, `main.py`, `requirements.txt`, and `pyproject.toml`. Check the real archive against that list. `.env.example` stays in git for remote debugging and `.difyignore` keeps it out of the package. `dist/` is not tracked in git.

Marketplace toolkit validator: **TODO(sdk-release): rerun marketplace validator.** The pre-SDK v0.1 numbers that used to be here (31 tests, checksum `6abed6eb…`, `requests==2.34.2` with no known vulnerabilities, a four-host access_domains scan of the plugin's own code, a python_safety pass) were measured on a different dependency set and code path. Do not reuse them. Record dependency_vulnerabilities, access_domains, python_safety, the PR-body checks, and the serverless start-up test from the new run.

Live smoke test: **TODO(sdk-release): rerun.** The 10 November 2026 run covered the pre-SDK package (credential check, web search, extract, organization, people, and news search, and entity resolution). It did not cover crawl. Two behaviors it settled are still in the code. News uses `sortBy:date` (newest first). People search groups employer and title as `employments.{employer.name:"..." title:"..."}` so both clauses must match the same job. Recheck both in the new run.

## Open questions and risks

Blockers before a real PR:

- `diffbot` 3.4.0 must be on PyPI and pinned, and the validator rerun on the resulting package. Until then the dependency, access-domain, and safety results are unknown.
- PRIVACY.md does not describe crawl yet.
- The package has not been installed in Dify Community Edition or Dify Cloud. Do that, or write the limitation in the PR.
- Whoever opens the PR must be allowed to publish under the `diffbot` author name. Open it from a fork owned by, or on behalf of, the `diffbot` organization.

Crawl scope and risk:

- Crawling user-supplied URLs is the main reason this plugin is high risk. An agent can start a crawl of any public site the user or the model names. The crawl follows links up to the configured limits and runs on Diffbot's infrastructure, against the user's own Diffbot account and quota. The plugin's URL guard stops literal private and metadata targets. It does not resolve hostnames, and it cannot judge whether the user is allowed to crawl a site. That depends on Diffbot's terms and the user's account.
- The `obey_robots` form field defaults to off. The SDK sends `obeyRobots=1` only when it is on. When it is off, nothing is sent and the Diffbot crawler's own robots.txt default applies, whatever that default is. So the toggle can say "off" while the crawler is still obeying robots.txt, or the reverse. Confirm the API default before release and make the label match it. A reviewer may also want robots.txt respected by default in a Dify-facing tool. That is a product call, and the change is a one-line YAML edit.
- Crawl jobs outlive the tool call. A user who starts a large crawl from an agent keeps using quota after the conversation ends, and the plugin has no cleanup. The tool text says the job runs in the background, and `crawl_jobs` can stop it with `delete`.
- `delete` is irreversible and has no confirmation step in the plugin. All that keeps a model from deleting is the LLM description ("only use delete when the user explicitly asks"). It also reaches every crawl job on the token's account, including jobs created outside Dify. If reviewers object, the options are to split delete into its own tool that users can leave disabled, or to limit delete to job names the plugin generated.
- The custom header parameter is sent to every crawled site. The parameter text warns against putting secrets there, but the plugin does not enforce that.

Product and API risks:

- Free tokens may not include Web Search, Knowledge Graph, Natural Language, and Crawl together. The Account API check can pass while a later call returns 401 or 403. No free-plan token has been tested.
- Organization industry is an exact category string. The MCP server resolves free text through the ontology. v1 returns nothing for "software" when the category is "Software Companies". Either document that clearly or add ontology resolution in a later version.
- Job-title abbreviations are not expanded (`CEO` versus `Chief Executive Officer`). The MCP server does expand them. The tool description tells the model to try both forms, but people search can still miss matches until expansion exists.

Review and policy risks:

- High risk is the honest box. Extract and crawl both have Diffbot fetch user-supplied URLs, and crawl is the plain "crawl arbitrary URLs" case. A reviewer can still ask for a narrower tool set. Dropping crawl would leave single-page Extract ("user-provided URLs") and people search (personal data), which is still at least medium. The written rule is to pick the higher label. Do not mark this low because Exa did: Exa's PR said it does not fetch arbitrary URLs, and this plugin does.
- Diffbot's privacy policy says the service is not directed at anyone 18 or under, and gives parents a contact address for privacy requests. The Knowledge Graph can still return a public profile of a younger person, and this plugin cannot filter by age. Raise that in review rather than claiming the plugin is age-safe.
- Dify Cloud customers will send workspace prompts and crawl targets to Diffbot. Whether that needs a DPA or a customer-facing subprocessors note is a question for Diffbot legal.
- A merged PR might not produce a listing. Watch the Marketplace after merge, as Exa had to.
- `meta.minimum_dify_version` is 1.14.0, taken from the SDK compatibility table rather than an install on 1.14.0. If the Community Edition test runs on a newer version and a reviewer asks, either test 1.14.0 or raise the floor to the tested version.

## Local install without the Marketplace

For an internal trial before review, use the unsigned package only on a Dify that is allowed to skip signature checks, or sign it with a key the plugin daemon trusts. Enter the token in the credential form. Do not put it in `.env`. Remote debugging is `python -m main` after copying `diffbot/.env.example` to `diffbot/.env` and filling the debug host and key from the Dify plugin page.
