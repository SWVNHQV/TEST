from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
import streamlit as st


# ---------------------------------------------------------------------------
# Secrets / VW Group LLMaaS
# ---------------------------------------------------------------------------

def _secret(name: str, default=None):
    """Read Streamlit Cloud Secrets first, then local environment variables."""
    try:
        value = st.secrets.get(name)
        if value not in (None, ""):
            return value
    except Exception:
        pass
    return os.getenv(name, default)


VW_TOKEN_URL = "https://idp.cloud.vwgroup.com/auth/realms/kums-mfa/protocol/openid-connect/token"


def enabled() -> bool:
    """Return True when the verified VW Group LLMaaS credentials are available."""
    return all(
        _secret(name)
        for name in (
            "VW_IDP_CLIENT_ID",
            "VW_IDP_CLIENT_SECRET",
            "LLM_API_CLIENT_ID",
        )
    )


def get_token() -> str:
    """Get the temporary VW Group IDP access token."""
    client_id = _secret("VW_IDP_CLIENT_ID")
    client_secret = _secret("VW_IDP_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError(
            "VW Group IDP credentials are missing. Configure "
            "VW_IDP_CLIENT_ID and VW_IDP_CLIENT_SECRET in Streamlit Secrets."
        )

    response = httpx.post(
        VW_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
        timeout=30.0,
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("VW Group IDP did not return an access token.")
    return token


def _client():
    """Create the OpenAI-compatible VW Group LLMaaS client."""
    from openai import OpenAI

    if not enabled():
        raise RuntimeError("VW Group LLMaaS credentials are not configured.")

    token = get_token()
    key = _secret("LLM_API_CLIENT_ID")
    base_url = _secret("LLM_API_BASE_URL", "https://llmapi.ai.vwgroup.com")

    return OpenAI(
        api_key=token,
        base_url=base_url,
        default_headers={"X-LLM-API-CLIENT-ID": f"Bearer {key}"},
    )


def _chat(prompt: str, model: str | None = None, temperature: float = 0.0) -> str:
    """Call the verified VW Group chat-completions endpoint."""
    model = model or _secret("OPENAI_MODEL", "gpt-4o")
    client = _client()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        stream=False,
        temperature=temperature,
    )
    return (response.choices[0].message.content or "").strip()


# ---------------------------------------------------------------------------
# Shared system prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are the Root-Cause Analyst and Warehouse Copilot for IntelliWarehouse AI.

You work only from the supplied Excel/SAP-style warehouse evidence.

Core rules:
1. Use ONLY supplied evidence.
2. Never invent quantities, IDs, dates, vendors, statuses, relationships, or events.
3. Preserve exact workbook values, IDs, field names, dates, and units.
4. For counts, totals, averages, comparisons, rankings, and date logic, calculate from
   the supplied workbook records.
5. Treat the connected workbook records as the source of truth.
6. Distinguish confirmed facts, deterministic calculations, and inference.
7. Never treat a calculated quantity as a physical fact unless the workbook supports it.
8. Recommendations are proposals only; never claim an action was executed.
9. If the evidence is insufficient, say exactly what is missing.
10. Answer the operator's actual question directly. Do not answer a different question.
11. Never import unrelated DQ/anomaly findings into a general question.
12. Keep answers concise, operational, and evidence-grounded.
"""


# ---------------------------------------------------------------------------
# Workbook loading
# ---------------------------------------------------------------------------

def _load_copilot_workbook():
    """Load the complete operational six-sheet workbook."""
    import pandas as pd

    candidates = [
        Path(__file__).with_name("Warehouse_AI_Hackathon_Synthetic_Dataset_FINAL 2.xlsx"),
        Path(__file__).with_name("Warehouse_AI_Hackathon_Synthetic_Dataset_FINAL_2.xlsx"),
    ]

    workbook = next((p for p in candidates if p.exists()), None)
    if workbook is None:
        return {}

    try:
        sheets = pd.read_excel(workbook, sheet_name=None)
    except Exception:
        return {}

    wanted = {
        "Material_Master",
        "Inventory_Stock",
        "Warehouse_Bin",
        "Deliveries_Dispatch",
        "Purchase_Replenish",
        "Vendor_Master",
    }
    return {k: v for k, v in sheets.items() if k in wanted}


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _norm(value) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def _display(value):
    if value is None:
        return "blank"
    try:
        import pandas as pd

        if pd.isna(value):
            return "blank"
    except Exception:
        pass
    return str(value)


def _finding_evidence(row):
    ev = row.get("evidence", {}) if isinstance(row, dict) else {}
    return ev if isinstance(ev, dict) else {}


def _extract_ids(question):
    return set(
        re.findall(
            r"\b[A-Z]{2,10}-\d{3,10}[A-Z]?\b",
            str(question).upper(),
        )
    )


def _rows_for_entity(data, entity):
    """Return rows connected to material/vendor/delivery/PO IDs."""
    result = {}
    if not entity:
        return result

    entities = {x.strip().upper() for x in str(entity).split("|") if x.strip()}
    for sheet, df in data.items():
        if df is None or df.empty:
            continue

        masks = []

        for col in ("Material", "Assigned Material", "Vendor", "Delivery", "Purchase Order"):
            if col in df.columns:
                masks.append(
                    df[col].astype(str).str.strip().str.upper().isin(entities)
                )

        if not masks:
            continue

        mask = masks[0]
        for extra in masks[1:]:
            mask = mask | extra

        matched = df.loc[mask]
        if not matched.empty:
            result[sheet] = matched.to_dict("records")

    return result


def _format_records(records, max_rows=12):
    lines = []
    for sheet, rows in records.items():
        lines.append(f"### {sheet} ({len(rows)} linked rows)")
        for row in rows[:max_rows]:
            compact = " · ".join(
                f"{k}={_display(v)}" for k, v in row.items()
            )
            lines.append(f"- {compact}")
        if len(rows) > max_rows:
            lines.append(f"- ... {len(rows) - max_rows} more rows")
        lines.append("")
    return "\n".join(lines)


def _specific_finding(question, dq, anomalies=None):
    """Resolve an exact DQ-/AN- ID without using unrelated findings."""
    ids = _extract_ids(question)
    dq = dq if dq is not None else []
    anomalies = anomalies if anomalies is not None else []

    for rows in (dq.to_dict("records") if hasattr(dq, "to_dict") else dq,
                 anomalies.to_dict("records") if hasattr(anomalies, "to_dict") else anomalies):
        for row in rows:
            issue_id = str(row.get("issue_id", "")).upper()
            if issue_id and issue_id in ids:
                return row
    return None


# ---------------------------------------------------------------------------
# Deterministic general-question engine
# ---------------------------------------------------------------------------

def _deterministic_general_answer(question: str, data: dict) -> str | None:
    """
    Safely answer common quantitative/status questions directly from the workbook.
    Return None when the question needs general LLM interpretation.
    """
    import pandas as pd

    q = str(question).strip()
    qn = _norm(q)
    if not q or not data:
        return None

    inventory = data.get("Inventory_Stock")
    deliveries = data.get("Deliveries_Dispatch")
    pos = data.get("Purchase_Replenish")
    materials = data.get("Material_Master")
    vendors = data.get("Vendor_Master")
    bins = data.get("Warehouse_Bin")

    # Entity counts.
    if any(k in qn for k in ("howmanymaterials", "numberofmaterials", "countofmaterials")):
        return f"### Answer\nThere are **{len(materials) if materials is not None else 0} material master records** in the workbook."

    if any(k in qn for k in ("howmanyvendors", "numberofvendors", "countofvendors")):
        return f"### Answer\nThere are **{len(vendors) if vendors is not None else 0} vendor master records** in the workbook."

    if any(k in qn for k in ("howmanydeliveries", "numberofdeliveries", "countofdeliveries")):
        return f"### Answer\nThere are **{len(deliveries) if deliveries is not None else 0} delivery records** in the workbook."

    if any(k in qn for k in ("howmanypurchaseorders", "howmanypos", "numberofpurchaseorders", "countofpurchaseorders")):
        return f"### Answer\nThere are **{len(pos) if pos is not None else 0} purchase-order records** in the workbook."

    # "Still in delivery" / open operational deliveries.
    asks_in_delivery = (
        ("delivery" in qn or "deliveries" in qn)
        and any(term in qn for term in ("still", "pending", "open", "progress", "outstanding", "remaining"))
        and any(term in qn for term in ("item", "items", "unit", "units", "quantity", "qty", "howmany", "howmuch", "count"))
    )
    if asks_in_delivery and deliveries is not None and not deliveries.empty and {"Status", "Order Qty"}.issubset(deliveries.columns):
        status = deliveries["Status"].astype(str).str.strip().str.upper()
        qty = pd.to_numeric(deliveries["Order Qty"], errors="coerce").fillna(0)
        completed = {"DELIVERED", "GI-DONE"}
        active = deliveries.loc[~status.isin(completed)].copy()

        status_summary = (
            active.assign(_qty=qty.loc[active.index])
            .groupby(status.loc[active.index])
            .agg(records=("Status", "size"), units=("_qty", "sum"))
            .reset_index()
            .rename(columns={"Status": "Status"})
        )

        lines = [
            "### Answer",
            f"There are **{len(active)} in-progress delivery records** totaling **{int(active['Order Qty'].map(pd.to_numeric, errors='coerce').fillna(0).sum()):,} units**.",
            "",
            "### Active delivery status",
        ]
        for _, r in status_summary.iterrows():
            lines.append(f"- **{r['Status']}**: {int(r['records'])} records / {int(r['units']):,} units")
        lines.append("")
        lines.append("Completed statuses excluded: DELIVERED, GI-DONE.")
        return "\n".join(lines)

    # Overdue deliveries relative to fixed project snapshot.
    if "overdue" in qn and "deliver" in qn and deliveries is not None and not deliveries.empty:
        if {"Planned GI Date", "Status"}.issubset(deliveries.columns):
            snapshot = pd.Timestamp("2026-09-05")
            planned = pd.to_datetime(deliveries["Planned GI Date"], errors="coerce")
            status = deliveries["Status"].astype(str).str.upper()
            active = ~status.isin({"DELIVERED", "GI-DONE"})
            overdue = deliveries.loc[active & planned.notna() & (planned < snapshot)]
            total_qty = 0
            if "Order Qty" in overdue.columns:
                total_qty = int(pd.to_numeric(overdue["Order Qty"], errors="coerce").fillna(0).sum())
            return (
                "### Answer\n"
                f"There are **{len(overdue)} overdue active delivery records**, totaling **{total_qty:,} units** "
                f"as of the **2026-09-05 snapshot**."
            )

    # Expired inventory.
    if "expired" in qn and ("inventory" in qn or "stock" in qn) and inventory is not None:
        if {"Batch Expiry", "Qty On Hand"}.issubset(inventory.columns):
            snapshot = pd.Timestamp("2026-09-05")
            expiry = pd.to_datetime(inventory["Batch Expiry"], errors="coerce")
            qty = pd.to_numeric(inventory["Qty On Hand"], errors="coerce").fillna(0)
            expired = inventory.loc[(expiry < snapshot) & (qty > 0)].copy()
            total = int(pd.to_numeric(expired["Qty On Hand"], errors="coerce").fillna(0).sum())
            lines = [
                "### Answer",
                f"There are **{len(expired)} expired inventory records**, totaling **{total:,} units** as of the **2026-09-05 snapshot**.",
                "",
                "### Expired inventory",
            ]
            cols = [c for c in ("Material", "Plant", "Qty On Hand", "Batch Expiry") if c in expired.columns]
            for _, row in expired.sort_values("Batch Expiry").iterrows():
                lines.append(
                    "- " + " · ".join(f"**{c}**={_display(row[c])}" for c in cols)
                )
            return "\n".join(lines)

    # Negative stock.
    if ("negative" in qn or "negativestock" in qn) and ("stock" in qn or "inventory" in qn) and inventory is not None:
        if "Qty On Hand" in inventory.columns:
            qty = pd.to_numeric(inventory["Qty On Hand"], errors="coerce")
            rows = inventory.loc[qty < 0].copy()
            total = int(abs(qty.loc[rows.index].fillna(0).sum()))
            return (
                "### Answer\n"
                f"There are **{len(rows)} inventory records with negative Qty On Hand**, "
                f"with **{total:,} units of negative on-hand quantity in absolute terms**."
            )

    # Blocked vendors.
    if "vendor" in qn and "block" in qn and vendors is not None and "Procurement Block" in vendors.columns:
        block = vendors["Procurement Block"].astype(str).str.strip().str.upper().eq("Y")
        rows = vendors.loc[block]
        if "Vendor" in rows.columns and "Vendor Name" in rows.columns:
            items = [f"**{r['Vendor']}** ({r['Vendor Name']})" for _, r in rows.iterrows()]
            return "### Answer\nThe procurement-blocked vendors are:\n" + "\n".join(f"- {x}" for x in items)

    # Over-capacity bins.
    if ("overcapacity" in qn or ("over" in qn and "capacity" in qn)) and bins is not None:
        if {"Capacity", "Occupied"}.issubset(bins.columns):
            cap = pd.to_numeric(bins["Capacity"], errors="coerce")
            occ = pd.to_numeric(bins["Occupied"], errors="coerce")
            rows = bins.loc[occ > cap].copy()
            excess = (occ.loc[rows.index] - cap.loc[rows.index]).sum()
            return (
                "### Answer\n"
                f"There are **{len(rows)} over-capacity warehouse bins**, with "
                f"**{int(excess):,} units of total excess occupancy**."
            )

    return None


# ---------------------------------------------------------------------------
# Root Cause / exact finding explanation
# ---------------------------------------------------------------------------

def generate_root_cause(case: dict, model: str | None = None) -> str:
    """Generate one AI-only RCA brief from the selected correlated case."""
    if not enabled():
        raise RuntimeError(
            "VW Group LLMaaS is not configured. RCA generation requires the live LLM."
        )

    prompt = f"""
Analyze exactly ONE correlated warehouse case.

CASE EVIDENCE:
{json.dumps(case, indent=2, default=str)}

Use the linked workbook records in the case as the source of truth.

Write exactly these sections:
### Root Cause
### Evidence Chain
### Business Impact
### Recommended Action
### Confidence

Requirements:
- Explain the primary causal mechanism first.
- Use exact values and IDs from the supplied evidence.
- Explicitly name the source sheet and record/field values in Evidence Chain.
- Distinguish confirmed facts from inference.
- Do not repeat unrelated findings.
- Do not invent any record or relationship.
- Keep the response concise and manager-ready.
"""
    return _chat(prompt, model=model)


def explain_finding(context: dict, model: str | None = None) -> str:
    """Explain exactly one selected DQ/anomaly finding and nothing else."""
    if not enabled():
        raise RuntimeError(
            "VW Group LLMaaS is not configured. Finding explanation requires the live LLM."
        )

    selected = context.get("selected_finding", context.get("finding", context))
    exact_id = selected.get("issue_id", "") if isinstance(selected, dict) else ""

    # Only exact selected finding + connected workbook records.
    payload = {
        "selected_finding": selected,
        "connected_workbook_records": context.get(
            "connected_workbook_records",
            context.get("direct_workbook_records", {}),
        ),
    }

    prompt = f"""
Explain ONE warehouse data-quality/inventory-process finding.

Selected finding ID: {exact_id}

Evidence:
{json.dumps(payload, indent=2, default=str)}

STRICT SCOPE:
- Explain ONLY the selected finding {exact_id}.
- Do not mention other DQ- or AN- IDs.
- Do not produce a list/table of other findings.
- Use only the selected finding and its connected workbook records.
- Do not infer causality beyond what the evidence supports.
- Preserve exact quantities, dates, IDs, fields, material, plant and status values.

Write exactly:
### Finding
### Exact Evidence
### Why It Matters
### Related Operational Risk
### Safest Next Step
### Summary
"""
    answer = _chat(prompt, model=model)

    # Defensive cleanup: prevent accidental unrelated issue IDs from leaking.
    if exact_id:
        ids = set(re.findall(r"\b(?:DQ|AN)-\d+\b", answer.upper()))
        allowed = exact_id.upper()
        for issue_id in sorted(ids - {allowed}):
            answer = re.sub(
                rf"(?im)^.*\b{re.escape(issue_id)}\b.*(?:\n|$)",
                "",
                answer,
            )
    return re.sub(r"\n{3,}", "\n\n", answer).strip()


# ---------------------------------------------------------------------------
# General Copilot
# ---------------------------------------------------------------------------

def copilot_workbook_answer(question: str, dq, anomalies, data, model: str | None = None) -> str:
    """
    General Copilot.

    Every general question follows the same path:
    1. Safely answer common numeric/status questions directly from the workbook.
    2. Otherwise send the operator question + the COMPLETE six-sheet workbook to the
       VW Group LLMaaS model.
    Exact DQ/AN explanations are handled separately by explain_finding().
    """
    import pandas as pd

    q = str(question or "").strip()
    if not q:
        return "### Answer\nPlease enter a question."

    data = data or {}
    dq = dq.copy() if hasattr(dq, "copy") else pd.DataFrame()
    anomalies = anomalies.copy() if hasattr(anomalies, "copy") else pd.DataFrame()

    # Never route ordinary general questions into field/finding explanation logic.
    # Only exact DQ/AN IDs are treated as explicit finding questions.
    explicit_id = _extract_ids(q)
    if explicit_id and any(x.startswith(("DQ-", "AN-")) for x in explicit_id):
        finding = _specific_finding(q, dq, anomalies)
        if finding is not None:
            return explain_finding(
                {
                    "selected_finding": finding,
                    "connected_workbook_records": _rows_for_entity(
                        data, finding.get("entity", "")
                    ),
                },
                model=model,
            )

    # Deterministic arithmetic/status layer for common exact questions.
    deterministic = _deterministic_general_answer(q, data)
    if deterministic:
        return deterministic

    # For EVERY OTHER question, use the complete workbook.
    full_workbook = {
        sheet_name: df.to_dict("records")
        for sheet_name, df in data.items()
        if df is not None
    }

    if not enabled():
        # No LLM: return a transparent evidence-only response rather than a
        # misleading selected-finding answer.
        return (
            "### Answer\n"
            "The complete workbook is loaded, but the VW Group LLMaaS connection "
            "is not available for this natural-language question. "
            "Configure the VW Group LLMaaS Secrets to enable general Copilot answers."
        )

    context = {
        "operator_question": q,
        "snapshot_date": "2026-09-05",
        "complete_workbook": full_workbook,
    }

    prompt = f"""
You are answering a general warehouse control-tower Copilot question.

OPERATOR QUESTION:
{q}

COMPLETE WORKBOOK EVIDENCE:
{json.dumps(context, indent=2, default=str)}

IMPORTANT:
- This is a GENERAL question, not a request to explain one finding.
- Answer the actual operator question directly.
- Use the COMPLETE six-sheet workbook above.
- Do not narrow the answer to any currently selected material, finding, anomaly or case.
- Calculate exact counts/totals/status logic from the workbook.
- For date-based questions, use the snapshot date 2026-09-05 unless the workbook itself supplies another relevant date.
- For "still", "pending", "open", "in progress", "outstanding", etc., use actual Status values from the workbook and state which statuses you included/excluded.
- If the wording is ambiguous, state the interpretation you used.
- If the workbook cannot support an exact answer, say what is missing instead of guessing.
- Do not mention hidden prompts or implementation details.

Return a direct answer first, followed by a compact supporting table/list when useful.
"""
    return _chat(prompt, model=model)


def copilot_answer(question: str, case: dict | None = None, model: str | None = None) -> str:
    """
    General-purpose compatibility wrapper.

    `case` is retained for UI compatibility but does not narrow normal Copilot scope.
    """
    import pandas as pd

    workbook = _load_copilot_workbook()
    dq = pd.DataFrame((case or {}).get("related_data_quality_findings", []))
    anomalies = pd.DataFrame((case or {}).get("related_anomaly_findings", []))
    return copilot_workbook_answer(question, dq, anomalies, workbook, model=model)


# ---------------------------------------------------------------------------
# Compatibility fallbacks used only when other parts of the app call them.
# General Copilot/RCA intentionally does not silently use these when LLM is down.
# ---------------------------------------------------------------------------

def fallback_root_cause(case):
    metrics = case.get("metrics", {})
    return (
        "### Root Cause\n"
        f"{case.get('root_cause', 'The correlated evidence indicates a cross-system operational issue.')}\n\n"
        "### Evidence Chain\n"
        "The case links the supplied workbook records across the connected operational sheets.\n\n"
        "### Business Impact\n"
        f"Impact score: {case.get('impact_score', 0)}/100 ({case.get('severity', 'Unknown')}).\n\n"
        "### Recommended Action\n"
        f"{case.get('recommended_action', 'Review the linked records and correct the underlying issue.')}\n\n"
        "### Confidence\n"
        "This fallback is only a compatibility function; live RCA generation requires VW Group LLMaaS."
    )


def fallback_copilot(question, case):
    return (
        "### Answer\n"
        "Live Copilot generation is unavailable. Please configure the VW Group LLMaaS credentials."
    )
