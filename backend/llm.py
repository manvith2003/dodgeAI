"""
LLM integration module: translates natural language to SQL using Google Gemini.
Includes guardrails, query execution, and response formatting.
"""
import json
import os
import re
import sqlite3
from typing import Optional

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), "dodgeai.db")

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Database schema description for the LLM
DB_SCHEMA = """
You have access to a SQLite database containing SAP Order-to-Cash (O2C) business data. Here are the tables:

1. sales_order_headers (100 rows) - Sales orders
   Columns: salesOrder (PK), salesOrderType, salesOrganization, distributionChannel, organizationDivision, salesGroup, salesOffice, soldToParty (FK→customers.customer), creationDate, createdByUser, lastChangeDateTime, totalNetAmount, overallDeliveryStatus, overallOrdReltdBillgStatus, overallSdDocReferenceStatus, transactionCurrency, pricingDate, requestedDeliveryDate, headerBillingBlockReason, deliveryBlockReason, incotermsClassification, incotermsLocation1, customerPaymentTerms, totalCreditCheckStatus

2. sales_order_items (167 rows) - Line items within sales orders
   Columns: salesOrder (FK→sales_order_headers), salesOrderItem, salesOrderItemCategory, material (FK→products.product), requestedQuantity, requestedQuantityUnit, transactionCurrency, netAmount, materialGroup, productionPlant, storageLocation, salesDocumentRjcnReason, itemBillingBlockReason

3. sales_order_schedule_lines (179 rows) - Delivery schedule for order items
   Columns: salesOrder, salesOrderItem, scheduleLine, confirmedDeliveryDate, orderQuantityUnit, confdOrderQtyByMatlAvailCheck

4. outbound_delivery_headers (86 rows) - Delivery documents
   Columns: actualGoodsMovementDate, actualGoodsMovementTime, creationDate, creationTime, deliveryBlockReason, deliveryDocument (PK), hdrGeneralIncompletionStatus, headerBillingBlockReason, lastChangeDate, overallGoodsMovementStatus, overallPickingStatus, overallProofOfDeliveryStatus, shippingPoint

5. outbound_delivery_items (137 rows) - Line items in deliveries
   Columns: actualDeliveryQuantity, batch, deliveryDocument (FK→outbound_delivery_headers), deliveryDocumentItem, deliveryQuantityUnit, itemBillingBlockReason, lastChangeDate, plant (FK→plants.plant), referenceSdDocument (FK→sales_order_headers.salesOrder), referenceSdDocumentItem, storageLocation

6. billing_document_headers (163 rows) - Billing/Invoice documents
   Columns: billingDocument (PK), billingDocumentType, creationDate, creationTime, lastChangeDateTime, billingDocumentDate, billingDocumentIsCancelled, cancelledBillingDocument, totalNetAmount, transactionCurrency, companyCode, fiscalYear, accountingDocument, soldToParty (FK→customers.customer)

7. billing_document_items (245 rows) - Line items in billing docs
   Columns: billingDocument (FK→billing_document_headers), billingDocumentItem, material (FK→products.product), billingQuantity, billingQuantityUnit, netAmount, transactionCurrency, referenceSdDocument (FK→sales_order_headers.salesOrder), referenceSdDocumentItem

8. billing_document_cancellations (80 rows) - Cancelled billing docs
   Columns: billingDocument, billingDocumentType, creationDate, creationTime, lastChangeDateTime, billingDocumentDate, billingDocumentIsCancelled, cancelledBillingDocument, totalNetAmount, transactionCurrency, companyCode, fiscalYear, accountingDocument, soldToParty

9. journal_entries (123 rows) - Accounting journal entries linked to billing
   Columns: companyCode, fiscalYear, accountingDocument (PK), glAccount, referenceDocument (FK→billing_document_headers.billingDocument), costCenter, profitCenter, transactionCurrency, amountInTransactionCurrency, companyCodeCurrency, amountInCompanyCodeCurrency, postingDate, documentDate, accountingDocumentType, accountingDocumentItem, assignmentReference, lastChangeDateTime, customer, financialAccountType, clearingDate, clearingAccountingDocument, clearingDocFiscalYear

10. payments (120 rows) - Payment records for accounts receivable
    Columns: companyCode, fiscalYear, accountingDocument (PK), accountingDocumentItem, clearingDate, clearingAccountingDocument, clearingDocFiscalYear, amountInTransactionCurrency, transactionCurrency, amountInCompanyCodeCurrency, companyCodeCurrency, customer, invoiceReference (FK→billing_document_headers.billingDocument), invoiceReferenceFiscalYear, salesDocument, salesDocumentItem, postingDate, documentDate, assignmentReference, glAccount, financialAccountType, profitCenter, costCenter

11. customers (8 rows) - Business partner/customer master data
    Columns: businessPartner, customer (PK), businessPartnerCategory, businessPartnerFullName, businessPartnerGrouping, businessPartnerName, correspondenceLanguage, createdByUser, creationDate, creationTime, firstName, formOfAddress, industry, lastChangeDate, lastName, organizationBpName1, organizationBpName2, businessPartnerIsBlocked, isMarkedForArchiving

12. customer_addresses (8 rows) - Customer address details
    Columns: businessPartner (FK→customers.businessPartner), addressId, validityStartDate, validityEndDate, addressUuid, addressTimeZone, cityName, country, poBox, poBoxDeviatingCityName, poBoxDeviatingCountry, poBoxDeviatingRegion, poBoxIsWithoutNumber, poBoxLobbyName, poBoxPostalCode, postalCode, region, streetName, taxJurisdiction, transportZone

13. customer_company_assignments (8 rows)
    Columns: customer, companyCode, accountingClerk, accountingClerkFaxNumber, accountingClerkInternetAddress, accountingClerkPhoneNumber, alternativePayerAccount, paymentBlockingReason, paymentMethodsList, paymentTerms, reconciliationAccount, deletionIndicator, customerAccountGroup

14. customer_sales_area_assignments (28 rows)
    Columns: customer, salesOrganization, distributionChannel, division, billingIsBlockedForCustomer, completeDeliveryIsDefined, creditControlArea, currency, customerPaymentTerms, deliveryPriority, incotermsClassification, incotermsLocation1, salesGroup, salesOffice, shippingCondition, slsUnlmtdOvrdelivIsAllwd, supplyingPlant, salesDistrict, exchangeRateType

15. products (69 rows) - Product master data
    Columns: product (PK), productType, crossPlantStatus, crossPlantStatusValidityDate, creationDate, createdByUser, lastChangeDate, lastChangeDateTime, isMarkedForDeletion, productOldId, grossWeight, weightUnit, netWeight, productGroup, baseUnit, division, industrySector

16. product_descriptions (69 rows) - Product text descriptions
    Columns: product (FK→products.product), language, productDescription

17. product_plants (3036 rows) - Product-plant assignments
    Columns: product (FK→products.product), plant (FK→plants.plant), countryOfOrigin, regionOfOrigin, productionInvtryManagedLoc, availabilityCheckType, fiscalYearVariant, profitCenter, mrpType

18. product_storage_locations (16723 rows) - Storage location details
    Columns: product, plant, storageLocation, physicalInventoryBlockInd, dateOfLastPostedCntUnRstrcdStk

19. plants (44 rows) - Plant/warehouse master data
    Columns: plant (PK), plantName, valuationArea, plantCustomer, plantSupplier, factoryCalendar, defaultPurchasingOrganization, salesOrganization, addressId, plantCategory, distributionChannel, division, language, isMarkedForArchiving

KEY RELATIONSHIPS (Order-to-Cash flow):
- Sales Order → Sales Order Items (salesOrder)
- Sales Order Items → Products (material = product)
- Sales Order → Customer (soldToParty = customer)
- Sales Order → Delivery (outbound_delivery_items.referenceSdDocument = salesOrder)
- Delivery → Delivery Items (deliveryDocument)
- Delivery Items → Plants (plant)
- Sales Order → Billing Document (billing_document_items.referenceSdDocument = salesOrder)
- Billing Document → Billing Items (billingDocument)
- Billing Document → Journal Entry (journal_entries.referenceDocument = billingDocument)
- Journal Entry → Payment (payments.clearingAccountingDocument = journal_entries.accountingDocument OR payments.invoiceReference = billingDocument)
- Customer → Address (businessPartner)
- Product → Plant (product_plants)
"""

SYSTEM_PROMPT = f"""You are Dodge AI, a data analysis assistant for the SAP Order-to-Cash (O2C) process. You answer questions ONLY about the provided dataset.

{DB_SCHEMA}

INSTRUCTIONS:
1. When the user asks a question about the data, generate a SQL query to answer it.
2. Return your response in this exact JSON format:
{{
  "thinking": "Brief explanation of your approach",
  "sql": "YOUR SQL QUERY HERE",
  "answer_template": "Template for the natural language answer using {{results}} placeholder"
}}
3. Use only SELECT statements. Never use INSERT, UPDATE, DELETE, DROP, ALTER, or any DDL/DML.
4. Always use double quotes for column/table names if they use camelCase.
5. When tracing flows, JOIN across tables using the documented relationships.
6. For "incomplete flows" queries, use LEFT JOINs to find missing links.
7. Limit results to 50 rows max unless the user asks for all.
8. All values are stored as TEXT in SQLite, so use string comparisons.

GUARDRAILS:
- If the user asks about topics unrelated to this dataset (general knowledge, creative writing, coding help, personal questions, etc.), respond with:
{{
  "thinking": "off_topic",
  "sql": null,
  "answer_template": "This system is designed to answer questions related to the SAP Order-to-Cash dataset only. I can help you with questions about sales orders, deliveries, billing documents, journal entries, payments, customers, products, and plants."
}}
- Do NOT generate answers that are not backed by data from the database.
- Do NOT hallucinate or make up data.
"""


def get_db():
    """Get SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def is_safe_sql(sql: str) -> bool:
    """Check if SQL is read-only (SELECT only)."""
    sql_upper = sql.strip().upper()
    dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "EXEC", "EXECUTE", "ATTACH", "DETACH"]
    for keyword in dangerous:
        # Check if it appears as a standalone keyword (not inside a string)
        if re.search(rf'\b{keyword}\b', sql_upper):
            return False
    return sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")


def execute_sql(sql: str, limit: int = 50) -> dict:
    """Execute SQL query and return results."""
    if not is_safe_sql(sql):
        return {"error": "Query rejected: only SELECT statements are allowed.", "rows": [], "columns": []}

    conn = get_db()
    try:
        # Add LIMIT if not present
        if "LIMIT" not in sql.upper():
            sql = sql.rstrip(";") + f" LIMIT {limit}"

        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return {"rows": rows, "columns": columns, "count": len(rows)}
    except Exception as e:
        return {"error": str(e), "rows": [], "columns": []}
    finally:
        conn.close()


def parse_llm_response(text: str) -> dict:
    """Parse the LLM's JSON response."""
    # Try to extract JSON from the response
    try:
        # Look for JSON block in markdown code block
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        # Try parsing the entire response as JSON
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: try to find JSON-like structure
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
    return {"thinking": "parse_error", "sql": None, "answer_template": text}


async def chat(user_message: str, conversation_history: list = None) -> dict:
    """
    Process a user message and return a data-backed response.
    Returns: {answer, sql, results, referenced_nodes, thinking}
    """
    if not GEMINI_API_KEY:
        return {
            "answer": "Gemini API key not configured. Please set GEMINI_API_KEY in your .env file.",
            "sql": None,
            "results": None,
            "referenced_nodes": [],
            "thinking": "no_api_key",
        }

    # Build conversation messages
    messages = []
    if conversation_history:
        for msg in conversation_history[-10:]:  # Keep last 10 messages for context
            messages.append(msg)

    messages.append({"role": "user", "parts": [user_message]})

    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT,
        )

        response = model.generate_content(
            messages,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=2048,
            ),
        )

        response_text = response.text
        parsed = parse_llm_response(response_text)

        thinking = parsed.get("thinking", "")
        sql = parsed.get("sql")
        answer_template = parsed.get("answer_template", "")

        # Handle off-topic queries
        if thinking == "off_topic" or sql is None:
            return {
                "answer": answer_template or "This system is designed to answer questions related to the SAP Order-to-Cash dataset only.",
                "sql": None,
                "results": None,
                "referenced_nodes": [],
                "thinking": thinking,
            }

        # Execute the SQL
        result = execute_sql(sql)

        if result.get("error"):
            # If SQL fails, ask LLM to fix it
            retry_messages = messages + [
                {"role": "model", "parts": [response_text]},
                {"role": "user", "parts": [
                    f"The SQL query failed with error: {result['error']}. Please fix the SQL query and try again. "
                    f"Remember all column names use camelCase and should be in double quotes. All values are TEXT type."
                ]},
            ]
            retry_response = model.generate_content(
                retry_messages,
                generation_config=genai.types.GenerationConfig(temperature=0.1, max_output_tokens=2048),
            )
            parsed = parse_llm_response(retry_response.text)
            sql = parsed.get("sql")
            answer_template = parsed.get("answer_template", "")
            if sql:
                result = execute_sql(sql)

        # If still error, return it
        if result.get("error"):
            return {
                "answer": f"I encountered an error executing the query: {result['error']}. Could you rephrase your question?",
                "sql": sql,
                "results": None,
                "referenced_nodes": [],
                "thinking": thinking,
            }

        # Format the answer using results
        answer = format_answer(answer_template, result, sql)

        # Extract referenced node IDs from results
        referenced_nodes = extract_node_references(result)

        return {
            "answer": answer,
            "sql": sql,
            "results": result,
            "referenced_nodes": referenced_nodes,
            "thinking": thinking,
        }

    except Exception as e:
        return {
            "answer": f"An error occurred: {str(e)}",
            "sql": None,
            "results": None,
            "referenced_nodes": [],
            "thinking": f"error: {str(e)}",
        }


def format_answer(template: str, result: dict, sql: str) -> str:
    """Format the answer using the template and results."""
    rows = result.get("rows", [])
    count = result.get("count", 0)

    if not rows:
        return "No results found for your query."

    # If template contains {results}, replace with formatted data
    if "{results}" in template:
        if count <= 5:
            formatted = "\n".join(
                [", ".join(f"{k}: {v}" for k, v in row.items()) for row in rows]
            )
        else:
            formatted = "\n".join(
                [", ".join(f"{k}: {v}" for k, v in row.items()) for row in rows[:10]]
            )
            if count > 10:
                formatted += f"\n... and {count - 10} more results."
        return template.replace("{results}", formatted)

    # Otherwise, use the template as is and append key data
    if count == 1:
        row = rows[0]
        details = ", ".join(f"{k}: {v}" for k, v in row.items())
        return f"{template}\n\n{details}"

    return template


def extract_node_references(result: dict) -> list:
    """Extract node IDs that can be highlighted in the graph."""
    refs = set()
    id_fields = {
        "salesOrder": "SalesOrder",
        "deliveryDocument": "Delivery",
        "billingDocument": "BillingDoc",
        "accountingDocument": "JournalEntry",
        "product": "Product",
        "material": "Product",
        "customer": "Customer",
        "soldToParty": "Customer",
        "plant": "Plant",
    }

    for row in result.get("rows", []):
        for field, prefix in id_fields.items():
            val = row.get(field)
            if val:
                refs.add(f"{prefix}:{val}")

    return list(refs)


def get_schema_info() -> dict:
    """Return database schema information for the frontend."""
    conn = get_db()
    tables = {}
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    for table in cursor.fetchall():
        t = table[0]
        info = conn.execute(f'PRAGMA table_info("{t}")').fetchall()
        count = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        tables[t] = {
            "columns": [{"name": r[1], "type": r[2]} for r in info],
            "count": count,
        }
    conn.close()
    return tables
