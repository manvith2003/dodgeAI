"""
Data ingestion script: reads JSONL files from raw_data/ and creates a SQLite database.
"""
import json
import os
import sqlite3
import sys

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "raw_data", "sap-o2c-data")
DB_PATH = os.path.join(os.path.dirname(__file__), "dodgeai.db")

# Mapping from folder name to table name
TABLE_MAP = {
    "sales_order_headers": "sales_order_headers",
    "sales_order_items": "sales_order_items",
    "sales_order_schedule_lines": "sales_order_schedule_lines",
    "outbound_delivery_headers": "outbound_delivery_headers",
    "outbound_delivery_items": "outbound_delivery_items",
    "billing_document_headers": "billing_document_headers",
    "billing_document_items": "billing_document_items",
    "billing_document_cancellations": "billing_document_cancellations",
    "journal_entry_items_accounts_receivable": "journal_entries",
    "payments_accounts_receivable": "payments",
    "business_partners": "customers",
    "business_partner_addresses": "customer_addresses",
    "customer_company_assignments": "customer_company_assignments",
    "customer_sales_area_assignments": "customer_sales_area_assignments",
    "products": "products",
    "product_descriptions": "product_descriptions",
    "product_plants": "product_plants",
    "product_storage_locations": "product_storage_locations",
    "plants": "plants",
}


def flatten_value(val):
    """Flatten nested dicts/lists to JSON strings for SQLite storage."""
    if isinstance(val, (dict, list)):
        return json.dumps(val)
    return val


def read_jsonl_folder(folder_path):
    """Read all JSONL files in a folder and return list of records."""
    records = []
    for fname in sorted(os.listdir(folder_path)):
        if not fname.endswith(".jsonl"):
            continue
        fpath = os.path.join(folder_path, fname)
        with open(fpath, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def infer_schema(records):
    """Infer SQLite column types from sample records."""
    if not records:
        return {}
    # Collect all keys across all records
    all_keys = {}
    for rec in records[:50]:  # Sample first 50
        for k, v in rec.items():
            if k not in all_keys:
                all_keys[k] = type(v)
    return all_keys


def create_table(conn, table_name, records):
    """Create table and insert records."""
    if not records:
        return 0

    schema = infer_schema(records)
    # All columns are TEXT for simplicity (SQLite is type-flexible)
    columns = list(schema.keys())
    col_defs = ", ".join(f'"{col}" TEXT' for col in columns)
    
    conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    conn.execute(f'CREATE TABLE "{table_name}" ({col_defs})')

    # Insert records
    placeholders = ", ".join(["?"] * len(columns))
    col_names = ", ".join(f'"{c}"' for c in columns)
    insert_sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'

    rows = []
    for rec in records:
        row = tuple(flatten_value(rec.get(col)) for col in columns)
        rows.append(row)

    conn.executemany(insert_sql, rows)
    return len(rows)


def create_indices(conn):
    """Create indices for fast lookups and joins."""
    indices = [
        ("idx_soh_salesorder", "sales_order_headers", "salesOrder"),
        ("idx_soh_soldtoparty", "sales_order_headers", "soldToParty"),
        ("idx_soi_salesorder", "sales_order_items", "salesOrder"),
        ("idx_soi_material", "sales_order_items", "material"),
        ("idx_sosl_salesorder", "sales_order_schedule_lines", "salesOrder"),
        ("idx_odh_delivery", "outbound_delivery_headers", "deliveryDocument"),
        ("idx_odi_delivery", "outbound_delivery_items", "deliveryDocument"),
        ("idx_odi_refsd", "outbound_delivery_items", "referenceSdDocument"),
        ("idx_bdh_billing", "billing_document_headers", "billingDocument"),
        ("idx_bdi_billing", "billing_document_items", "billingDocument"),
        ("idx_bdi_refsd", "billing_document_items", "referenceSdDocument"),
        ("idx_je_accdoc", "journal_entries", "accountingDocument"),
        ("idx_je_refdoc", "journal_entries", "referenceDocument"),
        ("idx_pay_accdoc", "payments", "accountingDocument"),
        ("idx_pay_invref", "payments", "invoiceReference"),
        ("idx_cust_bp", "customers", "businessPartner"),
        ("idx_cust_customer", "customers", "customer"),
        ("idx_addr_bp", "customer_addresses", "businessPartner"),
        ("idx_prod_product", "products", "product"),
        ("idx_proddesc_product", "product_descriptions", "product"),
        ("idx_prodplant_product", "product_plants", "product"),
        ("idx_prodplant_plant", "product_plants", "plant"),
        ("idx_prodstor_product", "product_storage_locations", "product"),
        ("idx_plant_plant", "plants", "plant"),
    ]

    for idx_name, table, col in indices:
        try:
            conn.execute(f'CREATE INDEX IF NOT EXISTS "{idx_name}" ON "{table}" ("{col}")')
        except Exception as e:
            print(f"  Warning: Could not create index {idx_name}: {e}")


def ingest():
    """Main ingestion function."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    total_records = 0
    for folder_name, table_name in TABLE_MAP.items():
        folder_path = os.path.join(RAW_DATA_DIR, folder_name)
        if not os.path.isdir(folder_path):
            print(f"  Skipping {folder_name} (not found)")
            continue

        records = read_jsonl_folder(folder_path)
        count = create_table(conn, table_name, records)
        total_records += count
        print(f"  {table_name}: {count} records")

    create_indices(conn)
    conn.commit()

    # Print summary
    print(f"\nTotal: {total_records} records ingested into {DB_PATH}")

    # Print table list
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tables: {', '.join(tables)}")

    conn.close()


if __name__ == "__main__":
    print("Ingesting SAP O2C data into SQLite...")
    ingest()
    print("Done!")
