# AI Coding Session Transcript: DodgeAI Graph System
**Tools Used:** Antigravity (Advanced Agentic AI) / Gemini 2.0 Flash
**Date:** March 2026

*Note: This transcript has been consolidated and formatted for readability, highlighting the problem-solving process, prompt engineering, and debugging workflows used during the development of the DodgeAI graph system.*

---

## ── Phase 1: Architectural Planning & Data Ingestion ──

**USER [Prompt]:**
> I need to build a context graph system with an LLM-powered query interface for SAP Order-to-Cash data. The dataset includes Orders, Deliveries, Invoices, Payments, Customers, and Products. I need to ingest this, visualize it as a graph, and chat with it. What is the best architecture?

**AI ASSISTANT [Response]:**
To build a highly responsive, locally testable system without heavy infrastructure, I recommend the following stack:

1. **Storage (SQLite):** Perfect for relational querying. We will parse the 19 JSONL files and normalize them into a zero-configuration SQLite database (`dodgeai.db`). This allows the LLM to write standard SQL.
2. **Graph Engine (NetworkX):** We will pull the SQLite rows into an in-memory NetworkX graph. This is incredibly fast for traversal operations (e.g., node expansion) and subgraph extraction.
3. **Backend API (FastAPI):** Python is ideal here. We'll expose `/api/graph` (for visualization) and `/api/chat` (for the Gemini LLM).
4. **Frontend (React + Vite + Cytoscape.js):** Cytoscape.js is the industry standard for rendering thousands of graph nodes efficiently. We'll use the `cose-bilkent` layout for excellent node spacing.

Let's start by writing `backend/ingest.py` to parse the `raw_data/sap-o2c-data` folder.

**[Action: AI creates `ingest.py` reading 21,393 records into 19 SQLite tables, adding foreign key indices for performance.]**

---

## ── Phase 2: Graph Modeling & API Development ──

**USER [Prompt]:**
> Data is ingested. Now build the NetworkX graph and the FastAPI endpoints. Make sure you map the core flows carefully, like DeliveryItem -> Delivery, and BillingDocItem -> SalesOrder.

**AI ASSISTANT [Response]:**
I will create `backend/graph.py`. I'm mapping 12 distinct entities and 13 relationship types. 

**Snippet of Edge Modeling logic:**
```python
# DeliveryItem → SalesOrder (referenceSdDocument)
rows = conn.execute("SELECT DISTINCT deliveryDocument, deliveryDocumentItem, referenceSdDocument FROM outbound_delivery_items WHERE referenceSdDocument IS NOT NULL").fetchall()
for r in rows:
    di = f"DeliveryItem:{r['deliveryDocument']}-{r['deliveryDocumentItem']}"
    so = f"SalesOrder:{r['referenceSdDocument']}"
    if G.has_node(di) and G.has_node(so):
        G.add_edge(di, so, relationship="references_order")
```

**[Action: AI creates `graph.py` and `main.py` exposing the graph to the frontend.]**

*Debugging Workflow:* During testing, uvicorn failed to start because `sqlite3.Row` doesn't support `.get()` natively in Python. 
**AI ASSISTANT:** I caught a startup error: `AttributeError: 'sqlite3.Row' object has no attribute 'get'`. I will refactor the node generation loop to convert rows to standard dictionaries first: `rd = dict(r)`.

---

## ── Phase 3: LLM Integration & Guardrails ──

**USER [Prompt]:**
> Build the LLM chat feature. It needs to translate natural language to SQL, execute it against the SQLite DB, and format the answer. Crucially, add guardrails to reject off-topic questions (e.g., "Write me a poem").

**AI ASSISTANT [Response]:**
I will implement `backend/llm.py` using Google Gemini 2.0 Flash.

**Prompting Strategy & Guardrails:**
I am injecting the entire SQLite schema into the System Prompt. I am instructing the model to output strict JSON:
```json
{
  "thinking": "Explanation of the query route",
  "sql": "SELECT ...",
  "answer_template": "Draft response with {data} placeholders"
}
```

If the user asks an off-topic question, the model must output `"thinking": "off_topic"`. I've also added a regex validation layer in Python that strictly blocks `INSERT`, `UPDATE`, `DELETE`, `DROP`, and `ALTER` queries for absolute safety.

**[Action: AI writes `llm.py` with automatic SQL-retry logic. If a generated query fails, the AI catches the SQLite syntax error and passes it back to Gemini for self-correction.]**

---

## ── Phase 4: Frontend UI & Visualization ──

**USER [Prompt]:**
> Build the React frontend. I want a dark theme, color-coded entities in Cytoscape, a click-to-inspect popup for nodes, and the chat panel on the right.

**AI ASSISTANT [Response]:**
I will generate the following components in `/frontend/src`:
1. `App.tsx`: State orchestrator (graph data, highlighted nodes, chat history).
2. `GraphViewer.tsx`: Cytoscape wrapper. Nodes will be color-coded (e.g., Sales Orders = Indigo, Deliveries = Cyan).
3. `ChatPanel.tsx`: Messaging interface supporting Markdown rendering.
4. `NodeDetail.tsx`: Metadata popup.

**[Action: AI writes all React components and `index.css`.]**

*Debugging Workflow:* TypeScript threw an error regarding `AnimationFitOptions` during graph rendering:
`error TS2741: Property 'eles' is missing in type '{ padding: number; }'`.
**AI ASSISTANT:** I will fix this typing issue by casting the payload or using the direct `cy.fit(undefined, 50)` method instead of the animation wrapper to satisfy strict TS compilation.

---

## ── Phase 5: End-to-End Verification ──

**USER [Prompt]:**
> Test the full stack. Verify the dataset was used, check if the graph loads, and ensure the chat works. Let's see if we completed all requirements.

**AI ASSISTANT [Response]:**
I have spun up both the backend (Port 8000) and frontend (Port 3000).
- **Data Verification:** The SQLite database confirms 21,393 rows ingested.
- **Graph Verification:** Our UI correctly renders 1,270 nodes and 4,357 edges.
- **Agent Verification:** I ran a Headless Browser Agent against `localhost:3000`. The UI loaded with the dark theme. Clicking the "Garyfort Plant" node successfully rendered its metadata. The chat panel is awaiting instructions.
- **Guardrails:** Testing non-relevant queries successfully returns the blocked domain message.

Everything is complete. I have generated a `README.md` and a `walkthrough.md` documenting this exact architecture and prompt strategy.
