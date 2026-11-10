#!/usr/bin/env python3
"""Build the midterm report: HTML evidence pages + screenshots + PDF.

Reads the real n8n execution/log output saved in ../results and the workflow
builder so the prompts and knowledge base in the report cannot drift from the
implemented workflow.
"""
from __future__ import annotations

import html
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent
MIDTERM = ROOT.parent
sys.path.insert(0, str(MIDTERM))
import build_midterm_workflow as bw  # noqa: E402

REPO_URL = "https://github.com/thuynh073/cis91-automation-workflows"
WORKFLOW_URL = "https://n8n-cis091.codislabs.club/workflow/clOIbUt0ShYirBXC"
WEBHOOK_URL = "https://n8n-cis091.codislabs.club/webhook/midterm-auto-responder"

TESTS = json.loads((MIDTERM / "results" / "official_tests.json").read_text())
LOG_ROWS = json.loads((MIDTERM / "results" / "log_rows.json").read_text())["data"]
LOG_ROWS.sort(key=lambda r: r["id"])

E = html.escape


def fmt_ts(value: str) -> str:
    if not value:
        return "—"
    return value.replace("T", " ").replace(".000Z", " UTC").replace("Z", " UTC")


def pct(value) -> str:
    return f"{float(value or 0) * 100:.0f}%"


# ---------------------------------------------------------------------------
# Shared CSS
# ---------------------------------------------------------------------------
CSS = """
:root { --ink:#17202a; --muted:#5b6b7c; --line:#d8e0e8; --brand:#c2410c;
        --brand2:#0f766e; --bg:#eef2f6; --card:#ffffff; --ok:#15803d; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
       font-family:"Segoe UI", Arial, Helvetica, sans-serif; font-size:13px; }
.page { width:1200px; margin:0 auto; padding:28px 34px 40px; background:var(--card); }
h1 { font-size:30px; margin:0 0 4px; letter-spacing:-.4px; }
h2 { font-size:19px; margin:24px 0 8px; padding-bottom:5px;
     border-bottom:2px solid var(--brand); }
h3 { font-size:14px; margin:14px 0 6px; }
p { line-height:1.45; margin:6px 0; }
a { color:var(--brand2); }
.small { font-size:11px; color:var(--muted); }
.mono { font-family:Consolas, "DejaVu Sans Mono", monospace; }
.links { background:#fff7ed; border:1px solid #fdba74; border-left:5px solid var(--brand);
         padding:12px 16px; margin:14px 0 18px; }
.links div { margin:4px 0; font-size:12.5px; }
.badge { display:inline-block; padding:2px 9px; border-radius:999px; font-size:11px;
         font-weight:700; letter-spacing:.3px; }
.pass { background:#dcfce7; color:var(--ok); border:1px solid #86efac; }
.warn { background:#fef3c7; color:#92400e; border:1px solid #fcd34d; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
.card { border:1px solid var(--line); border-radius:10px; padding:13px 15px;
        background:#fff; }
.card h3 { margin:0 0 8px; font-size:12px; text-transform:uppercase;
           letter-spacing:.7px; color:var(--brand); }
.kv { display:grid; grid-template-columns:120px 1fr; gap:3px 10px; font-size:12px; }
.kv dt { color:var(--muted); }
.kv dd { margin:0; }
.message { background:#f8fafc; border:1px solid var(--line); border-radius:8px;
           padding:10px 12px; font-size:12.5px; line-height:1.45; white-space:pre-wrap; }
table { width:100%; border-collapse:collapse; font-size:11.5px; }
th { text-align:left; background:#1f2937; color:#fff; padding:5px 7px; font-weight:600; }
td { padding:5px 7px; border-bottom:1px solid var(--line); vertical-align:top; }
tr:nth-child(even) td { background:#f8fafc; }
.prompt { background:#0f172a; color:#e2e8f0; border-radius:8px; padding:9px 11px;
          font-family:Consolas, "DejaVu Sans Mono", monospace; font-size:9.0px;
          line-height:1.24; white-space:pre-wrap; }
.stats { display:grid; grid-template-columns:repeat(5,1fr); gap:9px; margin:12px 0 2px; }
.stat { border:1px solid var(--line); border-radius:8px; padding:7px 8px; text-align:center;
        background:#f8fafc; }
.stat b { display:block; font-size:18px; color:var(--brand); line-height:1.1; }
.stat span { font-size:9.5px; color:var(--muted); }
.kbgrid { display:grid; grid-template-columns:1fr 1fr; gap:4px 20px; font-size:9.6px; margin-top:8px; }
.kbrow { border-bottom:1px solid #e5e7eb; padding:3px 0; line-height:1.3; }
.kbrow b { color:var(--brand); }
.kbrow span { color:var(--muted); font-size:8.2px; text-transform:uppercase;
              letter-spacing:.4px; margin-left:4px; }
.bar { height:9px; background:#e2e8f0; border-radius:99px; overflow:hidden; }
.bar > span { display:block; height:100%; background:var(--brand2); }
.flow { display:flex; flex-direction:column; align-items:center; gap:6px; margin:8px 0 4px; }
.frow { display:flex; align-items:center; justify-content:center; gap:8px; }
.node { border:2px solid #334155; border-radius:9px; padding:7px 12px; background:#fff;
        min-width:150px; text-align:center; font-size:11px; font-weight:700; }
.node small { display:block; font-weight:400; color:var(--muted); font-size:9.5px; }
.node.trigger { border-color:var(--brand); background:#fff7ed; }
.node.ai { border-color:var(--brand2); background:#ecfdf5; }
.node.log { border-color:#7c3aed; background:#f5f3ff; }
.node.err { border-color:#dc2626; background:#fef2f2; }
.arrow { color:#64748b; font-size:22px; line-height:1; }
.arrow.down { transform:rotate(90deg); }
.branchlabel { font-size:10px; color:var(--muted); }
.callout { background:#f1f5f9; border-left:4px solid #64748b; padding:9px 13px;
           margin:10px 0; font-size:12px; }
.section { page-break-before:always; }
.testhead { display:flex; justify-content:space-between; align-items:flex-end;
            border-bottom:3px solid var(--brand); padding-bottom:8px; margin-bottom:14px; }
.testhead .t { font-size:23px; font-weight:800; }
.testhead .s { color:var(--muted); font-size:12px; }
ul { margin:5px 0 5px 18px; padding:0; }
li { margin:2px 0; line-height:1.4; }
"""


def shell(title: str, body: str) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{E(title)}</title><style>{CSS}</style></head><body>{body}</body></html>"""


# ---------------------------------------------------------------------------
# Workflow diagram page
# ---------------------------------------------------------------------------
def workflow_page() -> str:
    body = f"""<div class="page">
<h1>Workflow Architecture</h1>
<p class="small">AI-Powered Auto-Responder · exported workflow <span class="mono">midterm/ai-auto-responder.json</span></p>
<div class="flow">
  <div class="frow"><div class="node trigger">Incoming Message Webhook<small>POST /webhook/midterm-auto-responder</small></div>
    <span class="arrow">→</span><div class="node">Normalize Message<small>Code · validate + metadata</small></div>
    <span class="arrow">→</span><div class="node">Valid Message?<small>IF</small></div></div>
  <div class="frow"><span class="branchlabel">invalid ↙</span><span style="width:560px"></span><span class="branchlabel">valid ↘</span></div>
  <div class="frow"><div class="node err">Respond Invalid Input<small>HTTP 400 JSON</small></div>
    <span style="width:120px"></span>
    <div class="node ai">Classify Message<small>LLM + structured parser · temp 0</small></div></div>
  <div class="frow"><span class="arrow down">→</span></div>
  <div class="frow"><div class="node">Search Knowledge Base<small>Code · 12 entries · top 3</small></div></div>
  <div class="frow"><span class="arrow down">→</span></div>
  <div class="frow"><div class="node ai">Generate Response<small>LLM + structured parser · temp 0.4</small></div></div>
  <div class="frow"><span class="arrow down">→</span></div>
  <div class="frow"><div class="node">Assemble Reply<small>Code · fallback + timing</small></div></div>
  <div class="frow"><span class="branchlabel">↙ delivery</span><span style="width:180px"></span><span class="branchlabel">logging ↘</span></div>
  <div class="frow"><div class="node">Respond With Reply<small>HTTP 200 JSON</small></div>
    <span style="width:60px"></span><div class="node log">Prepare Log Row → Log Interaction<small>Data Table · TH Interaction Log</small></div></div>
</div>
<div class="callout" style="margin-top:16px"><b>Error handling:</b> malformed input exits through the IF branch with HTTP 400; both LLM
chains retry twice and continue with a regular output on failure; the assembly step replaces an empty
LLM reply with a safe escalation message.</div>
</div>"""
    return shell("Workflow Architecture", body)


# ---------------------------------------------------------------------------
# Log table page
# ---------------------------------------------------------------------------
def log_page() -> str:
    rows = ""
    for r in LOG_ROWS:
        rows += (
            "<tr>"
            f"<td>{r['id']}</td><td class='small'>{E(fmt_ts(r.get('timestamp')))}</td>"
            f"<td>{E(r.get('sender') or '')}</td><td>{E(r.get('subject') or '')}</td>"
            f"<td><b>{E(r.get('category') or '')}</b></td><td>{pct(r.get('confidence'))}</td>"
            f"<td>{E(r.get('kb_match_ids') or '—')}</td><td>{E(r.get('kb_used_ids') or '—')}</td>"
            f"<td>{E(r.get('kb_match_type') or '')}</td>"
            f"<td>{'YES' if r.get('escalation_needed') else 'no'}</td>"
            f"<td>{E(r.get('delivery_status') or '')}</td>"
            f"<td>{r.get('response_time_ms') or 0} ms</td>"
            "</tr>"
        )
    body = f"""<div class="page">
<h1>Interaction Log — TH Interaction Log</h1>
<p class="small">Live n8n Data Table contents after the five official tests. Data read through the n8n Public API.</p>
<table>
<tr><th>ID</th><th>Timestamp</th><th>Sender</th><th>Subject</th><th>Category</th><th>Conf.</th>
<th>KB matched</th><th>KB used</th><th>Match</th><th>Escalated</th><th>Delivery</th><th>Time</th></tr>
{rows}
</table>
<div class="callout">Every row also stores the original message, the AI reasoning, the complete generated
response, and the reply subject. Those long fields are shown in each test's evidence page rather than
repeated here.</div>
</div>"""
    return shell("Interaction Log", body)


# ---------------------------------------------------------------------------
# Test evidence pages
# ---------------------------------------------------------------------------
TEST_META = [
    {
        "kind": "Direct match",
        "verdict": "PASS — correct answer, no escalation",
        "description": (
            "The message asks exactly how to connect to the campus VPN from a laptop. Triage labeled it "
            "<b>faq</b> (0.82) because the intent is a how-to, even though KB-01 is tagged technical_support. "
            "Search matched KB-01 (0.96), KB-02 (0.72), and KB-12 (0.63); the generated reply used KB-01 and "
            "included GlobalProtect, software.codis.edu/vpn, the vpn.codis.edu gateway, and the Duo prompt. "
            "The answer is accurate and complete."
        ),
    },
    {
        "kind": "Partial match",
        "verdict": "PASS — correct answer, escalated for urgency",
        "description": (
            "There is no exact VPN question; the sender describes phone internet in the library. Search still "
            "matched KB-02 at 1.00 through internet/phone/library/network, with KB-04 and KB-07 as weaker "
            "candidates. The reply used KB-02 and gave the CODID-Students and CODID-Guest instructions. It also "
            "set escalation_needed=true because the class starts in ten minutes, which is the right call."
        ),
    },
    {
        "kind": "No match",
        "verdict": "PASS — no invented answer, routed to a specialist",
        "description": (
            "Weather in Paris and a USD-to-EUR conversion are outside the knowledge base. Triage returned "
            "<b>general_inquiry</b> (0.80); the search returned zero entries. The model stated plainly that it "
            "cannot access live forecasts or exchange rates, did not invent data, and routed the message to a "
            "specialist with escalation_needed=true."
        ),
    },
    {
        "kind": "Short message",
        "verdict": "PASS — correct content; category is ambiguous",
        "description": (
            "The terse message 'Password reset?' was classified <b>technical_support</b> (0.55). Search matched "
            "KB-03 (0.86), KB-05 (0.59), and KB-08 (0.54), and the reply used KB-03. The reply gives the reset "
            "URL, the 12-character rule, and the five-minute propagation window. The content is correct, but the "
            "category could reasonably be faq; the low confidence reflects that ambiguity."
        ),
    },
    {
        "kind": "Long message",
        "verdict": "PASS — all three KB topics addressed, urgent items escalated",
        "description": (
            "The multi-paragraph message covers a week-three drop and charge, a portal login error, a Friday "
            "transcript deadline, and free software. Triage chose <b>billing</b> (0.55) because the refund is the "
            "first and most specific concern. Search matched KB-07, KB-08, and KB-11 at 0.98–1.00, and the reply "
            "used all three: the 50% week-three refund, transcript ordering, and the free software list. It "
            "escalated the portal error and the Friday deadline. A single category cannot represent all four "
            "topics, which is a documented limitation."
        ),
    },
]


def test_page(idx: int, rec: dict) -> str:
    meta = TEST_META[idx - 1]
    inp = rec["input"]
    cls = rec["classification"]
    kb = rec["kb"]
    resp = rec["response"]
    log = rec["log_row"]
    matches = kb.get("matches") or []
    match_rows = "".join(
        f"<tr><td><b>{E(m['id'])}</b></td><td>{m['score']:.2f}</td>"
        f"<td>{E(m['question'])}</td>"
        f"<td>{'used' if m['id'] in (rec['assembled'].get('kb_used_ids') or '') else 'candidate'}</td></tr>"
        for m in matches
    ) or "<tr><td colspan='4' class='small'>No knowledge base entry matched this message.</td></tr>"

    body = f"""<div class="page">
<div class="testhead">
  <div><div class="t">Test {idx} — {E(meta['kind'])}</div>
  <div class="s">Execution {E(str(rec['execution_id']))} · {E(fmt_ts(rec['started_at']))}</div></div>
  <span class="badge pass">{E(meta['verdict'])}</span>
</div>
<div class="grid2">
  <div>
    <div class="card"><h3>1 · Input message</h3>
      <dl class="kv"><dt>Sender</dt><dd>{E(inp['sender'])}</dd>
      <dt>Subject</dt><dd>{E(inp['subject'])}</dd>
      <dt>Message ID</dt><dd class="mono">{E(inp['message_id'])}</dd></dl>
      <div class="message" style="margin-top:8px">{E(inp['original_message'])}</div>
    </div>
    <div class="card" style="margin-top:14px"><h3>2 · AI classification</h3>
      <dl class="kv"><dt>Category</dt><dd><b>{E(cls['category'])}</b></dd>
      <dt>Confidence</dt><dd>{pct(cls['confidence'])}
        <div class="bar"><span style="width:{float(cls['confidence'])*100:.0f}%"></span></div></dd>
      <dt>Keywords</dt><dd>{E(', '.join(cls.get('keywords') or []))}</dd></dl>
      <p style="margin-top:8px"><b>Reasoning:</b> {E(cls.get('reasoning') or '')}</p>
    </div>
    <div class="card" style="margin-top:14px"><h3>3 · Knowledge base matches</h3>
      <table><tr><th>ID</th><th>Score</th><th>Question</th><th>Role</th></tr>{match_rows}</table>
    </div>
  </div>
  <div>
    <div class="card"><h3>4 · Generated response</h3>
      <dl class="kv"><dt>Subject</dt><dd>{E(resp.get('subject') or '')}</dd>
      <dt>Tone</dt><dd>{E(resp.get('tone') or '')}</dd>
      <dt>Escalation</dt><dd>{'YES' if resp.get('escalation_needed') else 'no'}</dd>
      <dt>KB used</dt><dd>{E(', '.join(resp.get('used_kb_ids') or []) or '—')}</dd></dl>
      <div class="message" style="margin-top:8px">{E(resp.get('body') or '')}</div>
    </div>
    <div class="card" style="margin-top:14px"><h3>5 · Log entry (TH Interaction Log)</h3>
      <dl class="kv">
      <dt>Row ID</dt><dd>{log.get('id')}</dd>
      <dt>Timestamp</dt><dd>{E(fmt_ts(log.get('timestamp')))}</dd>
      <dt>Category</dt><dd>{E(log.get('category') or '')} · {pct(log.get('confidence'))}</dd>
      <dt>KB matched</dt><dd>{E(log.get('kb_match_ids') or '—')}</dd>
      <dt>KB used</dt><dd>{E(log.get('kb_used_ids') or '—')}</dd>
      <dt>Match type</dt><dd>{E(log.get('kb_match_type') or '')} (top {log.get('kb_match_score')})</dd>
      <dt>Delivery</dt><dd>{E(log.get('delivery_status') or '')} via {E(log.get('delivery_channel') or '')}</dd>
      <dt>Priority</dt><dd>{E(log.get('priority') or '')}</dd>
      <dt>Response time</dt><dd>{log.get('response_time_ms') or 0} ms</dd>
      <dt>Reply subject</dt><dd>{E(log.get('reply_subject') or '')}</dd>
      </dl>
      <p class="small" style="margin-top:8px">Original message, reasoning, AI response and response
      status are all stored in the same row.</p>
    </div>
  </div>
</div>
<div class="callout" style="margin-top:16px"><b>What happened:</b> {meta['description']}</div>
</div>"""
    return shell(f"Test {idx}", body)


# ---------------------------------------------------------------------------
# Main report
# ---------------------------------------------------------------------------
def docs_html() -> str:
    kb_rows = "".join(
        f"<div class='kbrow'><b>{E(e['id'])}</b> <span>{E(e['category'])}</span><br>{E(e['question'])}</div>"
        for e in bw.KB_ENTRIES
    )
    classify_prompt = E(bw.CLASSIFY_PROMPT.lstrip("="))
    respond_prompt = E(bw.RESPOND_PROMPT.lstrip("="))
    tests_overview = "".join(
        f"<tr><td>Test {i}</td><td>{E(TEST_META[i-1]['kind'])}</td>"
        f"<td>{E(r['input']['message_summary'][:95])}</td>"
        f"<td>{E(r['classification']['category'])} · {pct(r['classification']['confidence'])}</td>"
        f"<td>{E(r['log_row'].get('kb_match_ids') or 'none')}</td>"
        f"<td>{'yes' if r['log_row'].get('escalation_needed') else 'no'}</td>"
        f"<td>{E(r['log_row'].get('delivery_status') or '')}</td></tr>"
        for i, r in enumerate(TESTS.values(), 1)
    )
    doc = f"""<div class="page">
<h1>AI-Powered Auto-Responder</h1>
<p class="small">CIS 91 · Week 7 Midterm Project · Tat Thang Huynh (TH) · {E(fmt_ts(TESTS[list(TESTS)[0]]['started_at']))}</p>
<div class="links">
  <div><b>GitHub repository:</b> <span class="mono">{E(REPO_URL)}</span></div>
  <div><b>n8n workflow:</b> <span class="mono">{E(WORKFLOW_URL)}</span></div>
  <div><b>Production webhook:</b> <span class="mono">{E(WEBHOOK_URL)}</span></div>
</div>
<div class="stats">
  <div class="stat"><b>4</b><span>categories</span></div>
  <div class="stat"><b>12</b><span>knowledge base entries</span></div>
  <div class="stat"><b>15</b><span>workflow nodes</span></div>
  <div class="stat"><b>2</b><span>LLM calls per message</span></div>
  <div class="stat"><b>5/5</b><span>tests passed</span></div>
</div>

<h2>1. Purpose</h2>
<p>This system is an AI-powered auto-responder for a fictional campus IT help desk. A student or staff
member sends a JSON message containing a sender, subject, and message body. The workflow classifies the
message, retrieves relevant help desk knowledge, drafts a professional reply, returns that reply to the
caller, and records the complete interaction. It is intended for high-volume first-line questions about
VPN, Wi-Fi, passwords, MFA, the student portal, printing, software, tuition plans, refunds, transcripts,
and instructor contact.</p>
<p>The design goal is not to replace a human, but to answer documented questions immediately and route
anything ambiguous, urgent, or outside scope to a specialist with enough context to act.</p>

<h2>2. Architecture</h2>
<div class="callout"><b>Design choice:</b> a webhook trigger is the easiest surface to test and to connect
to a form, chat widget, or email parser later. Deterministic keyword retrieval was chosen over embeddings
because it needs no vector database, runs instantly, and every match can be explained in the log. The LLM
is used for language tasks (classification and drafting), not for deciding policy facts.</div>
<ol>
<li><b>Incoming Message Webhook</b> accepts <span class="mono">POST /webhook/midterm-auto-responder</span>.
The JSON body arrives under <span class="mono">body</span>.</li>
<li><b>Normalize Message</b> accepts <span class="mono">sender/from/email</span>,
<span class="mono">subject/topic</span>, and <span class="mono">message/body/text/content</span> aliases,
trims values, creates a message ID and timestamp, and validates that message text exists.</li>
<li><b>Valid Message?</b> sends empty or malformed input to <b>Respond Invalid Input</b> (HTTP 400 with a
JSON error). Valid input continues.</li>
<li><b>Classify Message</b> is a LangChain LLM chain with a structured output parser. It returns
<span class="mono">category</span>, <span class="mono">confidence</span>,
<span class="mono">keywords</span>, and <span class="mono">reasoning</span> at temperature 0.</li>
<li><b>Search Knowledge Base</b> is a Code node. It tokenizes the subject, body, and classifier keywords,
removes stopwords, applies a light stemmer, and scores all 12 entries with IDF-weighted term overlap.
Scores are saturated so a long message cannot win by length alone; the classifier's category adds a small
tie-break bonus. The top three entries above 0.28 are kept, and a context block is built for the LLM.</li>
<li><b>Generate Response</b> is a second LLM chain at temperature 0.4. It receives the original message,
the classification, and the KB context, and returns <span class="mono">subject</span>,
<span class="mono">body</span>, <span class="mono">used_kb_ids</span>,
<span class="mono">escalation_needed</span>, and <span class="mono">tone</span>.</li>
<li><b>Assemble Reply</b> applies a safe fallback if the model returned no body, calculates response time,
and builds both the caller-facing reply and the log row.</li>
<li><b>Respond With Reply</b> returns HTTP 200 JSON. In parallel, <b>Prepare Log Row</b> and
<b>Log Interaction</b> write the interaction to the <b>TH Interaction Log</b> Data Table.</li>
</ol>

<div class="section">
<h2 style="margin-top:0">2. Architecture — workflow figure</h2>
<img src="workflow.png" alt="Workflow architecture" style="width:100%; border:1px solid #d8e0e8; border-radius:8px">

<h2>3. Knowledge Base</h2>
<p>The theme is a <b>campus IT help desk</b>. The knowledge base contains <b>12 entries</b>, each with an
ID, category, canonical question, answer, and search keywords. Entries are embedded as a JSON array inside
the Search Knowledge Base Code node, so the workflow is self-contained and needs no external sheet.
Categories: technical_support (KB-01, 02, 04, 05, 10), faq (KB-03, 08, 09), billing (KB-06, 07), and
general_inquiry (KB-11, 12). Every entry also carries search keywords; the full objects are in the
workflow JSON.</p>
<div class="kbgrid">{kb_rows}</div>
</div>

<div class="section">
<h2 style="margin-top:0">4. AI Prompts</h2>
<h3>Classification prompt (temperature 0)</h3>
<div class="prompt">{classify_prompt}</div>
<h3>Response generation prompt (temperature 0.4)</h3>
<div class="prompt">{respond_prompt}</div>
<p><b>Prompt design choices.</b> The classification prompt defines each category with concrete examples
and tells the model to classify by the sender's primary goal, not by every topic mentioned. It asks for a
calibrated confidence (below 0.6 when two categories fit), 3–6 lowercase keywords for retrieval, and a
short reason that can be audited in the log. Temperature 0 makes repeated messages consistent.</p>
<p>The response prompt puts the sender's actual question first, supplies only the matched KB context, and
explicitly forbids inventing policies, prices, phone numbers, or deadlines. It forces a plain-text reply
under 140 words, one clear next step, and an explicit escalation flag for billing disputes, account
lockouts, lost devices, out-of-policy refunds, or deadlines within 48 hours. The no-match instruction is
what prevents the weather/currency test from producing a fabricated answer. Temperature 0.4 keeps the
wording natural without changing facts.</p>

<h2>5. Limitations</h2>
<ul>
<li><b>Lexical retrieval, not semantic.</b> A paraphrase that shares no vocabulary with an entry can be
missed. Embeddings/vector search would improve recall.</li>
<li><b>One label, and sometimes an ambiguous one.</b> The long test is classified billing even though it
also contains a portal outage, a transcript deadline, and a software question; the top-three KB context
compensates, but the category is lossy. "Password reset?" can be faq or technical_support, so the workflow
logs 0.55 confidence instead of pretending certainty.</li>
<li><b>No webhook authentication, rate limiting, or deduplication.</b> A production deployment needs a
shared secret or gateway, and should key log rows on a sender-provided message ID.</li>
<li><b>Delivery is webhook + Data Table only.</b> There is no SMTP/email send, no outbound retry queue, and
no acknowledgement beyond the HTTP response.</li>
<li><b>Limited knowledge base and retention.</b> 12 entries cover the demo topics only, and the Data Table
has no retention policy for message text that may contain personal data.</li>
<li><b>Latency, cost, and generic fallback.</b> Tests took roughly 6–15 seconds because each message makes
two LLM calls. If both retries fail, the caller gets a safe escalation message rather than a specific
answer, and no operator alert is sent.</li>
</ul>
</div>"""
    return doc


def tests_section() -> str:
    overview = "".join(
        f"<tr><td>Test {i}</td><td>{E(TEST_META[i-1]['kind'])}</td>"
        f"<td>{E(r['input']['message_summary'][:95])}</td>"
        f"<td>{E(r['classification']['category'])} · {pct(r['classification']['confidence'])}</td>"
        f"<td>{E(r['log_row'].get('kb_match_ids') or 'none')}</td>"
        f"<td>{'yes' if r['log_row'].get('escalation_needed') else 'no'}</td>"
        f"<td>{E(r['log_row'].get('delivery_status') or '')}</td></tr>"
        for i, r in enumerate(TESTS.values(), 1)
    )
    pages = ""
    for i, rec in enumerate(TESTS.values(), 1):
        pages += f"""<div class="section">
<div class="testhead"><div><div class="t">Test {i} — {E(TEST_META[i-1]['kind'])}</div>
<div class="s">Execution {E(str(rec['execution_id']))} · {E(fmt_ts(rec['started_at']))}</div></div>
<span class="badge pass">{E(TEST_META[i-1]['verdict'])}</span></div>
<img src="test-{i:02d}.png" alt="Test {i} evidence" style="width:100%; border:1px solid #d8e0e8; border-radius:8px">
<div class="callout"><b>What happened:</b> {TEST_META[i-1]['description']}</div>
</div>"""
    return f"""<div class="section">
<h1>Testing — Five Diverse Messages</h1>
<p>The five cases below were sent to the production webhook with <span class="mono">curl</span> and the
JSON files in <span class="mono">midterm/tests/</span>. Each evidence page is a screenshot of the captured
n8n execution: the input, classification, KB matches, generated reply, and the resulting interaction-log
row. All five executions returned HTTP 200 and logged with delivery status
<span class="mono">delivered</span>.</p>
<table><tr><th>Test</th><th>Type</th><th>Message (short)</th><th>Category · confidence</th>
<th>KB matched</th><th>Escalated</th><th>Delivery</th></tr>{overview}</table>
<img src="log.png" alt="TH Interaction Log" style="width:100%; margin-top:14px; border:1px solid #d8e0e8; border-radius:8px">
<p class="small">The screenshot above is the live TH Interaction Log after all five tests. The per-test
pages that follow show the full original message, reasoning and AI response stored in each row.</p>
</div>{pages}"""


def report_html() -> str:
    body = docs_html() + tests_section()
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>AI-Powered Auto-Responder — Midterm</title>
<style>{CSS}
@page {{ size: Letter; margin: 0.40in 0.5in; }}
@media print {{
  body {{ background:#fff; font-size:10.5px; }}
  .page {{ width:auto; padding:0; margin:0; }}
  .section {{ page-break-before:always; }}
  img {{ page-break-inside:avoid; }}
  .card, .callout, table, .prompt {{ page-break-inside:avoid; }}
  h2 {{ page-break-after:avoid; }}
  h3 {{ page-break-after:avoid; }}
  .prompt {{ font-size:7.3px; line-height:1.18; }}
  h2 {{ margin:14px 0 6px; }}
  h3 {{ margin:9px 0 4px; }}
  p {{ margin:4px 0; }}
  li {{ margin:1px 0; font-size:9.9px; line-height:1.3; }}
  .stats {{ margin:8px 0 0; }}
  .kbrow {{ padding:2px 0; }}
}}
</style></head><body>{body}</body></html>"""


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def chrome(args: list[str]) -> None:
    cmd = [
        "google-chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        "--allow-file-access-from-files",
        "--force-device-scale-factor=1",
        "--virtual-time-budget=2500",
        *args,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def screenshot(html_path: Path, png_path: Path, width: int, height: int) -> None:
    chrome([
        f"--window-size={width},{height}",
        f"--screenshot={png_path}",
        html_path.as_uri(),
    ])
    # Trim uniform background so the image has no dead space at the bottom.
    img = Image.open(png_path).convert("RGB")
    bg = Image.new("RGB", img.size, img.getpixel((0, 0)))
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    if bbox:
        left, top, right, bottom = bbox
        right = min(img.width, right + 24)
        bottom = min(img.height, bottom + 24)
        img.crop((0, 0, right, bottom)).save(png_path)
    print(f"  {png_path.name}: {Image.open(png_path).size}")


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)

    pages = {"workflow": (workflow_page(), 1240, 1500),
             "log": (log_page(), 1500, 1000)}
    for i, rec in enumerate(TESTS.values(), 1):
        pages[f"test-{i:02d}"] = (test_page(i, rec), 1240, 2050)

    for name, (content, _, _) in pages.items():
        (ROOT / f"{name}.html").write_text(content, encoding="utf-8")

    for name, (_, w, h) in pages.items():
        screenshot(ROOT / f"{name}.html", ROOT / f"{name}.png", w, h)

    report = report_html()
    (ROOT / "report.html").write_text(report, encoding="utf-8")
    pdf = MIDTERM / "AI-Auto-Responder-Midterm.pdf"
    chrome([
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf}",
        (ROOT / "report.html").as_uri(),
    ])
    print(f"PDF: {pdf} ({pdf.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
