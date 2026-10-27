# Week 05 — Data Scraper & Formatter

Lab: build a data pipeline that scrapes [books.toscrape.com](https://books.toscrape.com),
cleans and transforms the data, analyzes it, and writes the results to n8n Data Tables.

## Files

| File | What it is |
|---|---|
| `data-scraper-formatter.json` | The workflow, exported from n8n. Import it with **Workflows → Import from File**, or paste it into the editor. |

## Workflow

12 nodes, targets the CIS 91 n8n server (`https://n8n-cis091.codislabs.club`).

```
Manual Trigger ─┐
                ├→ Fetch Bookstore → Extract Books → Split Out Books → Extract Book Fields
Schedule Trigger┘   (HTTP GET)       (20 x <article>)  (20 items)     (title/price/availability/rating)
                                                                              ↓
                                                                            Clean Book Data
                                                                              ↓
                                                                            Sort by Price (asc)
                                                                              ↓
                                                                            In Stock Only
                                                                    TRUE ─┬─→ Save Books (JH Books)
                                                                          └─→ Summary Statistics → Save Summary (JH Book Summary)
```

| Node | Type | Config |
|---|---|---|
| Fetch Bookstore | HTTP Request | GET `https://books.toscrape.com` |
| Extract Books | HTML | `article.product_pod`, return **HTML**, Return Array **on** → `books` |
| Split Out Books | Split Out | field `books` → 20 items, one per book |
| Extract Book Fields | HTML | from `books`: `h3 a`→attr `title`, `.price_color`→text, `.availability`→text, `p.star-rating`→attr `class` |
| Clean Book Data | Code | `£51.77`→`51.77`, `"In stock"`→`true`, `star-rating Three`→`3`, computes `value_score` |
| Sort by Price | Sort | `price` ascending |
| In Stock Only | If | `{{ $json.in_stock }}` is true; FALSE output discarded |
| Save Books | Data Table | Insert row → `JH Books`, Map Automatically |
| Summary Statistics | Code | totals, average, cheapest, most expensive, five-star count |
| Save Summary | Data Table | Insert row → `JH Book Summary`, Map Automatically |

## Data Tables

Both were created through the n8n API in the project `RgGwGSwNWEf8GjIf`.

| Table | ID | Columns |
|---|---|---|
| `JH Books` | `eM7tdvRtJAdaddvA` | `title` (string), `price` (number), `in_stock` (boolean), `stars` (number), `value_score` (number) |
| `JH Book Summary` | `rFZv7TUwAIUHlKtc` | `total_books`, `total_value`, `average_price` (number), `cheapest` (string), `cheapest_price` (number), `most_expensive` (string), `most_expensive_price` (number), `five_star_count` (number), `generated_at` (date) |

Column names match the Code node output character-for-character, so *Map Automatically* works.
`Insert row` appends, so each run adds 20 rows to `JH Books` and 1 to `JH Book Summary`.

## Scheduling

A `Schedule Trigger` (daily, 09:00) sits alongside the Manual Trigger. The workflow is left
**unpublished** — a schedule only fires after Publish/Activate.

## Notes

- No credentials are stored in this repo. The API key is read from the `N8N_API_KEY`
  environment variable (see `AGENTS.md`) and sent as the `X-N8N-API-KEY` header.
- `data-scraper-formatter.json` is safe to commit: it contains node parameters, CSS selectors
  and Data Table IDs only — no keys, no headers.
- Regenerate the upload payload from scratch with `../../build_workflow.py`.
