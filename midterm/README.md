# AI-Powered Auto-Responder — CIS 91 Midterm

An n8n workflow that receives a message, classifies it with an LLM, retrieves relevant
help-desk knowledge, drafts a grounded reply, returns it to the caller, and logs the
complete interaction.

**Author:** Tat Thang Huynh (TH)

## Links

- **GitHub repository:** https://github.com/thuynh073/cis91-automation-workflows
- **n8n workflow:** https://n8n-cis091.codislabs.club/workflow/clOIbUt0ShYirBXC
- **Production webhook:** `POST https://n8n-cis091.codislabs.club/webhook/midterm-auto-responder`
- **Submission PDF:** [`AI-Auto-Responder-Midterm.pdf`](AI-Auto-Responder-Midterm.pdf)

## What it does

1. **Intake** — a POST webhook accepts `sender`, `subject`, and `message`.
2. **Validation** — normalizes aliases (`from`, `email`, `topic`, `body`, `text`, `content`),
   creates a message ID/timestamp, and rejects empty messages with HTTP 400.
3. **Classification** — an LLM returns structured JSON with `category`, `confidence`,
   `keywords`, and `reasoning`. Categories: `faq`, `technical_support`, `billing`,
   `general_inquiry`.
4. **Knowledge base search** — a Code node searches 12 Q/A entries using stopword removal,
   light stemming, IDF-weighted term overlap, a category tie-break, and a 0.28 threshold.
   The top three matches become the LLM context.
5. **Response generation** — a second LLM writes a professional, grounded reply using only
   the matched knowledge, with an explicit escalation flag for urgent/out-of-scope cases.
6. **Delivery** — the reply is returned as HTTP 200 JSON by the Respond to Webhook node.
7. **Logging** — a parallel branch writes the full interaction to the **TH Interaction Log**
   n8n Data Table.

## Workflow files

| Path | Purpose |
|---|---|
| `ai-auto-responder.json` | Exported n8n workflow (15 nodes, connections, settings). |
| `build_midterm_workflow.py` | Reproducible builder that prints the workflow JSON. |
| `tests/*.json` | The five test payloads. |
| `results/*.response.json` | Raw webhook responses from the official test run. |
| `results/official_tests.json` | Compact execution evidence used in the report. |
| `results/log_rows.json` | Raw rows read from the live Data Table. |
| `executions/*.json` | Per-test n8n execution evidence (classification, KB, response, log row). |
| `report/build_report.py` | Generates the evidence screenshots and PDF. |
| `AI-Auto-Responder-Midterm.pdf` | Submission document (links, docs, test screenshots). |

## Knowledge base

Theme: **campus IT help desk**. The 12 entries live in the `Search Knowledge Base`
Code node, so the workflow has no external sheet dependency.

| Category | Entries |
|---|---|
| technical_support | KB-01 VPN, KB-02 Wi-Fi, KB-04 Duo/MFA, KB-05 portal/Canvas login, KB-10 lockout |
| faq | KB-03 password reset, KB-08 free software, KB-09 printing |
| billing | KB-06 payment plan, KB-07 drop/refund policy |
| general_inquiry | KB-11 official transcript, KB-12 instructor/office hours |

Each entry has `id`, `category`, `question`, `answer`, and `keywords`.

## API contract

Request:

```bash
curl -X POST "https://n8n-cis091.codislabs.club/webhook/midterm-auto-responder" \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "maria.lopez@student.codis.edu",
    "subject": "VPN help from off campus",
    "message": "How do I connect to the campus VPN from my laptop?"
  }'
```

Response (abridged):

```json
{
  "status": "ok",
  "message_id": "MSG-...",
  "category": "faq",
  "confidence": 0.82,
  "kb_matches": "KB-01, KB-02, KB-12",
  "kb_used": "KB-01",
  "escalation_needed": false,
  "reply": {
    "to": "maria.lopez@student.codis.edu",
    "subject": "Re: VPN help from off campus",
    "body": "...",
    "tone": "reassuring",
    "escalation_needed": false
  }
}
```

Invalid/empty messages return HTTP 400 with `{"status":"error", ...}`.

## Reproducing the workflow

Prerequisites in n8n:

- An OpenRouter credential named **TH OpenRouter**.
- A Data Table named **TH Interaction Log** with the columns listed below.

```bash
python3 midterm/build_midterm_workflow.py > midterm/ai-auto-responder.json
```

Import `midterm/ai-auto-responder.json` into n8n, select the OpenRouter credential, and
point the Log Interaction node at your own Data Table if the ID differs.

Data Table columns: `message_id`, `timestamp`, `sender`, `subject`, `message_summary`,
`original_message`, `category`, `confidence`, `reasoning`, `kb_match_ids`, `kb_used_ids`,
`kb_match_type`, `kb_match_score`, `ai_response`, `reply_subject`, `tone`,
`escalation_needed`, `priority`, `delivery_status`, `delivery_channel`, `response_time_ms`.

## Official test results

All five tests returned HTTP 200 and logged with `delivery_status = delivered`.

| Test | Type | Category · confidence | KB matched | KB used | Escalated |
|---|---|---|---|---|---|
| 1 | Direct match (VPN) | faq · 0.82 | KB-01, KB-02, KB-12 | KB-01 | no |
| 2 | Partial match (Wi-Fi) | technical_support · 0.92 | KB-02, KB-04, KB-07 | KB-02 | yes |
| 3 | No match (weather/FX) | general_inquiry · 0.80 | none | none | yes |
| 4 | Short ("Password reset?") | technical_support · 0.55 | KB-03, KB-05, KB-08 | KB-03 | no |
| 5 | Long multi-topic | billing · 0.55 | KB-07, KB-08, KB-11 | all three | yes |

See the PDF for the full input, classification reasoning, generated reply, and log entry
for every test.

## Design notes and limitations

- Retrieval is lexical (IDF-weighted keyword overlap), not embeddings. It is fast,
  deterministic, and explainable, but a paraphrase with no shared vocabulary can be missed.
- Classification is single-label; multi-topic messages rely on the top-three KB matches.
- Categories can be ambiguous: "Password reset?" can be `faq` or `technical_support`, so
  confidence is logged rather than hidden.
- The webhook has no authentication, rate limiting, or deduplication; production needs a
  shared secret/gateway and a sender-provided message ID.
- Delivery is webhook + Data Table only; there is no email send or retry queue.
- The 12-entry KB is a demo; the Data Table has no retention policy for message text.
- Each message makes two LLM calls (roughly 6–15 seconds in testing). If both retries fail,
  the caller receives a safe escalation message and no operator alert is sent.

## Model

OpenRouter `deepseek/deepseek-v4.1-flash-1017`. Classification runs at temperature 0;
response generation at temperature 0.4.
