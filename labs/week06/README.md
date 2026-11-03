# Week 06 — Sentiment Analysis Pipeline

Lab: analyze product reviews with an LLM, route each review by sentiment,
summarize the results, and log both the reviews and the dashboard to n8n
Data Tables.

## Files

| File | What it is |
|---|---|
| `sentiment-analysis-pipeline.json` | The workflow, exported from n8n. Import it with **Workflows → Import from File**, or paste it into the editor. |
| `../../build_sentiment_workflow.py` | Regenerates the workflow JSON (prints to stdout). |

## Workflow

14 nodes, on the CIS 91 n8n server (`https://n8n-cis091.codislabs.club`).

```
Manual Trigger → Test Reviews (5 reviews)
                     ↓
                Analyze Sentiment (Basic LLM Chain)
                  ├── OpenRouter Chat Model (deepseek/deepseek-v4.1-flash-1017, temp 0)
                  └── Structured Output Parser (sentiment/confidence/key_emotion/summary)
                     ↓
                Combine Results (one item at a time)
                     ↓
                Route by Sentiment
        positive ──→ Positive Action ─┐
        negative ──→ Negative Action ─┼→ Combine All (append, 3 inputs)
        fallback ──→ Neutral Action ──┘        │
                                              ├→ Log Reviews (TH Reviews)
                                              └→ Generate Dashboard
                                                       ↓
                                                 Log Dashboard (TH Sentiment Dashboard)
```

| Node | Type | Config |
|---|---|---|
| Test Reviews | Code | Five sample reviews (R001–R005) |
| Analyze Sentiment | Basic LLM Chain | Prompt includes `{{ $json.product }}` and `{{ $json.review_text }}` |
| OpenRouter Chat Model | Chat Model | `deepseek/deepseek-v4.1-flash-1017`, temperature `0`, credential `TH OpenRouter` |
| Structured Output Parser | Output Parser | Enforces `sentiment`, `confidence`, `key_emotion`, `summary`; parsed object lands in `$json.output` |
| Combine Results | Code | **Run Once for Each Item**; merges `$json.output` with `$('Test Reviews').item.json` |
| Route by Sentiment | Switch | `positive` → output 1, `negative` → output 2, fallback → `Neutral/Mixed` |
| Positive / Negative / Neutral Action | Edit Fields (Set) | Add `action`, `priority`, `follow_up`; **Include Other Input Fields** on |
| Combine All | Merge | Append, 3 inputs |
| Generate Dashboard | Code | Counts by sentiment, average confidence, escalations |
| Log Reviews | Data Table | Insert row → `TH Reviews`, Map Automatically |
| Log Dashboard | Data Table | Insert row → `TH Sentiment Dashboard`, Map Automatically |

## Data Tables

Column names match the Code/Set node output character-for-character, so
*Map Automatically* works.

| Table | ID | Columns |
|---|---|---|
| `TH Reviews` | `cqVgQuZLhRuWOCni` | `review_id`, `product`, `reviewer`, `review_text`, `date`, `sentiment`, `confidence`, `key_emotion`, `ai_summary`, `action`, `priority`, `follow_up` |
| `TH Sentiment Dashboard` | `oJJ3m9PSYzfXt7LH` | `report_title`, `generated_at`, `total_reviews`, `positive_count`, `positive_pct`, `negative_count`, `negative_pct`, `neutral_count`, `neutral_pct`, `average_confidence`, `escalations_needed` |

`Insert row` appends, so each run adds five rows to `TH Reviews` and one row to
`TH Sentiment Dashboard`.

## Latest run (execution 2007)

| review | sentiment | confidence | emotion | priority |
|---|---|---|---|---|
| R001 | positive | 0.99 | joy | low |
| R002 | negative | 0.99 | anger | high |
| R003 | neutral | 0.95 | indifference | medium |
| R004 | neutral | 0.65 | satisfaction | medium |
| R005 | positive | 1.0 | satisfaction | low |

Dashboard: 5 reviews, 2 positive (40%), 1 negative (20%), 2 neutral (40%),
average confidence 0.92, 1 escalation.

## Notes

- The prompt text starts with `=` in the exported JSON
  (`"text": "=Analyze the sentiment..."`). In n8n, a leading `=` is what turns
  the string into an expression, so `{{ $json.product }}` and
  `{{ $json.review_text }}` are interpolated. Without it the model receives the
  literal braces and reports that no review text was provided.
- No credentials are stored in this repo. The n8n API key is read from the
  `N8N_API_KEY` environment variable (see `AGENTS.md`) and sent as the
  `X-N8N-API-KEY` header. `sentiment-analysis-pipeline.json` contains node
  parameters, the credential ID/name, and Data Table IDs only.
- Workflow: https://n8n-cis091.codislabs.club/workflow/QJHHehgH3H7A7gDX
- Repository: https://github.com/thuynh073/cis91-automation-workflows
