"""
Graph construction module: builds a NetworkX graph from SQLite data.
Provides APIs for graph traversal, node expansion, and search.
"""
import json
import sqlite3
import os
import networkx as nx

DB_PATH = os.path.join(os.path.dirname(__file__), "dodgeai.db")


def get_db():
    """Get SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def build_graph():
    """Build a NetworkX graph from the SQLite database."""
    G = nx.Graph()
    conn = get_db()

    # --- Add nodes ---

    # Sales Orders
    rows = conn.execute("SELECT * FROM sales_order_headers").fetchall()
    for r in rows:
        node_id = f"SalesOrder:{r['salesOrder']}"
        G.add_node(node_id, entity="Sales Order", label=r['salesOrder'], **dict(r))

    # Sales Order Items
    rows = conn.execute("SELECT * FROM sales_order_items").fetchall()
    for r in rows:
        node_id = f"SalesOrderItem:{r['salesOrder']}-{r['salesOrderItem']}"
        G.add_node(node_id, entity="Sales Order Item", label=f"{r['salesOrder']}-{r['salesOrderItem']}", **dict(r))

    # Outbound Delivery Headers
    rows = conn.execute("SELECT * FROM outbound_delivery_headers").fetchall()
    for r in rows:
        node_id = f"Delivery:{r['deliveryDocument']}"
        G.add_node(node_id, entity="Delivery", label=r['deliveryDocument'], **dict(r))

    # Outbound Delivery Items
    rows = conn.execute("SELECT * FROM outbound_delivery_items").fetchall()
    for r in rows:
        node_id = f"DeliveryItem:{r['deliveryDocument']}-{r['deliveryDocumentItem']}"
        G.add_node(node_id, entity="Delivery Item", label=f"{r['deliveryDocument']}-{r['deliveryDocumentItem']}", **dict(r))

    # Billing Document Headers
    rows = conn.execute("SELECT * FROM billing_document_headers").fetchall()
    for r in rows:
        node_id = f"BillingDoc:{r['billingDocument']}"
        G.add_node(node_id, entity="Billing Document", label=r['billingDocument'], **dict(r))

    # Billing Document Items
    rows = conn.execute("SELECT * FROM billing_document_items").fetchall()
    for r in rows:
        node_id = f"BillingDocItem:{r['billingDocument']}-{r['billingDocumentItem']}"
        G.add_node(node_id, entity="Billing Document Item", label=f"{r['billingDocument']}-{r['billingDocumentItem']}", **dict(r))

    # Journal Entries
    rows = conn.execute("SELECT * FROM journal_entries").fetchall()
    for r in rows:
        node_id = f"JournalEntry:{r['accountingDocument']}"
        if not G.has_node(node_id):
            G.add_node(node_id, entity="Journal Entry", label=r['accountingDocument'], **dict(r))

    # Payments
    rows = conn.execute("SELECT * FROM payments").fetchall()
    for r in rows:
        node_id = f"Payment:{r['accountingDocument']}"
        if not G.has_node(node_id):
            G.add_node(node_id, entity="Payment", label=r['accountingDocument'], **dict(r))

    # Customers (Business Partners)
    rows = conn.execute("SELECT * FROM customers").fetchall()
    for r in rows:
        rd = dict(r)
        node_id = f"Customer:{rd['customer']}"
        G.add_node(node_id, entity="Customer", label=rd.get('businessPartnerFullName') or rd['customer'], **rd)

    # Products
    rows = conn.execute("SELECT * FROM products").fetchall()
    for r in rows:
        node_id = f"Product:{r['product']}"
        # Try to get description
        desc = conn.execute(
            "SELECT productDescription FROM product_descriptions WHERE product = ? LIMIT 1",
            (r['product'],)
        ).fetchone()
        product_label = desc['productDescription'] if desc else r['product']
        G.add_node(node_id, entity="Product", label=product_label, **dict(r))

    # Plants
    rows = conn.execute("SELECT * FROM plants").fetchall()
    for r in rows:
        rd = dict(r)
        node_id = f"Plant:{rd['plant']}"
        G.add_node(node_id, entity="Plant", label=rd.get('plantName') or rd['plant'], **rd)

    # Customer Addresses
    rows = conn.execute("SELECT * FROM customer_addresses").fetchall()
    for r in rows:
        node_id = f"Address:{r['businessPartner']}"
        G.add_node(node_id, entity="Address", label=f"Address-{r['businessPartner']}", **dict(r))

    # --- Add edges ---

    # SalesOrder → SalesOrderItem
    rows = conn.execute("SELECT DISTINCT salesOrder, salesOrderItem FROM sales_order_items").fetchall()
    for r in rows:
        so = f"SalesOrder:{r['salesOrder']}"
        soi = f"SalesOrderItem:{r['salesOrder']}-{r['salesOrderItem']}"
        if G.has_node(so) and G.has_node(soi):
            G.add_edge(so, soi, relationship="has_item")

    # SalesOrderItem → Product (material)
    rows = conn.execute("SELECT DISTINCT salesOrder, salesOrderItem, material FROM sales_order_items WHERE material IS NOT NULL AND material != ''").fetchall()
    for r in rows:
        soi = f"SalesOrderItem:{r['salesOrder']}-{r['salesOrderItem']}"
        prod = f"Product:{r['material']}"
        if G.has_node(soi) and G.has_node(prod):
            G.add_edge(soi, prod, relationship="uses_material")

    # SalesOrder → Customer (soldToParty)
    rows = conn.execute("SELECT DISTINCT salesOrder, soldToParty FROM sales_order_headers WHERE soldToParty IS NOT NULL AND soldToParty != ''").fetchall()
    for r in rows:
        so = f"SalesOrder:{r['salesOrder']}"
        cust = f"Customer:{r['soldToParty']}"
        if G.has_node(so) and G.has_node(cust):
            G.add_edge(so, cust, relationship="ordered_by")

    # DeliveryItem → Delivery
    rows = conn.execute("SELECT DISTINCT deliveryDocument, deliveryDocumentItem FROM outbound_delivery_items").fetchall()
    for r in rows:
        dh = f"Delivery:{r['deliveryDocument']}"
        di = f"DeliveryItem:{r['deliveryDocument']}-{r['deliveryDocumentItem']}"
        if G.has_node(dh) and G.has_node(di):
            G.add_edge(dh, di, relationship="has_item")

    # DeliveryItem → SalesOrder (referenceSdDocument)
    rows = conn.execute("SELECT DISTINCT deliveryDocument, deliveryDocumentItem, referenceSdDocument FROM outbound_delivery_items WHERE referenceSdDocument IS NOT NULL AND referenceSdDocument != ''").fetchall()
    for r in rows:
        di = f"DeliveryItem:{r['deliveryDocument']}-{r['deliveryDocumentItem']}"
        so = f"SalesOrder:{r['referenceSdDocument']}"
        if G.has_node(di) and G.has_node(so):
            G.add_edge(di, so, relationship="references_order")

    # DeliveryItem → Plant
    rows = conn.execute("SELECT DISTINCT deliveryDocument, deliveryDocumentItem, plant FROM outbound_delivery_items WHERE plant IS NOT NULL AND plant != ''").fetchall()
    for r in rows:
        di = f"DeliveryItem:{r['deliveryDocument']}-{r['deliveryDocumentItem']}"
        plant = f"Plant:{r['plant']}"
        if G.has_node(di) and G.has_node(plant):
            G.add_edge(di, plant, relationship="from_plant")

    # BillingDocItem → BillingDoc
    rows = conn.execute("SELECT DISTINCT billingDocument, billingDocumentItem FROM billing_document_items").fetchall()
    for r in rows:
        bd = f"BillingDoc:{r['billingDocument']}"
        bdi = f"BillingDocItem:{r['billingDocument']}-{r['billingDocumentItem']}"
        if G.has_node(bd) and G.has_node(bdi):
            G.add_edge(bd, bdi, relationship="has_item")

    # BillingDocItem → SalesOrder (via referenceSdDocument)
    rows = conn.execute("SELECT DISTINCT billingDocument, billingDocumentItem, referenceSdDocument FROM billing_document_items WHERE referenceSdDocument IS NOT NULL AND referenceSdDocument != ''").fetchall()
    for r in rows:
        bdi = f"BillingDocItem:{r['billingDocument']}-{r['billingDocumentItem']}"
        so = f"SalesOrder:{r['referenceSdDocument']}"
        if G.has_node(bdi) and G.has_node(so):
            G.add_edge(bdi, so, relationship="references_order")

    # BillingDoc → JournalEntry (via referenceDocument matching billingDocument)
    rows = conn.execute("SELECT DISTINCT referenceDocument, accountingDocument FROM journal_entries WHERE referenceDocument IS NOT NULL AND referenceDocument != ''").fetchall()
    for r in rows:
        je = f"JournalEntry:{r['accountingDocument']}"
        bd = f"BillingDoc:{r['referenceDocument']}"
        if G.has_node(je) and G.has_node(bd):
            G.add_edge(bd, je, relationship="journal_entry")

    # JournalEntry → Payment (via clearingAccountingDocument)
    rows = conn.execute("SELECT DISTINCT accountingDocument, clearingAccountingDocument FROM journal_entries WHERE clearingAccountingDocument IS NOT NULL AND clearingAccountingDocument != ''").fetchall()
    for r in rows:
        je = f"JournalEntry:{r['accountingDocument']}"
        pay = f"Payment:{r['clearingAccountingDocument']}"
        if G.has_node(je) and G.has_node(pay):
            G.add_edge(je, pay, relationship="cleared_by")

    # Customer → Address
    rows = conn.execute("SELECT DISTINCT businessPartner FROM customer_addresses").fetchall()
    for r in rows:
        cust = f"Customer:{r['businessPartner']}"
        addr = f"Address:{r['businessPartner']}"
        if G.has_node(cust) and G.has_node(addr):
            G.add_edge(cust, addr, relationship="has_address")

    # Product → Plant (via product_plants, limit to meaningful connections)
    rows = conn.execute("SELECT DISTINCT product, plant FROM product_plants").fetchall()
    for r in rows:
        prod = f"Product:{r['product']}"
        plant = f"Plant:{r['plant']}"
        if G.has_node(prod) and G.has_node(plant):
            G.add_edge(prod, plant, relationship="at_plant")

    conn.close()

    print(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


# --- API functions ---

def node_to_dict(G, node_id):
    """Convert a node to a serializable dict."""
    if not G.has_node(node_id):
        return None
    data = dict(G.nodes[node_id])
    return {
        "id": node_id,
        "entity": data.get("entity", "Unknown"),
        "label": data.get("label", node_id),
        "data": {k: v for k, v in data.items() if k not in ("entity", "label")},
        "connections": G.degree(node_id),
    }


def edge_to_dict(G, u, v):
    """Convert an edge to a serializable dict."""
    data = G.edges[u, v]
    return {
        "source": u,
        "target": v,
        "relationship": data.get("relationship", "related_to"),
    }


def get_full_graph(G, max_nodes=500):
    """Get the full graph for visualization, potentially limited."""
    nodes = []
    edges = []

    # If graph is too large, use a sampling strategy
    all_nodes = list(G.nodes())
    if len(all_nodes) > max_nodes:
        # Prioritize high-level entities (Sales Orders, Deliveries, Billing, etc.)
        priority_types = ["Sales Order", "Delivery", "Billing Document", "Journal Entry", "Payment", "Customer", "Product", "Plant"]
        selected = set()
        for ptype in priority_types:
            for n in all_nodes:
                if G.nodes[n].get("entity") == ptype:
                    selected.add(n)
        # Add some items if under limit
        for n in all_nodes:
            if len(selected) >= max_nodes:
                break
            selected.add(n)
        all_nodes = list(selected)

    node_set = set(all_nodes)
    for n in all_nodes:
        nd = node_to_dict(G, n)
        if nd:
            nodes.append(nd)

    for u, v in G.edges():
        if u in node_set and v in node_set:
            edges.append(edge_to_dict(G, u, v))

    return {"nodes": nodes, "edges": edges}


def get_node_detail(G, node_id):
    """Get detailed info for a node including its neighbors."""
    nd = node_to_dict(G, node_id)
    if not nd:
        return None

    neighbors = []
    for n in G.neighbors(node_id):
        edge_data = G.edges[node_id, n]
        neighbors.append({
            "node": node_to_dict(G, n),
            "relationship": edge_data.get("relationship", "related_to"),
        })

    return {
        "node": nd,
        "neighbors": neighbors,
    }


def expand_node(G, node_id, depth=1):
    """Get subgraph around a node up to given depth."""
    if not G.has_node(node_id):
        return {"nodes": [], "edges": []}

    # BFS to collect nodes within depth
    visited = {node_id}
    frontier = {node_id}
    for _ in range(depth):
        next_frontier = set()
        for n in frontier:
            for neighbor in G.neighbors(n):
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.add(neighbor)
        frontier = next_frontier

    nodes = [node_to_dict(G, n) for n in visited if node_to_dict(G, n)]
    edges = []
    for u, v in G.edges():
        if u in visited and v in visited:
            edges.append(edge_to_dict(G, u, v))

    return {"nodes": nodes, "edges": edges}


def search_nodes(G, query, limit=20):
    """Search nodes by label or entity type."""
    query_lower = query.lower()
    results = []
    for n in G.nodes():
        data = G.nodes[n]
        label = str(data.get("label", "")).lower()
        entity = str(data.get("entity", "")).lower()
        node_id_lower = n.lower()
        if query_lower in label or query_lower in entity or query_lower in node_id_lower:
            results.append(node_to_dict(G, n))
            if len(results) >= limit:
                break
    return results
