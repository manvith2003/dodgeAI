# DodgeAI — Graph-Based Order-to-Cash Data Modeling & Query System

An interactive graph visualization and AI-powered query system that models SAP Order-to-Cash (O2C) business data as a connected graph, enabling natural language exploration of complex business relationships.

![DodgeAI Screenshot](docs/screenshot.png)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (Vite + React + TypeScript)                   │
│  ┌─────────────────────┐  ┌──────────────────────────┐  │
│  │  Graph Visualization │  │  Chat Interface           │ │
│  │  (Cytoscape.js)      │  │  (NL → SQL → Response)   │ │
│  └─────────────────────┘  └──────────────────────────┘  │
└───────────────────────┬─────────────────────────────────┘
                        │ REST API (proxied via Vite)
┌───────────────────────▼─────────────────────────────────┐
│  Backend (Python / FastAPI)                             │
│  ┌───────────┐ ┌──────────────┐ ┌────────────────────┐  │
│  │ Graph API  │ │ Chat/LLM API │ │ Data Ingestion     │  │
│  └───────────┘ └──────────────┘ └────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐│
│  │  SQLite (structured storage) + NetworkX (graph)     ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### Database: SQLite
- **Zero-config**, file-based, no external dependencies
- Perfect for this data scale (~21K records across 19 tables)
- Enables standard SQL querying which the LLM can generate
- Indexed on all foreign-key columns for fast joins

### Graph Engine: NetworkX (in-memory)
- Fast traversal and neighborhood queries
- 1,270 nodes and 4,357 edges modeling the full O2C flow
- Supports BFS node expansion, path tracing, and subgraph extraction

### Graph Visualization: Cytoscape.js
- Production-grade graph rendering with cose-bilkent force-directed layout
- Entity-type color coding and size differentiation
- Click-to-inspect nodes with metadata popup
- "Granular Overlay" toggle to show/hide item-level detail
- Highlighted node support for chat response references

### LLM: Google Gemini (gemini-2.0-flash, free tier)
- **Prompting Strategy**: System prompt contains the full database schema with all 19 tables, column descriptions, foreign-key relationships, and the Order-to-Cash flow mapping. The LLM is instructed to return a structured JSON response `{thinking, sql, answer_template}`.
- **NL → SQL Translation**: User questions are translated to SQL queries executed against SQLite. Results are formatted into natural language responses.
- **Auto-retry**: If SQL fails, the error is sent back to the LLM for self-correction.
- **Conversation Memory**: Last 10 messages are sent as context for follow-up questions.

### Guardrails
- **Off-topic rejection**: System prompt instructs the LLM to return a `"thinking": "off_topic"` marker for non-dataset queries (general knowledge, creative writing, etc.)
- **SQL safety validation**: Only `SELECT`/`WITH` statements are allowed. `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER` and other DDL/DML are blocked via regex.
- **Result limiting**: All queries are limited to 50 rows to prevent excessive output.

## Graph Model

```
SalesOrder ──has_item──▶ SalesOrderItem ──uses_material──▶ Product
    │                                                          │
    ├── ordered_by ──▶ Customer ──has_address──▶ Address        ├── at_plant ──▶ Plant
    │                                                          
    ├── (via delivery items) ──▶ Delivery ──has_item──▶ DeliveryItem ──from_plant──▶ Plant
    │
    ├── (via billing items) ──▶ BillingDocument ──journal_entry──▶ JournalEntry ──cleared_by──▶ Payment
```

**19 Entity Tables** mapped to **12 Node Types** with **13 Relationship Types**.

## Example Queries

| Query | What It Does |
|-------|-------------|
| "Which products are associated with the highest number of billing documents?" | Joins billing_document_items → products, aggregates by count |
| "Trace the full flow of billing document 91150187" | Follows BillingDoc → SalesOrder → Delivery → JournalEntry → Payment |
| "Identify sales orders with incomplete flows" | LEFT JOINs across delivery and billing tables to find gaps |
| "Write me a poem" | Rejected: "This system is designed to answer questions related to the SAP Order-to-Cash dataset only." |

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Google Gemini API key ([get one free](https://ai.google.dev))

### Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Set your Gemini API key
echo "GEMINI_API_KEY=your_key_here" > .env

# Ingest the dataset (creates dodgeai.db)
python ingest.py

# Start the API server
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

## Project Structure

```
DodgeAI/
├── backend/
│   ├── main.py          # FastAPI app with graph, chat, schema endpoints
│   ├── ingest.py        # JSONL → SQLite ingestion script
│   ├── graph.py         # NetworkX graph construction + traversal APIs
│   ├── llm.py           # Gemini integration, NL→SQL, guardrails
│   ├── dodgeai.db       # SQLite database (generated)
│   ├── requirements.txt
│   └── .env             # GEMINI_API_KEY
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # Main orchestrator component
│   │   ├── components/
│   │   │   ├── GraphViewer.tsx # Cytoscape.js graph canvas
│   │   │   ├── ChatPanel.tsx   # Chat interface
│   │   │   └── NodeDetail.tsx  # Node metadata popup
│   │   └── index.css           # Design system (dark theme)
│   ├── index.html
│   ├── vite.config.ts          # Dev server + API proxy
│   └── package.json
└── raw_data/                   # SAP O2C dataset (JSONL)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/graph` | GET | Full graph (nodes + edges) for visualization |
| `/api/graph/node/{id}` | GET | Node details + neighbors |
| `/api/graph/expand/{id}` | GET | Subgraph around a node |
| `/api/graph/search?q=` | GET | Search nodes by label/type |
| `/api/chat` | POST | Natural language query → data-backed response |
| `/api/schema` | GET | Database schema information |
| `/api/health` | GET | Health check |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Vite |
| Graph Viz | Cytoscape.js + cose-bilkent layout |
| Backend | Python + FastAPI + Uvicorn |
| Database | SQLite |
| Graph Engine | NetworkX |
| LLM | Google Gemini 2.0 Flash |
| Styling | Vanilla CSS (dark theme) |
