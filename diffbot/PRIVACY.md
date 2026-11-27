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
| Plain text from the user, up to 20,000 characters, and an optional language code | `nl.diffbot.com` | Recognize and link named entities. |
| Plain text from the user, up to 20,000 characters, the requested result fields (entities, sentiment, facts, records, categories, sentences, language, summary), language, text format, document type, and summary length | `nl.diffbot.com` NLP | Analyze one document. Facts and records can restate personal data that appears in the text. |
| The question, an optional system prompt (each up to 8,000 characters), the answer format, and an optional JSON schema (up to 20 KB) | `llm.diffbot.com` Ask | Get an answer from Diffbot's LLM. The token is sent as a bearer header. The endpoint is not publicly documented. |
| A raw DQL query (up to 10,000 characters) and its options: type, columns, filters, export spec and separator, JSON mode, clustering, offset, and size | `kg.diffbot.com` DQL | Run any Knowledge Graph query a user or model writes. JSON and jsonl results are scrubbed of email, phone and html fields. csv, xls and xlsx export files are returned as Diffbot sent them and are **not** scrubbed. |
| Nothing from the user. No token or query is sent | `kg.diffbot.com` ontology | Download the public ontology document for the ontology tool and industry matching. The plugin keeps one copy in memory for 24 hours per Diffbot host. |
| Seed URLs, URL patterns and regular expressions, page process pattern, custom request headers, and per-subdomain limits | `api.diffbot.com` Crawl | Start a crawl job. Diffbot stores the settings with the job, and the crawler sends the headers to the crawled sites. Do not put secrets in headers or patterns. |
| An email address (`notify_email`) | `api.diffbot.com` Crawl | Diffbot emails that address about the crawl job. It is personal data. Only a workflow builder can set it, not the model. |
| A webhook URL (`notify_webhook`) | `api.diffbot.com` Crawl | Diffbot calls that URL when the job finishes. Do not put secrets in the URL. Only a workflow builder can set it. |
| The token and the number of days (1 to 366) | `api.diffbot.com` Account API | The Account usage tool reads plan, status and daily usage. The plugin returns only those; it never returns the token, child tokens, or the account email. |
| The token, and queries or text as above | A different Diffbot host, if the optional base URL fields are set | The advanced credential fields (`api_base`, `kg_base`, `llm_base`, `nlp_base`) can point at another host. Only https hosts on `diffbot.com` are accepted. Leave them blank for the defaults. |

The search tools do not offer parameters for email address, phone number, or IP address (the crawl notification email is the one exception, described above). If a Knowledge Graph or NLP response contains email or phone values, the plugin drops them from the JSON it returns. That includes raw DQL JSON and jsonl output. It does not apply to csv, xls and xlsx export files from the raw DQL tool, which are returned unfiltered. It also drops article HTML and, unless the news tool is asked for an excerpt, article body text.

People and organization results can still contain personal data that is already public on the web: names, job titles, employers, cities, countries, homepage URLs, and LinkedIn profile URLs. Diffbot describes people in its index as search subjects whose information was published on publicly available sites. News results can quote public articles. Entity resolution can identify people named in text the user pasted.

Do not send secrets, credentials, private messages, or data about children into these tools. The plugin cannot tell whether a Knowledge Graph profile refers to a minor.

## What Diffbot does with that data

Diffbot receives the token and the query content described above. Their privacy policy covers subscribers (API customers) and search subjects (people whose public web information is in the index). This plugin does not add a further recipient. It does not sell data and it has no separate subprocessors.

Diffbot's full policy is at [https://www.diffbot.com/company/privacy](https://www.diffbot.com/company/privacy). If it changes, this section will be updated in a new plugin version.

## What Dify can still retain

Chat and workflow logs in Dify may retain tool inputs and outputs under the workspace's own settings. That retention is Dify's, not an extra copy kept by this plugin. Administrators who need shorter retention should configure that in Dify.

## Contact

Questions about this plugin's handling of data, or requests about data held by Diffbot, can be sent to support@diffbot.com. Source code: https://github.com/diffbot/dify-diffbot.
