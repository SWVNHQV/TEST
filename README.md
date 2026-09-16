# IntelliWarehouse AI

Hackathon-ready warehouse AI control tower built around the supplied synthetic SAP-style warehouse workbook.

## Product workspaces

- **Overview** — warehouse health at a glance, investigation status, and the FIND → UNDERSTAND → DECIDE workflow.
- **Data Quality** — review data-quality findings, filter by severity/entity, inspect a selected finding, and use **Explain a finding** for an evidence-grounded AI explanation.
- **Inventory & Process** — review operational/process anomalies and use **Explain an inventory / process anomaly** for an explanation focused on the selected anomaly.
- **Correlated Cases** — review cross-system cases created from linked material, inventory, warehouse, delivery, purchase, and vendor evidence.
- **Root Cause AI** — generate one AI-generated decision brief for the selected correlated case.
- **Trace Graph** — trace one material across master data, inventory, warehouse bins, deliveries, purchase orders, and vendors.
- **Approvals** — human approval gate for proposed actions; actions are approved, rejected, or simulated and retained in the audit trail.
- **Copilot** — general-purpose natural-language warehouse Q&A over the complete operational workbook.
- **Data Explorer** — inspect operational/master workbook records and export a selected sheet.
- **Audit** — review human decisions and simulated actions recorded during the session.

## Core architecture

Excel workbook
→ Ingestion
→ Data Quality Agent
→ Anomaly Agent
→ Relationship / Correlation Agent
→ Root Cause AI
→ Impact scoring
→ Action / Remediation Agent
→ Human Approval
→ Simulated Execution
→ Audit Trail

## Workbook coverage

Operational/master sheets:

- Material_Master
- Inventory_Stock
- Warehouse_Bin
- Deliveries_Dispatch
- Purchase_Replenish
- Vendor_Master

Documentation sheets:

- README
- Data_Dictionary

The app loads the workbook and exposes operational sheets in Data Explorer.

## What the system detects

### Master-data findings

- missing Base UoM
- missing / negative Reorder Point
- ROP below Safety Stock
- duplicate material descriptions
- orphan material references
- obsolete/blocked lifecycle still active downstream
- blocked vendor with active PO
- hazmat/storage handling mismatch

### Operational anomalies

- negative stock
- expired batches
- stale/dead stock
- bin over-capacity
- overdue active deliveries
- missing route
- delivery demand > physical available stock
- overdue purchase orders

## Cross-system correlation

Cases use workbook relationships based on actual keys such as:

- Material
- Plant
- Assigned Material
- Delivery
- Purchase Order
- Vendor

A correlated case can connect evidence across:

Material_Master → Inventory_Stock → Warehouse_Bin → Deliveries_Dispatch → Purchase_Replenish → Vendor_Master

## AI / VW Group LLMaaS

`llm.py` uses the verified VW Group LLMaaS flow:

1. Read VW Group IDP client credentials from Streamlit Secrets.
2. Request a temporary access token from the VW Group identity provider.
3. Create an OpenAI-compatible client against the VW Group LLMaaS base URL.
4. Send the `X-LLM-API-CLIENT-ID` header.
5. Use the configured chat model for Root Cause AI, exact finding/anomaly explanations, and general Copilot responses.

Recommended Streamlit Secrets:

```toml
VW_IDP_CLIENT_ID = "..."
VW_IDP_CLIENT_SECRET = "..."
LLM_API_CLIENT_ID = "..."
LLM_API_BASE_URL = "https://llmapi.ai.vwgroup.com"
OPENAI_MODEL = "gpt-4o"
```

Do not commit real credentials to source control.

## AI response behavior

### Root Cause AI

The selected correlated case is sent to the LLM with its connected workbook evidence. The AI generates one decision brief with:

- Root Cause
- Evidence Chain
- Business Impact
- Recommended Action
- Confidence

The RCA page is intended to show the live AI-generated analysis rather than the deterministic case narrative as the displayed RCA.

### Explain a finding / Explain an anomaly

These flows are intentionally scoped to the selected DQ or anomaly. The response should focus on that exact finding/anomaly and its directly connected workbook evidence so unrelated findings are not mixed into the explanation.

### General Copilot

General Copilot is separate from the exact-finding explanation flows. It answers natural-language questions using the **complete six-sheet operational workbook** as its primary evidence source.

For questions requiring counts, totals, comparisons, or date logic, the app calculates from the supplied workbook records when deterministic handling is available. Other general questions are passed to the VW Group LLMaaS model with the complete workbook context.

General Copilot can answer questions about:

- materials and material master attributes
- inventory and stock quantities
- warehouse bins and capacity
- deliveries and delivery status
- purchase orders and replenishment
- vendors and procurement status
- data-quality and anomaly findings
- workbook-wide operational questions

## UI / presentation

The app uses the supplied warehouse background image as the visual theme. AI-generated answers are rendered on opaque/light content surfaces so the background does not interfere with readability.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Demo flow

1. Open **Overview**.
2. Review Data Quality, Inventory & Process, correlated cases, and pending approvals.
3. Open **Data Quality** and explain a selected finding.
4. Open **Inventory & Process** and explain a selected anomaly.
5. Open **Correlated Cases** and select a high-impact case.
6. Open **Root Cause AI** and click **Generate AI explanation**.
7. Review the AI-generated decision brief and supporting records.
8. Open **Approvals**, review or edit the proposed action, and Approve, Reject, or Simulate Execute.
9. Open **Audit** to review the governed decision trail.
10. Use **Copilot** for workbook-wide natural-language questions.

## Governance

No live ERP/SAP write-back is implemented. Corrective actions remain proposals and simulated actions. Human approval is required before a case is marked Approved, and decisions/simulations are recorded in the session audit trail.
