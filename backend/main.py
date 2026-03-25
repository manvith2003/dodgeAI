"""
FastAPI application: serves graph data, chat queries, and schema info.
"""
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from graph import build_graph, get_full_graph, get_node_detail, expand_node, search_nodes
from llm import chat, get_schema_info

# Global graph instance
_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build graph on startup."""
    global _graph
    print("Building graph...")
    _graph = build_graph()
    print("Graph ready!")
    yield


app = FastAPI(title="DodgeAI API", version="1.0.0", lifespan=lifespan)

# CORS - allow frontend to access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic models ---

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[list] = None


class ChatResponse(BaseModel):
    answer: str
    sql: Optional[str] = None
    results: Optional[dict] = None
    referenced_nodes: list = []
    thinking: Optional[str] = None


# --- Graph endpoints ---

@app.get("/api/graph")
async def get_graph(max_nodes: int = 500):
    """Get the full graph for visualization."""
    if _graph is None:
        raise HTTPException(status_code=503, detail="Graph not ready")
    return get_full_graph(_graph, max_nodes)


@app.get("/api/graph/node/{node_id:path}")
async def get_node(node_id: str):
    """Get details and neighbors of a specific node."""
    if _graph is None:
        raise HTTPException(status_code=503, detail="Graph not ready")
    result = get_node_detail(_graph, node_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    return result


@app.get("/api/graph/expand/{node_id:path}")
async def expand(node_id: str, depth: int = 1):
    """Get subgraph around a node."""
    if _graph is None:
        raise HTTPException(status_code=503, detail="Graph not ready")
    return expand_node(_graph, node_id, depth)


@app.get("/api/graph/search")
async def search(q: str, limit: int = 20):
    """Search nodes by label or entity type."""
    if _graph is None:
        raise HTTPException(status_code=503, detail="Graph not ready")
    return search_nodes(_graph, q, limit)


# --- Chat endpoint ---

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Process a natural language query."""
    result = await chat(request.message, request.conversation_history)
    return ChatResponse(**result)


# --- Schema endpoint ---

@app.get("/api/schema")
async def schema():
    """Get database schema information."""
    return get_schema_info()


# --- Health check ---

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "graph_ready": _graph is not None,
        "graph_nodes": _graph.number_of_nodes() if _graph else 0,
        "graph_edges": _graph.number_of_edges() if _graph else 0,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
