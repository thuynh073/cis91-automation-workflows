#!/usr/bin/env python3
"""Build the 'JH - Data Scraper & Formatter' workflow JSON and write it to
labs/week05/data-scraper-formatter.json (or print to stdout with --stdout).

No secrets live in this file: the n8n API key is read from $N8N_API_KEY at
push time (see push.sh), and only Data Table IDs appear below.
"""
import json
import uuid

BOOKS_TABLE_ID = "eM7tdvRtJAdaddvA"   # JH Books
SUMMARY_TABLE_ID = "rFZv7TUwAIUHlKtc"  # JH Book Summary

CLEAN_CODE = """return $input.all().map(item => {
  const data = item.json;

  // Parse price: remove "£" and convert to number
  const price = parseFloat((data.price || '').replace(/[^0-9.]/g, ''));

  // Parse availability: extract clean text
  const available = (data.availability || '').trim().toLowerCase().includes('in stock');

  // Parse rating: extract star count from class name
  const ratingMap = { 'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5 };
  const ratingClass = (data.rating || '').replace('star-rating ', '');
  const stars = ratingMap[ratingClass] || 0;

  return {
    json: {
      title: data.title || 'Unknown',
      price: price,
      in_stock: available,
      stars: stars,
      value_score: stars > 0 ? Math.round((stars / price) * 100) / 100 : 0
    }
  };
});"""

SUMMARY_CODE = """const items = $input.all();
const prices = items.map(i => i.json.price);
const total = prices.reduce((sum, p) => sum + p, 0);
const avg = total / prices.length;

return [{
  json: {
    total_books: items.length,
    total_value: Math.round(total * 100) / 100,
    average_price: Math.round(avg * 100) / 100,
    cheapest: items[0]?.json.title || 'N/A',
    cheapest_price: prices[0] || 0,
    most_expensive: items[items.length - 1]?.json.title || 'N/A',
    most_expensive_price: prices[prices.length - 1] || 0,
    five_star_count: items.filter(i => i.json.stars === 5).length,
    generated_at: new Date().toISOString()
  }
}];"""


def table_node(name, table_id, table_name, position):
    """Data Table node, Insert row + Map Automatically (autoMapInputData)."""
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
        "id": str(uuid.uuid4()),
        "name": name,
        "type": "n8n-nodes-base.dataTable",
        "typeVersion": 1,
        "position": position,
    }


nodes = [
    {
        "parameters": {},
        "id": str(uuid.uuid4()),
        "name": "Manual Trigger",
        "type": "n8n-nodes-base.manualTrigger",
        "typeVersion": 1,
        "position": [-220, 0],
    },
    {
        "parameters": {
            "rule": {"interval": [{"field": "days", "triggerAtHour": 9}]}
        },
        "id": str(uuid.uuid4()),
        "name": "Schedule Trigger",
        "type": "n8n-nodes-base.scheduleTrigger",
        "typeVersion": 1.2,
        "position": [-220, 200],
    },
    {
        "parameters": {"url": "https://books.toscrape.com", "options": {}},
        "id": str(uuid.uuid4()),
        "name": "Fetch Bookstore",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [0, 60],
    },
    {
        "parameters": {
            "operation": "extractHtmlContent",
            "extractionValues": {
                "values": [
                    {
                        "key": "books",
                        "cssSelector": "article.product_pod",
                        "returnValue": "html",
                        "returnArray": True,
                    }
                ]
            },
            "options": {},
        },
        "id": str(uuid.uuid4()),
        "name": "Extract Books",
        "type": "n8n-nodes-base.html",
        "typeVersion": 1.2,
        "position": [220, 60],
    },
    {
        "parameters": {"fieldToSplitOut": "books", "options": {}},
        "id": str(uuid.uuid4()),
        "name": "Split Out Books",
        "type": "n8n-nodes-base.splitOut",
        "typeVersion": 1,
        "position": [440, 60],
    },
    {
        "parameters": {
            "operation": "extractHtmlContent",
            "dataPropertyName": "books",
            "extractionValues": {
                "values": [
                    {
                        "key": "title",
                        "cssSelector": "h3 a",
                        "returnValue": "attribute",
                        "attribute": "title",
                    },
                    {"key": "price", "cssSelector": ".price_color"},
                    {"key": "availability", "cssSelector": ".availability"},
                    {
                        "key": "rating",
                        "cssSelector": "p.star-rating",
                        "returnValue": "attribute",
                        "attribute": "class",
                    },
                ]
            },
            "options": {},
        },
        "id": str(uuid.uuid4()),
        "name": "Extract Book Fields",
        "type": "n8n-nodes-base.html",
        "typeVersion": 1.2,
        "position": [660, 60],
    },
    {
        "parameters": {"jsCode": CLEAN_CODE},
        "id": str(uuid.uuid4()),
        "name": "Clean Book Data",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [880, 60],
    },
    {
        "parameters": {
            "sortFieldsUi": {
                "sortField": [{"fieldName": "price", "order": "ascending"}]
            },
            "options": {},
        },
        "id": str(uuid.uuid4()),
        "name": "Sort by Price",
        "type": "n8n-nodes-base.sort",
        "typeVersion": 1,
        "position": [1100, 60],
    },
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
                        "id": str(uuid.uuid4()),
                        "leftValue": "={{ $json.in_stock }}",
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
        "id": str(uuid.uuid4()),
        "name": "In Stock Only",
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [1320, 60],
    },
    table_node("Save Books", BOOKS_TABLE_ID, "JH Books", [1540, -60]),
    {
        "parameters": {"jsCode": SUMMARY_CODE},
        "id": str(uuid.uuid4()),
        "name": "Summary Statistics",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1540, 160],
    },
    table_node("Save Summary", SUMMARY_TABLE_ID, "JH Book Summary", [1760, 160]),
]


def conn(targets):
    return {"main": [[{"node": t, "type": "main", "index": 0} for t in targets]]}


connections = {
    "Manual Trigger": conn(["Fetch Bookstore"]),
    "Schedule Trigger": conn(["Fetch Bookstore"]),
    "Fetch Bookstore": conn(["Extract Books"]),
    "Extract Books": conn(["Split Out Books"]),
    "Split Out Books": conn(["Extract Book Fields"]),
    "Extract Book Fields": conn(["Clean Book Data"]),
    "Clean Book Data": conn(["Sort by Price"]),
    "Sort by Price": conn(["In Stock Only"]),
    "In Stock Only": {"main": [
        [{"node": "Save Books", "type": "main", "index": 0},
         {"node": "Summary Statistics", "type": "main", "index": 0}],
        [],
    ]},
    "Summary Statistics": conn(["Save Summary"]),
}

workflow = {
    "name": "JH - Data Scraper & Formatter",
    "nodes": nodes,
    "connections": connections,
    "settings": {"executionOrder": "v1", "binaryMode": "separate"},
}

if __name__ == "__main__":
    print(json.dumps(workflow, indent=2))
