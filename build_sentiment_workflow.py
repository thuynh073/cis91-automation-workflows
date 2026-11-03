#!/usr/bin/env python3
"""Build the 'Sentiment Analysis Pipeline' workflow JSON (CIS 91 week 06 lab).

Prints the workflow JSON to stdout. No secrets here: only the OpenRouter
credential ID and the two Data Table IDs.
"""
import json
import uuid

REVIEWS_TABLE_ID = "cqVgQuZLhRuWOCni"    # TH Reviews
DASHBOARD_TABLE_ID = "oJJ3m9PSYzfXt7LH"  # TH Sentiment Dashboard
OPENROUTER_CRED_ID = "W9uBPl8BObqfpjkn"  # TH OpenRouter
OPENROUTER_CRED_NAME = "TH OpenRouter"
MODEL = "deepseek/deepseek-v4.1-flash-1017"

uid = lambda: str(uuid.uuid4())

TEST_CODE = """return [
  {
    json: {
      review_id: 'R001',
      product: 'Wireless Earbuds Pro',
      reviewer: 'Alice M.',
      review_text: 'Absolutely love these earbuds! Sound quality is incredible and the battery lasts all day. Best purchase I made this year.',
      date: '2026-03-01'
    }
  },
  {
    json: {
      review_id: 'R002',
      product: 'Wireless Earbuds Pro',
      reviewer: 'Bob T.',
      review_text: 'Terrible quality. The left earbud stopped working after two days. Customer service was unhelpful and rude. Want my money back.',
      date: '2026-03-03'
    }
  },
  {
    json: {
      review_id: 'R003',
      product: 'Phone Case Ultra',
      reviewer: 'Carol S.',
      review_text: 'It is a phone case. It fits my phone and seems to protect it fine. Nothing special but nothing wrong with it either.',
      date: '2026-03-05'
    }
  },
  {
    json: {
      review_id: 'R004',
      product: 'Laptop Stand Deluxe',
      reviewer: 'David K.',
      review_text: 'The stand wobbles slightly but overall improves my desk setup. Wish it was more adjustable. Decent for the price.',
      date: '2026-03-07'
    }
  },
  {
    json: {
      review_id: 'R005',
      product: 'Laptop Stand Deluxe',
      reviewer: 'Eve R.',
      review_text: 'This completely transformed my workspace! Ergonomic, sturdy, and looks great. My neck pain is gone. Five stars easily!',
      date: '2026-03-09'
    }
  }
];"""

PROMPT = """=Analyze the sentiment of this product review.

Product: {{ $json.product }}
Review: {{ $json.review_text }}

Classify the sentiment as "positive", "negative", or "neutral". Include a
confidence from 0.0 to 1.0, the single strongest emotion (e.g., joy,
frustration, indifference, satisfaction, anger), and a one-sentence summary."""

PARSER_EXAMPLE = json.dumps(
    {
        "sentiment": "positive",
        "confidence": 0.95,
        "key_emotion": "joy",
        "summary": "one-sentence summary of the review",
    },
    indent=2,
)

COMBINE_CODE = """// The Structured Output Parser puts the parsed object in $json.output
const aiResult = $json.output;
// The original review this AI result came from
const review = $('Test Reviews').item.json;

return {
  json: {
    review_id: review.review_id,
    product: review.product,
    reviewer: review.reviewer,
    review_text: review.review_text,
    date: review.date,
    sentiment: aiResult.sentiment,
    confidence: aiResult.confidence,
    key_emotion: aiResult.key_emotion,
    ai_summary: aiResult.summary
  }
};"""

DASHBOARD_CODE = """const items = $input.all();
const total = items.length;
const positive = items.filter(i => i.json.sentiment === 'positive').length;
const negative = items.filter(i => i.json.sentiment === 'negative').length;
const neutral = total - positive - negative;
const avgConfidence = items.reduce((sum, i) => sum + (i.json.confidence || 0), 0) / total;
const escalations = items.filter(i => i.json.priority === 'high').length;

return [{
  json: {
    report_title: 'Sentiment Analysis Dashboard',
    generated_at: new Date().toISOString(),
    total_reviews: total,
    positive_count: positive,
    positive_pct: Math.round((positive / total) * 100) + '%',
    negative_count: negative,
    negative_pct: Math.round((negative / total) * 100) + '%',
    neutral_count: neutral,
    neutral_pct: Math.round((neutral / total) * 100) + '%',
    average_confidence: Math.round(avgConfidence * 100) / 100,
    escalations_needed: escalations
  }
}];"""


def code_node(name, code, position, mode=None):
    params = {"jsCode": code}
    if mode:
        params["mode"] = mode
    return {
        "parameters": params,
        "id": uid(),
        "name": name,
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
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


def set_node(name, fields, position):
    return {
        "parameters": {
            "assignments": {
                "assignments": [
                    {"id": uid(), "name": k, "value": v, "type": "string"}
                    for k, v in fields
                ]
            },
            "includeOtherFields": True,
            "options": {},
        },
        "id": uid(),
        "name": name,
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": position,
    }


def rule(value, output_name):
    return {
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
                    "leftValue": "={{ $json.sentiment }}",
                    "rightValue": value,
                    "operator": {"type": "string", "operation": "equals"},
                }
            ],
            "combinator": "and",
        },
        "renameOutput": True,
        "outputKey": output_name,
    }


nodes = [
    {
        "parameters": {},
        "id": uid(),
        "name": "Manual Trigger",
        "type": "n8n-nodes-base.manualTrigger",
        "typeVersion": 1,
        "position": [-220, 0],
    },
    code_node("Test Reviews", TEST_CODE, [0, 0]),
    {
        "parameters": {
            "promptType": "define",
            "text": PROMPT,
            "hasOutputParser": True,
            "options": {},
        },
        "id": uid(),
        "name": "Analyze Sentiment",
        "type": "@n8n/n8n-nodes-langchain.chainLlm",
        "typeVersion": 1.5,
        "position": [220, 0],
    },
    {
        "parameters": {
            "model": MODEL,
            "options": {"temperature": 0},
        },
        "id": uid(),
        "name": "OpenRouter Chat Model",
        "type": "@n8n/n8n-nodes-langchain.lmChatOpenRouter",
        "typeVersion": 1,
        "position": [140, 220],
        "credentials": {
            "openRouterApi": {
                "id": OPENROUTER_CRED_ID,
                "name": OPENROUTER_CRED_NAME,
            }
        },
    },
    {
        "parameters": {
            "schemaType": "fromJson",
            "jsonSchemaExample": PARSER_EXAMPLE,
        },
        "id": uid(),
        "name": "Structured Output Parser",
        "type": "@n8n/n8n-nodes-langchain.outputParserStructured",
        "typeVersion": 1.2,
        "position": [300, 220],
    },
    code_node("Combine Results", COMBINE_CODE, [460, 0], mode="runOnceForEachItem"),
    {
        "parameters": {
            "rules": {
                "values": [
                    rule("positive", "Positive"),
                    rule("negative", "Negative"),
                ]
            },
            "options": {"fallbackOutput": "extra", "renameFallbackOutput": "Neutral/Mixed"},
        },
        "id": uid(),
        "name": "Route by Sentiment",
        "type": "n8n-nodes-base.switch",
        "typeVersion": 3,
        "position": [700, 0],
    },
    set_node(
        "Positive Action",
        [
            ("action", "Feature in testimonials"),
            ("priority", "low"),
            ("follow_up", "Send thank-you coupon"),
        ],
        [940, -160],
    ),
    set_node(
        "Negative Action",
        [
            ("action", "Escalate to customer success"),
            ("priority", "high"),
            ("follow_up", "Reach out within 24 hours"),
        ],
        [940, 0],
    ),
    set_node(
        "Neutral Action",
        [
            ("action", "Add to product feedback log"),
            ("priority", "medium"),
            ("follow_up", "Include in weekly product review"),
        ],
        [940, 160],
    ),
    {
        "parameters": {"mode": "append", "numberInputs": 3, "options": {}},
        "id": uid(),
        "name": "Combine All",
        "type": "n8n-nodes-base.merge",
        "typeVersion": 3,
        "position": [1180, 0],
    },
    code_node("Generate Dashboard", DASHBOARD_CODE, [1400, 120]),
    table_node("Log Reviews", REVIEWS_TABLE_ID, "TH Reviews", [1400, -80]),
    table_node("Log Dashboard", DASHBOARD_TABLE_ID, "TH Sentiment Dashboard", [1620, 120]),
]


def conn(targets):
    return {"main": [[{"node": t, "type": "main", "index": 0} for t in targets]]}


connections = {
    "Manual Trigger": conn(["Test Reviews"]),
    "Test Reviews": conn(["Analyze Sentiment"]),
    "OpenRouter Chat Model": {
        "ai_languageModel": [[{"node": "Analyze Sentiment", "type": "ai_languageModel", "index": 0}]]
    },
    "Structured Output Parser": {
        "ai_outputParser": [[{"node": "Analyze Sentiment", "type": "ai_outputParser", "index": 0}]]
    },
    "Analyze Sentiment": conn(["Combine Results"]),
    "Combine Results": conn(["Route by Sentiment"]),
    "Route by Sentiment": {
        "main": [
            [{"node": "Positive Action", "type": "main", "index": 0}],
            [{"node": "Negative Action", "type": "main", "index": 0}],
            [{"node": "Neutral Action", "type": "main", "index": 0}],
        ]
    },
    "Positive Action": {"main": [[{"node": "Combine All", "type": "main", "index": 0}]]},
    "Negative Action": {"main": [[{"node": "Combine All", "type": "main", "index": 1}]]},
    "Neutral Action": {"main": [[{"node": "Combine All", "type": "main", "index": 2}]]},
    "Combine All": conn(["Log Reviews", "Generate Dashboard"]),
    "Generate Dashboard": conn(["Log Dashboard"]),
}

workflow = {
    "name": "Sentiment Analysis Pipeline",
    "nodes": nodes,
    "connections": connections,
    "settings": {"executionOrder": "v1"},
}

if __name__ == "__main__":
    print(json.dumps(workflow, indent=2))
