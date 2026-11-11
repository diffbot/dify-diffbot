# Publishing the Diffbot plugin to the Dify Marketplace

This is the runbook for publishing the plugin from the Diffbot organization. As of 10 November 2026 the source is public at https://github.com/diffbot/dify-diffbot and the package passes the marketplace validator, but no pull request has been opened against `langgenius/dify-plugins` and the package has not been installed in Dify Community Edition or Dify Cloud.

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
- Live API check: every tool was called against the real Diffbot API on 10 November 2026. Results are below.

Still to do:

1. Install the `.difypkg` on current Dify Community Edition and on Dify Cloud and record the version and result in the PR. The checklist asks for that test or a written limitation. Remote debugging (`python -m main` with a debug key from the Dify plugin page) is the quickest path.
2. Confirm that Diffbot is fine with its logo on the Dify Marketplace listing. Reviewers can ask for proof of the right to use a mark.
3. Have someone at Diffbot read `diffbot/PRIVACY.md` against the current Diffbot privacy policy and terms: user queries, page URLs, and pasted text are sent to Diffbot, and organization, people, and news results can include personal data already on the public web.

## Package the file they will attach

From a checkout of the plugin, with the Dify plugin CLI (this run used `dify-plugin-linux-amd64` 0.6.15):

```bash
dify plugin package ./diffbot -o dist/diffbot-0.1.0.difypkg
dify plugin checksum dist/diffbot-0.1.0.difypkg
python3 validator/validate-difypkg.py dist/diffbot-0.1.0.difypkg --output-dir ./validation-report
```

The validator lives in [langgenius/dify-marketplace-toolkit](https://github.com/langgenius/dify-marketplace-toolkit). Exit code 0 means no blocking package errors. Warnings still need an explanation in the PR. The PR body below already contains the summary for the current package.

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

Fill this from the live template. Do not delete sections. The risk box must be exactly one level. None or several becomes the `risk: missing` label.

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

New tool plugin for Diffbot. Seven tools:

- Web search on llm.diffbot.com
- Extract page on api.diffbot.com (auto or a specific page type)
- Knowledge Graph search for organizations, people, and news
- Enhance entity for one organization or person
- Resolve entities in pasted text to Knowledge Graph ids

Authentication is a Diffbot token (free at https://app.diffbot.com/get-started). Saving the credential calls the Account API. The plugin does not crawl, run raw DQL, or accept email, phone, or IP as inputs.

## Risk level

- [ ] Low risk
- [ ] Medium risk
- [x] High risk

Extract sends a user-supplied http(s) URL to Diffbot, which fetches that URL. People search, Enhance, and entity resolution handle personal data from public profiles and from text the user pastes (names, employers, locations, LinkedIn URLs). The submission rules say to pick the higher level when more than one could apply. Search-only peers have been accepted as low risk; this plugin does more than search, so it is marked high.

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

## Security and privacy notes

- Input constraints and security boundaries: outbound hosts are only api.diffbot.com, kg.diffbot.com, llm.diffbot.com, and nl.diffbot.com. The user cannot pass a raw URL for the plugin to request, and cannot pass raw DQL. Extract rejects non-http(s) URLs, URLs with userinfo, and literal local, private, or link-local hosts. Timeouts are 15 to 45 seconds. Result counts are capped (10 search rows, 3 enhance matches, 20,000 characters of text). Errors are rewritten so the token is not returned. Email and phone fields are dropped from Knowledge Graph records before they reach the model.
- Arbitrary URL fetching: Extract asks Diffbot to fetch one user-supplied public http(s) URL. The plugin itself only calls the four Diffbot hosts above. Scheme, userinfo, and literal private-host checks are described above.
- Personal data: People search, Enhance, and entity resolution process names, public profile fields, and location text. They do not accept email, phone, or IP input. Outputs drop email and phone if the API includes them. The Knowledge Graph cannot be filtered by age, so a public profile of a minor could be returned; the privacy policy tells users not to send data about children.
- Financial data: Organization search can return public revenue and headcount figures. It does not move money.
- No command execution, code execution, shell, SQL against a customer database, SSH/SFTP, file operations, or browser automation.
- Queries, URLs, and pasted text are sent to Diffbot over HTTPS. The plugin does not store them. See PRIVACY.md and https://www.diffbot.com/company/privacy.

## Local validation

```text
dify plugin package ./diffbot -o dist/diffbot-0.1.0.difypkg   # dify CLI 0.6.15
dify plugin checksum dist/diffbot-0.1.0.difypkg
python3 validator/validate-difypkg.py dist/diffbot-0.1.0.difypkg --output-dir ./validation-report --pr-body-file pr-body.md
```

Checksum `6abed6eb542446e656d598ed5bb98476cc2ec971a3254a7f295661ce10ca84a8`.

Validator: exit code 0, blocking failures 0. package_contents, package_secrets, package_binaries, manifest_metadata, readme_metadata, package_dependencies, python_compile, sensitive_capabilities: PASS. python_safety, prohibited_financial_activity: PASS. access_domains: static scan found only api.diffbot.com, kg.diffbot.com, llm.diffbot.com, nl.diffbot.com, matching `network.domains`. dependency_vulnerabilities: `dify_plugin==0.11.0` and `requests==2.34.2` pinned, no known vulnerabilities.

Unit tests: `pytest` 31 passed (mocked HTTP). Plugin start-up: `validator/test-plugin-install.py` with `INSTALL_METHOD=serverless` succeeded.

Live smoke test against the Diffbot API on 10 November 2026, calling each tool class directly with a real token: credential check, web search, extract, organization search, people search, news search (newest first), enhance, and entity resolution all returned results.

## Reviewer notes

- Not yet installed on Dify Community Edition or Dify Cloud. The tools were exercised live outside Dify, and the package passes the toolkit's start-up test. Results from a Community Edition and Dify Cloud install will be added to this PR before it is marked ready for review.
- `meta.minimum_dify_version` is 1.14.0, from the dify_plugin 0.11.0 compatibility table (SDK 0.8.1 and later). The plugin uses no later gated feature.
- Industry filter on organization search is an exact `categories.name`. Free text is not resolved through the ontology in this version.
- Job titles match profile text as written. `CEO` and `Chief Executive Officer` may return different people; the tool description tells the model to try both.
- The icon is Diffbot's own 2026 logomark, published by Diffbot.
````

Leave the "tested on Community Edition and Dify Cloud" box unchecked until that test exists. Do not check a box the package does not meet. Explain the gap under reviewer notes instead.

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

`diffbot-mcp` tools on 9 November 2026: `extract`, `search_web`, `crawl`, `resolve_entities`, `search_news`, `search_organizations`, `search_people`, `search_places`, `search_deals`, `dql`, `dql_probe`, `dql_ontology`. The October 2026 changelog removed MCP `enhance` in favor of `resolve_entities` plus the typed searches. The Enhance HTTP API is still documented at `https://kg.diffbot.com/kg/v3/enhance`.

v1 keeps the tools a Dify user already expects from Tavily or Firecrawl (search and extract) and adds the Knowledge Graph lookups that distinguish Diffbot (organizations, people, news, enhance, entity linking). It does not expose raw DQL, so a model cannot send an unbounded query. It does not start crawls, which are background jobs and a clearer "crawl arbitrary URLs" case. Places, deals, ontology browse, and hit-count probes can be a later version once v1 has been installed for real.

Authentication matches the docs, with one exception. Extract, Account, DQL, Enhance, and Natural Language take `token` as a query parameter on `api.diffbot.com`, `kg.diffbot.com`, and `nl.diffbot.com`. Web Search on `llm.diffbot.com` is documented with `Authorization: Bearer`, and the plugin does that so the token is not written into the query string for that host.

## Results for the current package

Unit tests, no network:

```text
pytest
31 passed
```

Dify CLI 0.6.15:

```text
dify plugin package ./diffbot -o dist/diffbot-0.1.0.difypkg
dify plugin checksum dist/diffbot-0.1.0.difypkg
# checksum 6abed6eb542446e656d598ed5bb98476cc2ec971a3254a7f295661ce10ca84a8
```

The archive is about 62 KB, 29 files: the manifest, provider, seven tool pairs, client code, README, PRIVACY.md, icon, `main.py`, `requirements.txt`, and `pyproject.toml`. `.env.example` is kept in git for remote debugging and excluded from the package by `.difyignore`. `dist/` is not tracked in git.

Marketplace toolkit validator, with `--pr-body-file` and the OSV lookup:

- Exit code 0. Blocking failures: 0.
- package_contents, package_secrets, package_binaries, manifest_metadata, readme_metadata, package_dependencies, python_compile, and sensitive_capabilities passed. python_safety and prohibited_financial_activity passed.
- access_domains: the static scan found only `api.diffbot.com`, `kg.diffbot.com`, `llm.diffbot.com`, and `nl.diffbot.com`, which are the `network.domains` entries.
- dependency_vulnerabilities: pinned `dify_plugin==0.11.0` and `requests==2.34.2` had no known vulnerabilities.
- `check-pr-body.py` and `check-pr-review-notes.py` passed on the PR body.
- `test-plugin-install.py` (`INSTALL_METHOD=serverless`) started the plugin and got a response on port 8080.

Live smoke test, 10 November 2026, each tool class called directly with a real token (not inside Dify):

```text
[PASS] credential check (2.8s): ok
[PASS] search_web (1.9s): text=Diffbot web search returned 3 result(s). 1. Knowledge Graph | Diffbot (score 0.992)    https://www.diffbot.com/products/knowledge-graph/    # Knowledge Graph  [](https://www.diffbot.com/products/knowl | json keys=['query', 'timeMs', 'results'] n=3 | first={"title": "Knowledge Graph | Diffbot", "date": null, "pageUrl": "https://www.diffbot.com/products/knowledge-graph/", "score": 0.992}
[PASS] extract (1.9s): text=Diffbot extract for https://www.diffbot.com/company/ About Diffbot | Diffbot (other) https://www.diffbot.com/company/about | json keys=['objects', 'humanLanguage', 'url', 'page_type'] n=1 | first={"title": "About Diffbot | Diffbot", "pageUrl": "https://www.diffbot.com/company/about", "type": "other"}
[PASS] search_organizations (1.5s): text=Organization search returned 2 record(s) of 4. 1. Diffbot — Menlo Park, United States    diffbot.com    American machine learning and knowledge management company 2. ROS Mobile Robots — Feldkirch, Aus | json keys=['dql', 'hits', 'returned', 'results'] n=2 | first={"name": "Diffbot", "diffbotUri": "http://diffbot.com/entity/EYX1i02YVPsuT7fPLUYgRhQ"}
[PASS] search_people (2.4s): employer "Diffbot" + title "CEO" -> 1 public profile (Diffbot's founder and CEO); grouped employments.{...} query
[PASS] search_news (2.1s): text=News search returned 3 article(s) of 3552, newest publication date first. 1. Windows-Sicherheit: Microsoft stuft Family-Safety-App als veraltet ein (WinFuture.de — d2026-11-10T19:07)    https://winfut | json keys=['dql', 'hits', 'returned', 'results'] n=3 | first={"title": "Windows-Sicherheit: Microsoft stuft Family-Safety-App als veraltet ein", "date": "d2026-11-10T19:07", "pageUrl": "https://winfuture.de/news,162580.html"}
[PASS] enhance_entity (2.0s): text=Enhance returned 1 organization match(es). 1. Diffbot (score 0.943500057890868)    diffbot.com    http://diffbot.com/entity/EYX1i02YVPsuT7fPLUYgRhQ | json keys=['hits', 'matches'] n=1 | first={"score": 0.943500057890868}
[PASS] resolve_entities (1.8s): text=Resolved 4 entities from the supplied text. - Mike Tung [person] id=ESGMaGV9uP0SuTmfPTtNEoA - Menlo Park [location, administrative area, city] id=EQiAUr370NpW1gvx-V4fTrQ - Diffbot [organization] id=EY | json keys=['sentiment', 'entities', 'dql_filter'] n=4
```

A live DQL check decided news ordering. `type:Article tags.label:"Microsoft" date>="2026-01-01"` with `sortBy:date` returned articles from 10 November 2026 first. With `revSortBy:date` it returned 1 January 2026 first. The plugin now uses `sortBy:date`.

People search with employer `Diffbot` and title `Chief Executive Officer` returned an executive assistant at another company, because separate `employments.*` clauses could match different jobs. The plugin now groups them as `employments.{employer.name:"..." title:"..."}`. Titles still match profile text as written: `CEO` finds Diffbot's founder and `Chief Executive Officer` does not.

## Open questions and risks

Blockers before a real PR:

- The package has not been installed in Dify Community Edition or Dify Cloud. Do that, or write the limitation in the PR.
- Whoever opens the PR must be allowed to publish under the `diffbot` author name. Open it from a fork owned by, or on behalf of, the `diffbot` organization.

Product and API risks:

- Free tokens may not include Web Search, Knowledge Graph, Enhance, and Natural Language together. The Account API can succeed while a later call returns 401 or 403. The 10 November live test used one Diffbot token with all of them enabled; a free-plan token has not been tried.
- Organization industry is an exact category string. The MCP server resolves free text through the ontology. v1 will return empty results for "software" when the category is "Software Companies". Either document that sharply or add ontology resolution in a later version.
- Job-title abbreviations are not expanded (`CEO` versus `Chief Executive Officer`). The MCP server does expand them. The tool description tells the model to try both forms, but people search can still under-count until expansion exists.
- Web Search might also accept `token` as a query parameter. This plugin uses only the documented bearer header. If a token type rejects the header, the tool fails closed. That is a live test, not a guess to code around.
- Enhance can spend more credits when `size` is above 1. The cap is 3. `refresh` and `search=true` are not exposed because they recrawl or do an extra web merge and are slow. Say that in support docs so customers do not expect them.

Review and policy risks:

- High risk is the honest box. A reviewer can still ask for a narrower tool set. Dropping Extract would remove user-supplied URL fetch, but people search would still be personal data. Dropping people, Enhance, and entity resolution would look more like Tavily and might be argued as medium, because the remaining URL fetch is still "user-provided URLs" in the medium definition and "proxy or crawl arbitrary URLs" in the high definition. The written rule is to choose the higher label. Do not mark this low because Exa did. Exa's PR text said it does not fetch arbitrary URLs. This plugin does ask Diffbot to fetch them.
- Diffbot's privacy policy says the service is not directed at anyone 18 or under, and gives parents a contact address for privacy requests. The Knowledge Graph can still return a public profile of a younger person, and this plugin cannot filter by age. Call that out in review rather than claiming the plugin is age-safe.
- Dify Cloud customers will send workspace prompts to Diffbot. Whether that needs a DPA or a customer-facing subprocessors note is a Diffbot legal question. The plugin policy links Diffbot's policy and says the plugin itself stores nothing. It does not answer the Dify customer's contract question.
- A merged PR might not produce a listing. Watch the Marketplace after merge, as Exa had to.
- `meta.minimum_dify_version` is 1.14.0, taken from the SDK compatibility table rather than an install on 1.14.0. If the Community Edition test runs on a newer version and a reviewer asks, either test 1.14.0 or raise the floor to the tested version.

## Local install without the Marketplace

For an internal trial before review, use the unsigned package only on a Dify that is allowed to skip signature checks, or sign it with a key the plugin daemon trusts. Enter the token in the credential form. Do not put it in `.env`. Remote debugging is `python -m main` after copying `diffbot/.env.example` to `diffbot/.env` and filling the debug host and key from the Dify plugin page.
