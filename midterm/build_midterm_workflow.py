#!/usr/bin/env python3
"""Build the midterm 'AI-Powered Auto-Responder' workflow JSON (CIS 91).

Prints the workflow JSON to stdout. No secrets here: only the OpenRouter
credential ID and the interaction-log Data Table ID.

Usage:
    python3 build_midterm_workflow.py                       # placeholder table id
    python3 build_midterm_workflow.py --table-id abc123      # real Data Table id
    python3 midterm/build_midterm_workflow.py > midterm/ai-auto-responder.json
"""
import argparse
import json
import uuid

OPENROUTER_CRED_ID = "W9uBPl8BObqfpjkn"  # TH OpenRouter
OPENROUTER_CRED_NAME = "TH OpenRouter"
CLASSIFY_MODEL = "deepseek/deepseek-v4.1-flash-1017"
RESPOND_MODEL = "deepseek/deepseek-v4.1-flash-1017"

PLACEHOLDER_TABLE_ID = "YRpXfjz54bzN8k0P"
LOG_TABLE_NAME = "TH Interaction Log"

uid = lambda: str(uuid.uuid4())

CATEGORIES = ["faq", "technical_support", "billing", "general_inquiry"]

# --------------------------------------------------------------------------
# Node 2 — Normalize the webhook payload
# --------------------------------------------------------------------------
NORMALIZE_CODE = """// The Webhook node hands us the POSTed JSON under $json.body.
// Fall back to $json itself so "paste JSON into a Set node" tests still work.
try {
  const body = ($json && $json.body) ? $json.body : ($json || {});
  const asText = (v) => (v === undefined || v === null ? '' : String(v).trim());

  const sender =
    asText(body.sender) || asText(body.from) || asText(body.email) || 'unknown@sender';
  const subject = asText(body.subject) || asText(body.topic) || '(no subject)';
  // "message" is the documented field; accept a few aliases so the workflow
  // is forgiving about the shape of the incoming payload.
  const message =
    asText(body.message) || asText(body.body) || asText(body.text) || asText(body.content);

  return [{
    json: {
      message_id: 'MSG-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7),
      received_at: new Date().toISOString(),
      sender: sender,
      subject: subject,
      original_message: message,
      message_length: message.length,
      message_summary: message.slice(0, 160),
      valid: message.length > 0,
      validation_error: message.length > 0 ? '' : 'No message text found in the request body.',
      kb_matches: [],
      kb_match_ids: '',
      kb_match_type: 'none',
      kb_top_score: 0,
      kb_context: ''
    }
  }];
} catch (error) {
  // Never let a malformed payload throw: hand it to the reject branch instead.
  return [{
    json: {
      message_id: 'MSG-INVALID-' + Date.now(),
      received_at: new Date().toISOString(),
      sender: 'unknown@sender',
      subject: '(unreadable payload)',
      original_message: '',
      message_length: 0,
      message_summary: '',
      valid: false,
      validation_error: 'Could not read the request body: ' + error.message
    }
  }];
}"""

# --------------------------------------------------------------------------
# Node 4 — Classification chain
# --------------------------------------------------------------------------
CLASSIFY_PROMPT = """=You are the triage classifier for the CIS 91 Help Desk, which answers
questions from students and staff about campus IT, accounts, and billing.

Classify the message below into exactly ONE of these categories:

- faq: a general "how do I..." question that the help desk documents cover
  (printing, software availability, hours, common how-tos).
- technical_support: something is broken or unreachable for this user -
  VPN, campus Wi-Fi, logins, MFA, locked accounts, portal errors.
- billing: money matters - tuition, payment plans, refunds, charges, holds,
  late fees, receipts.
- general_inquiry: anything that is not IT or money - transcripts,
  enrollment questions, contacting an instructor, office hours, policies.

Sender: {{ $json.sender }}
Subject: {{ $json.subject }}
Message:
{{ $json.original_message }}

Rules:
- Choose the category that matches the sender's primary goal, even if they
  mention several topics.
- confidence is a number from 0.0 to 1.0 and must reflect genuine ambiguity.
  Use below 0.6 when the message could reasonably fit two categories.
- keywords: 3 to 6 single lowercase words taken from the message, used to
  search the help desk knowledge base.
- reasoning: one or two sentences explaining the choice."""

CLASSIFY_PARSER_EXAMPLE = json.dumps(
    {
        "category": "technical_support",
        "confidence": 0.93,
        "keywords": ["vpn", "connect", "laptop", "off-campus"],
        "reasoning": "The sender cannot connect to a documented campus service, which is a support issue rather than a billing or policy question.",
    },
    indent=2,
)

# --------------------------------------------------------------------------
# Node 5 — Knowledge base + search
# --------------------------------------------------------------------------
KB_ENTRIES = [
    {
        "id": "KB-01",
        "category": "technical_support",
        "question": "How do I connect to the campus VPN from my laptop?",
        "answer": "Install the GlobalProtect client from software.codis.edu/vpn, sign in with your campus username and password, and approve the Duo prompt. The gateway is vpn.codis.edu. Once connected the client shows \"Connected\" and you can reach library databases and lab servers from off campus.",
        "keywords": ["vpn", "globalprotect", "connect", "remote", "gateway", "off-campus", "tunnel"],
    },
    {
        "id": "KB-02",
        "category": "technical_support",
        "question": "Why can't I get on the campus Wi-Fi?",
        "answer": "Join the SSID CODID-Students with your campus username (not your email alias) and password. Forget the network first if it keeps failing, then rejoin. Guest access is SSID CODID-Guest, which is open for 24 hours and does not reach internal servers.",
        "keywords": ["wifi", "wi-fi", "wireless", "ssid", "network", "internet", "connect"],
    },
    {
        "id": "KB-03",
        "category": "faq",
        "question": "How do I reset my campus password?",
        "answer": "Go to accounts.codis.edu/reset, enter your campus username, confirm with Duo, and set a new password of at least 12 characters. Password changes propagate to Wi-Fi, VPN, and the portal within about 5 minutes.",
        "keywords": ["password", "reset", "forgot", "forgotten", "change", "credentials", "expired"],
    },
    {
        "id": "KB-04",
        "category": "technical_support",
        "question": "How do I set up Duo multi-factor authentication on a new phone?",
        "answer": "Open accounts.codis.edu/mfa, choose \"Add a device\", scan the QR code with the Duo Mobile app, and complete one test approval. Keep the old phone enrolled until the new one works. If you have lost both devices, bring photo ID to the Tech Desk in the library for a bypass code.",
        "keywords": ["duo", "mfa", "two-factor", "2fa", "phone", "authenticator", "enroll", "device"],
    },
    {
        "id": "KB-05",
        "category": "technical_support",
        "question": "The student portal or Canvas will not let me log in.",
        "answer": "First confirm the password at accounts.codis.edu/unlock, which clears lockouts after five failed attempts. If the password is accepted there but the portal still fails, clear the browser cache or try an incognito window, then open a ticket with the exact error text.",
        "keywords": ["portal", "canvas", "login", "log", "signin", "sign-in", "cached", "browser", "locked"],
    },
    {
        "id": "KB-06",
        "category": "billing",
        "question": "Does the college offer a tuition payment plan?",
        "answer": "Yes. Fall and spring tuition can be split into four interest-free installments through the Nelnet plan in the student portal under Finances > Payment Plans. The first installment is due at enrollment in the plan, and there is a $35 per-term setup fee.",
        "keywords": ["payment", "plan", "installment", "tuition", "nelnet", "pay", "split", "monthly"],
    },
    {
        "id": "KB-07",
        "category": "billing",
        "question": "What is the refund policy if I drop a class?",
        "answer": "A 100% refund applies through the end of the second week of the term, 50% through the fourth week, and no refund after that. Refunds go back to the original payment method within 10 business days. Dropping after the refund window still removes the charge only if the withdrawal is an approved medical or administrative withdrawal.",
        "keywords": ["refund", "drop", "withdraw", "withdrawal", "money", "back", "reimburse", "policy"],
    },
    {
        "id": "KB-08",
        "category": "faq",
        "question": "What software can students install for free?",
        "answer": "Students get Microsoft 365, the JetBrains suite, GitHub Student Developer Pack, and VMware through software.codis.edu. Log in with your campus account and download from the Student Software page. Adobe Creative Cloud is available only in the open labs, not for personal machines.",
        "keywords": ["software", "install", "free", "license", "microsoft", "office", "jetbrains", "adobe", "download"],
    },
    {
        "id": "KB-09",
        "category": "faq",
        "question": "How do I print on campus?",
        "answer": "Print from any lab machine or upload to print.codis.edu from your own laptop, then release the job at any printer with your student ID card. Each student gets $12.00 of printing credit per term; black and white pages cost $0.05 and color pages cost $0.25.",
        "keywords": ["print", "printing", "printer", "pages", "credit", "scan", "copy", "release"],
    },
    {
        "id": "KB-10",
        "category": "technical_support",
        "question": "My account is locked out after too many failed logins.",
        "answer": "Accounts lock for 30 minutes after five failed attempts. Self-service unlock is at accounts.codis.edu/unlock and takes effect immediately. If you are locked out during an exam or a timed deadline, call the Tech Desk at x4357 with your student ID and they can unlock the account manually.",
        "keywords": ["locked", "lockout", "failed", "attempts", "unlock", "blocked", "suspended", "account"],
    },
    {
        "id": "KB-11",
        "category": "general_inquiry",
        "question": "How do I request an official transcript?",
        "answer": "Order official transcripts through the National Student Clearinghouse link in the portal under Records > Transcripts. Electronic transcripts are $8 and usually arrive within one business day; paper transcripts are $12 and take 5 to 7 business days. Unofficial transcripts are free and instant from the same page.",
        "keywords": ["transcript", "official", "records", "order", "clearinghouse", "diploma", "grades"],
    },
    {
        "id": "KB-12",
        "category": "general_inquiry",
        "question": "How do I contact my instructor or find office hours?",
        "answer": "Office hours are on the syllabus and on the course page in Canvas. Email is the fastest route; use your campus address so it is not filtered. Instructors are expected to reply within two business days, and the department office can reach them if you have an urgent deadline issue.",
        "keywords": ["instructor", "professor", "teacher", "office", "hours", "email", "contact", "reach", "syllabus"],
    },
]

KB_JSON = json.dumps(KB_ENTRIES, indent=2)

SEARCH_CODE = """// ---------------------------------------------------------------------------
// Knowledge base: 12 Q/A entries covering all four categories.
// Edit this array to change the knowledge base; nothing else needs to change.
// ---------------------------------------------------------------------------
const KB = __KB_JSON__;

const STOPWORDS = new Set([
  'the','and','for','are','but','not','you','your','with','have','this','that','how',
  'can','get','from','was','were','when','what','why','does','did','will','would',
  'could','should','about','into','out','any','all','its','i','my','me','we','us',
  'our','to','of','in','on','at','is','be','do','as','if','or','so','up','an','a',
  'it','just','still','really','please','help','need','want','there','here','been',
  'also','got','one','two','like','know','sure','going','much','many','very','some',
  'them','they','then','than','now','new','im','id','dont','cant','thanks','hi'
]);

// Very light stemmer so "printing", "printed" and "print" all match and
// "dropped" matches "drop". Consistency matters more than linguistic accuracy.
const stem = (word) => {
  if (word.length <= 4) return word;
  let w = word;
  if (/ing$/.test(w)) w = w.slice(0, -3);
  else if (/ed$/.test(w)) w = w.slice(0, -2);
  else if (/(ss|us|is)$/.test(w)) return w;
  else if (/es$/.test(w)) w = w.slice(0, -2);
  else if (/s$/.test(w)) w = w.slice(0, -1);
  // "dropp" -> "drop", "runn" -> "run"
  return /([bdgklmnprt])\\1$/.test(w) ? w.slice(0, -1) : w;
};

const words = (text) =>
  [...new Set((String(text || '').toLowerCase().match(/[a-z0-9]+/g) || [])
    .filter((w) => w.length > 2 && !STOPWORDS.has(w))
    .map(stem))];

// Index the knowledge base once: which entries each term appears in. Terms that
// appear in only a few entries ("vpn", "password") carry more weight than
// generic ones ("campus"), the same idea as TF-IDF.
const vocab = new Map();
for (const entry of KB) {
  const terms = new Set([
    ...words(entry.question),
    ...entry.keywords.map((k) => stem(String(k).toLowerCase()))
  ]);
  for (const term of terms) {
    if (!vocab.has(term)) vocab.set(term, new Set());
    vocab.get(term).add(entry.id);
  }
}
const idf = (term) => {
  const df = vocab.has(term) ? vocab.get(term).size : 0;
  return df === 0 ? 0 : Math.log(KB.length / (1 + df));
};

// The classifier node only passes its own { output } object downstream, so
// recover the normalized message from the Normalize Message node.
const msg = $('Normalize Message').first().json;

// Search the subject plus the body, so "VPN" in the subject still counts.
// Read the classifier defensively: if the LLM failed, still search the KB.
let classification = {};
try {
  classification = $('Classify Message').first().json.output || {};
} catch (error) {
  classification = {};
}
const category = classification.category || 'general_inquiry';
const confidence = Number(classification.confidence) || 0;
const reasoning = classification.reasoning || '';
const classifierKeywords = Array.isArray(classification.keywords)
  ? classification.keywords.join(' ')
  : '';

const tokens = words(
  (msg.original_message || '') + ' ' +
  (msg.subject || '') + ' ' +
  classifierKeywords
);
const messageSet = new Set(tokens);

const scored = KB.map((entry) => {
  const entryTerms = new Set([
    ...words(entry.question),
    ...entry.keywords.map((k) => stem(String(k).toLowerCase()))
  ]);
  const matched = [...messageSet].filter((t) => entryTerms.has(t));
  // Saturating sum: one distinctive term already means a lot, extra terms add
  // less, so a long message cannot inflate its score by sheer length.
  const weightSum = matched.reduce((sum, t) => sum + idf(t), 0);
  let score = 1 - Math.exp(-weightSum / 1.8);
  if (entry.category === category) score = Math.min(score + 0.05, 1);
  return {
    id: entry.id,
    category: entry.category,
    question: entry.question,
    answer: entry.answer,
    matched_terms: matched,
    score: Math.round(Math.min(score, 1) * 100) / 100
  };
});

const THRESHOLD = 0.28;
const ranked = scored.sort((a, b) => b.score - a.score);
const matches = ranked.filter((entry) => entry.score >= THRESHOLD).slice(0, 3);
const topScore = matches.length ? matches[0].score : 0;

// strong = the message hits the distinctive vocabulary of an entry,
// partial = related to the topic but not an exact match,
// none = outside the knowledge base entirely.
const matchType = matches.length === 0 ? 'none' : topScore >= 0.65 ? 'strong' : 'partial';

const kbContext = matches.length === 0
  ? 'No knowledge base entry matched this message.'
  : matches.map((m) => '[' + m.id + '] (' + m.category + ', score ' + m.score + ')\\nQ: ' + m.question + '\\nA: ' + m.answer).join('\\n\\n');

return [{
  json: {
    ...msg,
    kb_matches: matches,
    kb_match_ids: matches.map((m) => m.id).join(', '),
    kb_match_count: matches.length,
    kb_top_score: topScore,
    kb_match_type: matchType,
    kb_context: kbContext,
    // Carry the classification forward so later nodes never have to reach
    // back into the LLM node's output (which may be empty on failure).
    classified_category: category,
    classified_confidence: confidence,
    classification_reasoning: reasoning
  }
}];"""

SEARCH_CODE = SEARCH_CODE.replace("__KB_JSON__", KB_JSON)

# --------------------------------------------------------------------------
# Node 7 — Response generation chain
# --------------------------------------------------------------------------
RESPOND_PROMPT = """=You are a support agent for the CIS 91 Help Desk replying to a student
or staff member. Write the actual reply that will be sent to them.

Incoming message
Sender: {{ $json.sender }}
Subject: {{ $json.subject }}
Category chosen by triage: {{ $json.classified_category }} (confidence {{ $json.classified_confidence }})
Message:
{{ $json.original_message }}

Knowledge base matches ({{ $json.kb_match_type }} match)
{{ $json.kb_context }}

How to write the reply:
- Answer the sender's actual question first, in the first sentence.
- When knowledge base entries are provided, use their concrete details only -
  never invent policies, prices, phone numbers, or deadlines that are not in
  the knowledge base.
- If the match is "none" or the question is not covered, say plainly that you
  do not have that information and that you are routing the message to a
  specialist, then set escalation_needed to true.
- Set escalation_needed to true for billing disputes, account lockouts,
  lost devices, refunds outside policy, or anything with a deadline in the
  next 48 hours.
- Keep the body under 140 words, professional and warm, plain text only (no
  markdown headings or bullet characters).
- End with one clear next step.

Return subject (a short reply subject line), body, used_kb_ids (the KB ids you
actually used, or an empty array), escalation_needed (true or false), and tone
(one word, e.g. reassuring, apologetic, neutral)."""

RESPOND_PARSER_EXAMPLE = json.dumps(
    {
        "subject": "Re: Connecting to the campus VPN",
        "body": "Hi, thanks for reaching out. To connect from off campus, install GlobalProtect from software.codis.edu/vpn and sign in with your campus username and password, then approve the Duo prompt. The gateway is vpn.codis.edu. Once the client shows Connected you can reach the library databases. If it still fails, reply with the error message and we will dig in.",
        "used_kb_ids": ["KB-01"],
        "escalation_needed": False,
        "tone": "reassuring",
    },
    indent=2,
)

# --------------------------------------------------------------------------
# Node 9 — Assemble the delivery payload + the log row
# --------------------------------------------------------------------------
ASSEMBLE_CODE = """const kb = $('Search Knowledge Base').item.json;
const reply = $json.output || {};

// Defensive defaults: if the response chain returned nothing usable, deliver a
// safe fallback instead of an empty reply, and flag it as escalated.
const fallbackBody =
  'Thanks for your message. I was not able to draft a confident answer, so I have ' +
  'routed it to a help desk specialist who will follow up within one business day.';

const body = (reply.body && String(reply.body).trim()) || fallbackBody;
const escalated = reply.escalation_needed === true || !reply.body;
const matchedIds = kb.kb_match_ids || '';
const usedIds = Array.isArray(reply.used_kb_ids) && reply.used_kb_ids.length
  ? reply.used_kb_ids.join(', ')
  : '';

const elapsed = Date.now() - Date.parse(kb.received_at);

return [{
  json: {
    // --- log row (column names match the TH Interaction Log Data Table) ---
    message_id: kb.message_id,
    timestamp: kb.received_at,
    sender: kb.sender,
    subject: kb.subject,
    message_summary: kb.message_summary,
    original_message: kb.original_message,
    category: kb.classified_category || 'unknown',
    confidence: Number(kb.classified_confidence) || 0,
    reasoning: kb.classification_reasoning || '',
    kb_match_ids: matchedIds,
    kb_used_ids: usedIds,
    kb_match_type: kb.kb_match_type,
    kb_match_score: kb.kb_top_score || 0,
    ai_response: body,
    reply_subject: reply.subject || ('Re: ' + kb.subject),
    tone: reply.tone || 'neutral',
    escalation_needed: escalated,
    priority: escalated ? 'high' : 'normal',
    delivery_status: 'delivered',
    delivery_channel: 'webhook',
    response_time_ms: elapsed,
    // --- what the webhook returns to the caller (removed before logging) ---
    reply: {
      to: kb.sender,
      subject: reply.subject || ('Re: ' + kb.subject),
      body: body,
      tone: reply.tone || 'neutral',
      escalation_needed: escalated
    }
  }
}];"""

PREPARE_LOG_CODE = """// Keep only real Data Table columns. The Respond to Webhook node still gets
// the full item from Assemble Reply on the parallel branch.
const row = $json;
return [{
  json: {
    message_id: row.message_id,
    timestamp: row.timestamp,
    sender: row.sender,
    subject: row.subject,
    message_summary: row.message_summary,
    original_message: row.original_message,
    category: row.category,
    confidence: row.confidence,
    reasoning: row.reasoning,
    kb_match_ids: row.kb_match_ids,
    kb_used_ids: row.kb_used_ids,
    kb_match_type: row.kb_match_type,
    kb_match_score: row.kb_match_score,
    ai_response: row.ai_response,
    reply_subject: row.reply_subject,
    tone: row.tone,
    escalation_needed: row.escalation_needed,
    priority: row.priority,
    delivery_status: row.delivery_status,
    delivery_channel: row.delivery_channel,
    response_time_ms: row.response_time_ms
  }
}];"""


# --------------------------------------------------------------------------
# Node builders
# --------------------------------------------------------------------------
def code_node(name, code, position, mode=None, on_error=None):
    params = {"jsCode": code}
    if mode:
        params["mode"] = mode
    node = {
        "parameters": params,
        "id": uid(),
        "name": name,
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": position,
    }
    if on_error:
        node["onError"] = on_error
    return node


def chain_node(name, prompt, position, temperature=0.0):
    return {
        "parameters": {
            "promptType": "define",
            "text": prompt,
            "hasOutputParser": True,
            "options": {},
        },
        "id": uid(),
        "name": name,
        "type": "@n8n/n8n-nodes-langchain.chainLlm",
        "typeVersion": 1.5,
        "position": position,
        "onError": "continueRegularOutput",
        "retryOnFail": True,
        "maxTries": 2,
        "waitBetweenTries": 2000,
    }


def model_node(name, position, temperature):
    return {
        "parameters": {
            "model": CLASSIFY_MODEL if temperature == 0 else RESPOND_MODEL,
            "options": {"temperature": temperature},
        },
        "id": uid(),
        "name": name,
        "type": "@n8n/n8n-nodes-langchain.lmChatOpenRouter",
        "typeVersion": 1,
        "position": position,
        "credentials": {
            "openRouterApi": {
                "id": OPENROUTER_CRED_ID,
                "name": OPENROUTER_CRED_NAME,
            }
        },
    }


def parser_node(name, example, position):
    return {
        "parameters": {"schemaType": "fromJson", "jsonSchemaExample": example},
        "id": uid(),
        "name": name,
        "type": "@n8n/n8n-nodes-langchain.outputParserStructured",
        "typeVersion": 1.2,
        "position": position,
    }


def table_node(name, table_id, table_name, position):
    return {
        "parameters": {
            "dataTableId": {
                "__rl": True,
                "value": table_id,
                "mode": "list",
                "cachedResultName": table_name,
            },
            "columns": {
                "mappingMode": "autoMapInputData",
                "value": {},
                "matchingColumns": [],
                "schema": [],
            },
            "options": {},
        },
        "id": uid(),
        "name": name,
        "type": "n8n-nodes-base.dataTable",
        "typeVersion": 1,
        "position": position,
    }


def build(table_id):
    nodes = [
        {
            "parameters": {
                "httpMethod": "POST",
                "path": "midterm-auto-responder",
                "responseMode": "responseNode",
                "options": {},
            },
            "id": uid(),
            "name": "Incoming Message Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [-560, 0],
            "webhookId": uid(),
        },
        code_node("Normalize Message", NORMALIZE_CODE, [-340, 0]),
        {
            "parameters": {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                        "version": 2,
                    },
                    "conditions": [
                        {
                            "id": uid(),
                            "leftValue": "={{ $json.valid }}",
                            "rightValue": True,
                            "operator": {
                                "type": "boolean",
                                "operation": "true",
                                "singleValue": True,
                            },
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            "id": uid(),
            "name": "Valid Message?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2,
            "position": [-120, 0],
        },
        {
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ { status: 'error', message_id: $json.message_id, error: $json.validation_error } }}",
                "options": {"responseCode": 400},
            },
            "id": uid(),
            "name": "Respond Invalid Input",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.1,
            "position": [160, 240],
        },
        chain_node("Classify Message", CLASSIFY_PROMPT, [160, 0], temperature=0.0),
        model_node("OpenRouter Chat Model (Classify)", [60, 240], 0.0),
        parser_node("Classification Parser", CLASSIFY_PARSER_EXAMPLE, [240, 240]),
        code_node("Search Knowledge Base", SEARCH_CODE, [420, 0]),
        chain_node("Generate Response", RESPOND_PROMPT, [660, 0], temperature=0.4),
        model_node("OpenRouter Chat Model (Respond)", [560, 240], 0.4),
        parser_node("Response Parser", RESPOND_PARSER_EXAMPLE, [740, 240]),
        code_node("Assemble Reply", ASSEMBLE_CODE, [900, 0]),
        {
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ { status: 'ok', message_id: $json.message_id, category: $json.category, confidence: $json.confidence, kb_matches: $json.kb_match_ids, kb_used: $json.kb_used_ids, escalation_needed: $json.escalation_needed, reply: $json.reply } }}",
                "options": {"responseCode": 200},
            },
            "id": uid(),
            "name": "Respond With Reply",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.1,
            "position": [1160, -140],
        },
        code_node("Prepare Log Row", PREPARE_LOG_CODE, [1120, 140]),
        table_node("Log Interaction", table_id, LOG_TABLE_NAME, [1340, 140]),
    ]

    def conn(targets):
        return {"main": [[{"node": t, "type": "main", "index": 0} for t in targets]]}

    connections = {
        "Incoming Message Webhook": conn(["Normalize Message"]),
        "Normalize Message": conn(["Valid Message?"]),
        "Valid Message?": {
            "main": [
                [{"node": "Classify Message", "type": "main", "index": 0}],
                [{"node": "Respond Invalid Input", "type": "main", "index": 0}],
            ]
        },
        "OpenRouter Chat Model (Classify)": {
            "ai_languageModel": [
                [{"node": "Classify Message", "type": "ai_languageModel", "index": 0}]
            ]
        },
        "Classification Parser": {
            "ai_outputParser": [
                [{"node": "Classify Message", "type": "ai_outputParser", "index": 0}]
            ]
        },
        "Classify Message": conn(["Search Knowledge Base"]),
        "Search Knowledge Base": conn(["Generate Response"]),
        "OpenRouter Chat Model (Respond)": {
            "ai_languageModel": [
                [{"node": "Generate Response", "type": "ai_languageModel", "index": 0}]
            ]
        },
        "Response Parser": {
            "ai_outputParser": [
                [{"node": "Generate Response", "type": "ai_outputParser", "index": 0}]
            ]
        },
        "Generate Response": conn(["Assemble Reply"]),
        "Assemble Reply": conn(["Respond With Reply", "Prepare Log Row"]),
        "Prepare Log Row": conn(["Log Interaction"]),
    }

    return {
        "name": "AI-Powered Auto-Responder",
        "nodes": nodes,
        "connections": connections,
        "settings": {"executionOrder": "v1"},
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--table-id", default=PLACEHOLDER_TABLE_ID, help="Data Table id for TH Interaction Log")
    args = ap.parse_args()
    print(json.dumps(build(args.table_id), indent=2))
