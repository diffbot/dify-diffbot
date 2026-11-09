# Privacy policy

This policy describes the Diffbot tool plugin for Dify. It covers the plugin itself. Dify's own handling of workspace data is described in the [Dify privacy policy](https://dify.ai/privacy). Diffbot's handling of API traffic is described in [Diffbot's privacy policy](https://www.diffbot.com/company/privacy) (page checked 9 November 2026; the page said it was last updated 29 August 2025). Terms of use are linked from that page.

## What the plugin stores

The plugin does not collect, store, or log an account of its own. It does not enable Dify persistent storage. It does not write files, set cookies, or send data to an analytics service run by the plugin.

The Diffbot token is saved by Dify as a plugin credential. This plugin reads that credential only to call Diffbot, and it removes the token from error text it returns.

## What is sent to Diffbot

Every tool call leaves the Dify workspace and is processed by Diffbot Technologies Corp. The destination depends on the tool:

| Data | Destination | Why |
| --- | --- | --- |
| Token, plus a one-day usage window during credential save | `api.diffbot.com` Account API | Check that the token is valid. The response includes account email and the token. The plugin does not return that body to the chat. |
| Search query, result count, snippet size | `llm.diffbot.com` Web Search | Run a web search. The token is sent as a bearer header. |
| Page URL and page type | `api.diffbot.com` Extract | Fetch and structure one public page. Diffbot retrieves the URL. |
| Names, homepages, categories, places, employee and revenue bounds, article phrases, publishers, dates | `kg.diffbot.com` DQL | Search the Knowledge Graph. |
| Person or organization name, public URL, location text, employer, title | `kg.diffbot.com` Enhance | Match a Knowledge Graph record. |
| Plain text from the user, up to 20,000 characters, and an optional language code | `nl.diffbot.com` | Recognize and link named entities. |

The plugin does not offer parameters for email address, phone number, or IP address, including on Enhance, where the Diffbot API supports those fields. If a Knowledge Graph response still contains email or phone values, the plugin drops them before returning the tool result. It also drops article HTML and, unless the news tool is asked for an excerpt, article body text.

People and organization results can still contain personal data that is already public on the web: names, job titles, employers, cities, countries, homepage URLs, and LinkedIn profile URLs. Diffbot describes people in its index as search subjects whose information was published on publicly available sites. News results can quote public articles. Entity resolution can identify people named in text the user pasted.

Do not send secrets, credentials, private messages, or data about children into these tools. The plugin cannot tell whether a Knowledge Graph profile refers to a minor.

## What Diffbot does with that data

Diffbot receives the token and the query content described above. Their privacy policy covers subscribers (API customers) and search subjects (people whose public web information is in the index). This plugin does not add a further recipient. It does not sell data and it has no separate subprocessors.

Review [https://www.diffbot.com/company/privacy](https://www.diffbot.com/company/privacy) before publishing this plugin, and replace this section if Diffbot's policy changes.

## What Dify can still retain

Chat and workflow logs in Dify may retain tool inputs and outputs under the workspace's own settings. That retention is Dify's, not an extra copy kept by this plugin. Administrators who need shorter retention should configure that in Dify.

## Contact

The publisher must list a monitored contact address in the plugin README before marketplace submission. Until that address is added, privacy questions about this prototype have no public inbox.
