
from __future__ import annotations
import os, json
import base64
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st

from agents import load_workbook, run_pipeline, SNAPSHOT_DATE
from llm import generate_root_cause, copilot_answer, copilot_workbook_answer, enabled

st.set_page_config(page_title="IntelliWarehouse AI Control Tower", page_icon="◈", layout="wide")

# Load the warehouse image from the same folder as app.py and embed it as base64.
# This is reliable on Streamlit Cloud; CSS cannot reliably resolve a local
# relative file such as url("bg.jpeg") from the browser.
# IMPORTANT: keep bg.jpeg in the same GitHub folder as app.py.
BG_PATH = Path(__file__).parent / "bg.jpeg"
bg_data_uri = ""
if BG_PATH.exists():
    bg_b64 = base64.b64encode(BG_PATH.read_bytes()).decode("utf-8")
    bg_data_uri = f"url('data:image/jpeg;base64,{bg_b64}')"

bg_layer = (
    f"linear-gradient(rgba(238,244,250,.76),rgba(238,244,250,.76)), {bg_data_uri}"
    if bg_data_uri else
    "linear-gradient(#f4f7fb,#f4f7fb)"
)

st.markdown("""
<style>
/* Warehouse image background */
.stApp{{
    background: __BG_LAYER__;
    background-size:cover;
    background-position:center center;
    background-attachment:fixed;
    background-repeat:no-repeat;
}}
.block-container{max-width:1500px;padding-top:1.1rem;padding-bottom:3rem}

/* Keep the background visible without reducing readability */
.main .block-container{background:transparent}


/* Hero */
.hero{
    background:linear-gradient(135deg,#081b3a 0%,#12366d 52%,#2459a8 100%);
    color:white;border-radius:24px;padding:30px 34px;margin-bottom:18px;
    box-shadow:0 12px 30px rgba(8,27,58,.16)
}
.hero h1{font-size:2.35rem;margin:0;font-weight:800;letter-spacing:-.02em}
.hero p{opacity:.82;margin:.45rem 0 0;font-size:1.02rem}

/* Overview */
.section-title{font-size:1.45rem;font-weight:800;color:#172033;margin:4px 0 2px}
.section-subtitle{color:#697386;margin-bottom:16px}
.overview-card{
    background:#fff;border:1px solid #e2e8f0;border-radius:18px;
    padding:18px 18px 16px;min-height:142px;
    box-shadow:0 5px 18px rgba(15,30,60,.055)
}
.overview-card .icon{
    width:36px;height:36px;border-radius:11px;display:flex;
    align-items:center;justify-content:center;font-size:18px;font-weight:800;
    margin-bottom:12px
}
.overview-card .label{font-size:.88rem;color:#667085;font-weight:650}
.overview-card .value{font-size:1.75rem;line-height:1.05;font-weight:850;color:#182235;margin:3px 0 7px}
.overview-card .desc{font-size:.78rem;color:#7a8495;line-height:1.35}
.blue .icon{background:#e7f0ff;color:#2359a8}
.teal .icon{background:#e4f8f5;color:#087f73}
.amber .icon{background:#fff3d8;color:#a66a00}
.purple .icon{background:#f0eaff;color:#6f42c1}
.red .icon{background:#ffe8e7;color:#c23b35}
.green .icon{background:#e5f7eb;color:#24824a}

.health-card{
    background:#fff;border:1px solid #e2e8f0;border-radius:18px;
    padding:17px 19px;box-shadow:0 5px 18px rgba(15,30,60,.045)
}
.health-card .big{font-size:1.7rem;font-weight:850;margin-top:4px}
.health-card .small{font-size:.78rem;color:#737e90}
.health-title{font-weight:750;color:#253047}
.health-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px}
.dot-red{background:#df4b45}.dot-amber{background:#e3a629}.dot-blue{background:#4c78c2}.dot-green{background:#37a56a}

/* Workflow */
.workflow{
    display:flex;align-items:center;gap:10px;flex-wrap:wrap;
    margin:4px 0 2px
}
.workflow-step{
    background:#fff;border:1px solid #e0e6ef;border-radius:14px;
    padding:12px 15px;min-width:135px;box-shadow:0 4px 14px rgba(15,30,60,.04)
}
.workflow-step .num{
    display:inline-flex;width:24px;height:24px;border-radius:50%;
    align-items:center;justify-content:center;background:#e9f0fb;color:#1f4f93;
    font-size:.76rem;font-weight:800;margin-right:7px
}
.workflow-step strong{font-size:.88rem;color:#273249}
.workflow-arrow{color:#98a2b3;font-weight:800}


.overview-note{background:#eef4ff;border:1px solid #d7e3f7;border-radius:14px;padding:12px 15px;color:#52627a;font-size:.86rem;margin:4px 0 18px}
.priority-strip{display:flex;align-items:center;gap:12px;flex-wrap:wrap;background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:12px 15px;color:#52627a;font-size:.88rem;box-shadow:0 3px 12px rgba(15,30,60,.035)}
.priority-strip.ok{background:#eefaf2;border-color:#ccebd7;color:#28633f}
.priority-label{font-weight:800;color:#253047}.priority-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin:0 5px 1px 2px}.priority-dot.red{background:#df4b45}.priority-dot.amber{background:#e3a629}.priority-dot.blue{background:#4c78c2}.priority-sep{color:#c3cad5}
.rca-header{display:flex;justify-content:space-between;align-items:center;gap:20px;background:#fff;border:1px solid #e1e7f0;border-radius:16px;padding:16px 18px;margin:8px 0 12px}.rca-kicker{font-size:.68rem;font-weight:800;letter-spacing:.08em;color:#7a8495}.rca-title{font-size:1.35rem;font-weight:850;color:#182235;line-height:1.15;margin-top:3px}.rca-material{font-size:.86rem;color:#697386;margin-top:4px}.rca-meta{display:flex;gap:7px;align-items:center;flex-wrap:wrap;justify-content:flex-end}.severity-pill,.impact-pill{border-radius:999px;padding:6px 10px;font-size:.78rem;font-weight:800}.severity-pill.critical{background:#ffe8e7;color:#b42318}.severity-pill.high{background:#fff3d8;color:#8a5a00}.severity-pill.medium{background:#eef4ff;color:#315c9d}.impact-pill{background:#f2f4f7;color:#4b5565}.rca-finding{margin-bottom:14px;padding:15px 17px !important;line-height:1.5}.ai-label{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;font-weight:800;color:#6f42c1;margin-bottom:5px}.compact-action{padding:11px 13px !important;font-size:.88rem;line-height:1.4}

/* Existing components */
.card{background:white;border:1px solid #e4e8ef;border-radius:18px;padding:18px;box-shadow:0 5px 20px rgba(15,30,60,.05)}
.kpi{font-size:1.75rem;font-weight:800}.muted{color:#697386;font-size:.86rem}
.chain{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin:12px 0}
.node{background:white;border:1px solid #dfe4ec;border-radius:10px;padding:9px 12px;font-weight:700}
.arrow{color:#8290a5}
.ai{background:#f5f1ff;border:1px solid #ddd2ff;border-radius:16px;padding:18px}
.good{background:#eefaf2;border:1px solid #ccebd7;border-radius:14px;padding:14px}
.warn{background:#fff8e8;border:1px solid #f2dfae;border-radius:14px;padding:14px}

/* Make Streamlit tabs look like a real product navigation bar */
div[data-baseweb="tab-list"]{
    gap:6px;background:#e9eef6;padding:6px;border-radius:15px;
    border:1px solid #dde4ee
}
button[data-baseweb="tab"]{
    border-radius:11px !important;padding:9px 13px !important;
    font-weight:700 !important;color:#4f5b70 !important;
    border:1px solid transparent !important;background:transparent !important;
    display:flex !important;align-items:center !important;gap:7px !important;
}
button[data-baseweb="tab"]::before{
    content:"";display:inline-block;width:21px;height:21px;flex:0 0 21px;
    background-repeat:no-repeat;background-position:center;background-size:19px 19px;
    opacity:.86;
}
button[data-baseweb="tab"]:nth-child(1)::before{
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23235aa6' stroke-width='2'%3E%3Cpath d='M3 11.5 12 4l9 7.5'/%3E%3Cpath d='M5 10v10h14V10M9 20v-6h6v6'/%3E%3C/svg%3E");
}
button[data-baseweb="tab"]:nth-child(2)::before{
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23235aa6' stroke-width='2'%3E%3Cpath d='M4 19V5h16v14z'/%3E%3Cpath d='M7 15h2v2H7zm4-5h2v7h-2zm4-3h2v10h-2z'/%3E%3C/svg%3E");
}
button[data-baseweb="tab"]:nth-child(3)::before{
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%236f42c1' stroke-width='2'%3E%3Cpath d='M9 4a3 3 0 0 1 6 0v2a4 4 0 0 1 0 8v2a3 3 0 0 1-6 0v-2a4 4 0 0 1 0-8z'/%3E%3Cpath d='M6 9h3m6 0h3M6 15h3m6 0h3'/%3E%3C/svg%3E");
}
button[data-baseweb="tab"]:nth-child(4)::before{
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%230b72c9' stroke-width='2'%3E%3Ccircle cx='5' cy='12' r='2'/%3E%3Ccircle cx='19' cy='6' r='2'/%3E%3Ccircle cx='19' cy='18' r='2'/%3E%3Cpath d='m7 11 10-4M7 13l10 4'/%3E%3C/svg%3E");
}
button[data-baseweb="tab"]:nth-child(5)::before{
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%231f8b5b' stroke-width='2'%3E%3Crect x='3' y='3' width='18' height='18' rx='4'/%3E%3Cpath d='m5 12.5 4.5 4.5L19 7.5'/%3E%3C/svg%3E");
}
button[data-baseweb="tab"]:nth-child(6)::before{
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%230b72c9' stroke-width='2'%3E%3Cpath d='M6 8h12a3 3 0 0 1 3 3v4a3 3 0 0 1-3 3H9l-4 3v-6a3 3 0 0 1-2-3v-1a3 3 0 0 1 3-3z'/%3E%3Ccircle cx='8' cy='13' r='1' fill='%230b72c9'/%3E%3Ccircle cx='12' cy='13' r='1' fill='%230b72c9'/%3E%3Ccircle cx='16' cy='13' r='1' fill='%230b72c9'/%3E%3C/svg%3E");
}
button[data-baseweb="tab"]:nth-child(7)::before{
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%233b63a3' stroke-width='2'%3E%3Cellipse cx='12' cy='5' rx='8' ry='3'/%3E%3Cpath d='M4 5v7c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12v7c0 1.7 3.6 3 8 3s8-1.3 8-3v-7'/%3E%3C/svg%3E");
}
button[data-baseweb="tab"]:nth-child(8)::before{
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%235b6577' stroke-width='2'%3E%3Cpath d='M7 3h8l4 4v14H7z'/%3E%3Cpath d='M15 3v5h4M10 13h6M10 17h6'/%3E%3C/svg%3E");
}
button[data-baseweb="tab"][aria-selected="true"]{
    background:rgba(255,255,255,.96) !important;color:#173d78 !important;
    border-color:#d5deeb !important;box-shadow:0 3px 10px rgba(20,45,85,.08)
}
button[data-baseweb="tab"]:hover{color:#173d78 !important;background:#f8fafc !important}
button[data-baseweb="tab"] span{font-size:.95rem}
button[data-baseweb="tab"] p{display:flex;align-items:center;gap:6px}
div[data-baseweb="tab-highlight"]{background:#2b63b7 !important;height:3px !important}

.workspace-hint{display:flex;align-items:center;gap:9px;color:#68758a;font-size:.86rem;margin:4px 0 8px;padding-left:2px}.workspace-hint span{font-size:1rem}

/* Sidebar */
section[data-testid="stSidebar"]{background:#eef3f9}
section[data-testid="stSidebar"] .block-container{padding-top:1.2rem}
.sidebar-brand{
    background:linear-gradient(135deg,#0b1f44,#234a91);color:white;
    border-radius:17px;padding:16px 17px;margin-bottom:16px
}
.sidebar-brand .title{font-weight:800;font-size:1.05rem}
.sidebar-brand .sub{font-size:.76rem;opacity:.78;margin-top:3px}
.status-pill{
    border-radius:12px;padding:11px 13px;margin:8px 0;
    font-weight:700;font-size:.82rem
}
.status-ok{background:#dff4e7;color:#1d7041;border:1px solid #bfe5cd}
.status-warn{background:#fff1d8;color:#8a5a00;border:1px solid #efd59e}
</style>
""".replace("__BG_LAYER__", bg_layer), unsafe_allow_html=True)

if "actions" not in st.session_state: st.session_state.actions={}
if "audit" not in st.session_state: st.session_state.audit=[]
if "ai_cache" not in st.session_state: st.session_state.ai_cache={}

BG_IMAGE = Path(__file__).parent / "bg.jpeg"
if not BG_IMAGE.exists():
    st.warning("Background image bg.jpeg was not found. Upload bg.jpeg next to app.py in the repository.")

st.markdown("""
<div class="hero">
<h1>◈IntelliWarehouse AI Control Tower</h1>
<p>Detect → Correlate → Explain → Impact → Approve</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Control Center")
    default_path = Path(__file__).parent / "Warehouse_AI_Hackathon_Synthetic_Dataset_FINAL_2.xlsx"
    uploaded=st.file_uploader("Upload warehouse workbook",type=["xlsx"])
    path=uploaded if uploaded is not None else default_path
    st.caption("Snapshot: 05 Sep 2026")
    model_name = st.secrets.get('OPENAI_MODEL', os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'))
    if enabled():
        st.success(f"LLM enabled · {model_name}")
    else:
        st.warning("LLM not enabled — deterministic evidence-grounded fallback is active.")
        st.caption("Configure VW Group LLMaaS secrets in Streamlit Cloud → Settings → Secrets.")
    st.divider()
    st.caption("Governance")
    st.caption("Human approval required · Simulated actions · Audit retained")

try:
    raw=load_workbook(path)
    data, graph, dq, anomalies, cases=run_pipeline(raw)
except Exception as e:
    st.error(f"Could not load workbook: {e}")
    st.stop()

# Keep every current RCA case in the human approval queue.
# The default status is Pending; approval/rejection is persisted in session state
# and therefore survives Streamlit reruns. No action is executed automatically.
if cases is not None and not cases.empty:
    current_case_ids = set()
    for _, _case in cases.iterrows():
        _cid = str(_case.get("case_id", "")).strip()
        if not _cid:
            continue
        current_case_ids.add(_cid)
        if _cid not in st.session_state.actions:
            st.session_state.actions[_cid] = {
                "status": "Pending",
                "approver": "",
                "note": "",
                "action": _case.get("recommended_action", "Review the linked records before corrective action."),
            }

def evidence_text(e):
    if not isinstance(e, dict):
        return str(e)
    parts=[]
    for k,v in e.items():
        if isinstance(v, (list,tuple)):
            val=", ".join(map(str,v))
        elif v is None or (not isinstance(v, dict) and pd.isna(v)):
            val="blank"
        else:
            val=str(v)
        parts.append(f"{k}={val}")
    return " · ".join(parts)

def build_finding_context(finding, data, dq, anomalies):
    """Build exact evidence for one DQ/anomaly finding for Copilot."""
    f = finding.to_dict() if hasattr(finding, "to_dict") else dict(finding)
    entity = str(f.get("entity", "")).strip()
    evidence = f.get("evidence", {}) if isinstance(f.get("evidence"), dict) else {}
    import re

    material = None
    if entity.upper().startswith("MAT-"):
        material = entity.split("|")[0].strip()
    elif evidence.get("Material"):
        material = str(evidence["Material"]).strip()
    else:
        ids = re.findall(r"MAT-\d+[A-Z]?", entity.upper())
        if ids:
            material = ids[0]

    connected = {}
    if material:
        for sheet, col in [
            ("Material_Master", "Material"),
            ("Inventory_Stock", "Material"),
            ("Warehouse_Bin", "Assigned Material"),
            ("Deliveries_Dispatch", "Material"),
            ("Purchase_Replenish", "Material"),
        ]:
            df = data.get(sheet, pd.DataFrame())
            if not df.empty and col in df.columns:
                connected[sheet] = df[df[col].astype(str).eq(material)].head(25).to_dict("records")
            else:
                connected[sheet] = []

        po_rows = pd.DataFrame(connected["Purchase_Replenish"])
        vdf = data.get("Vendor_Master", pd.DataFrame())
        if not po_rows.empty and "Vendor" in po_rows.columns and not vdf.empty and "Vendor" in vdf.columns:
            vendors = set(po_rows["Vendor"].astype(str))
            connected["Vendor_Master"] = vdf[vdf["Vendor"].astype(str).isin(vendors)].head(10).to_dict("records")
        else:
            connected["Vendor_Master"] = []
    else:
        connected["Direct Evidence"] = [evidence]

    related = []
    for df in [dq, anomalies]:
        if df is not None and not df.empty:
            for _, r in df.iterrows():
                if str(r.get("issue_id", "")) == str(f.get("issue_id", "")):
                    continue
                if material and material in str(r.get("entity", "")).split("|"):
                    related.append({
                        "issue_id": r.get("issue_id"),
                        "severity": r.get("severity"),
                        "title": r.get("title"),
                        "detail": r.get("detail"),
                        "evidence": r.get("evidence"),
                    })

    return {
        "finding_type": "Data Quality" if str(f.get("issue_id", "")).startswith("DQ-") else "Anomaly",
        "issue_id": f.get("issue_id"),
        "severity": f.get("severity"),
        "entity": entity,
        "title": f.get("title"),
        "detail": f.get("detail"),
        "exact_finding_evidence": evidence,
        "material": material,
        "connected_workbook_records": connected,
        "related_findings": related[:30],
        "root_cause": f.get("detail"),
        "impact_score": 0,
        "recommended_action": "Review the exact finding and connected operational records before corrective action.",
    }

# -------------------------------------------------------------------
# Executive overview / landing section
# -------------------------------------------------------------------
critical_count = 0
high_count = 0
if cases is not None and not cases.empty and "severity" in cases.columns:
    critical_count = int((cases["severity"].astype(str).str.lower() == "critical").sum())
    high_count = int((cases["severity"].astype(str).str.lower() == "high").sum())

pending = sum(
    1 for _, _case in cases.iterrows()
    if st.session_state.actions.get(
        str(_case.get("case_id", "")).strip(), {}
    ).get("status") == "Pending"
) if cases is not None and not cases.empty else 0

st.markdown(
    """
    <div class="section-title">Operations overview</div>
    <div class="section-subtitle">
        A quick health view of the warehouse control tower. Use the tabs below
        when you want to investigate, explain, trace, approve, or explore records.
    </div>
    """,
    unsafe_allow_html=True,
)

overview_cols = st.columns(6)
overview_cards = [
    ("blue", "▦", "Materials", len(data["Material_Master"]), "Master-data records in scope"),
    ("teal", "◫", "Inventory", len(data["Inventory_Stock"]), "Stock records being monitored"),
    ("amber", "↗", "Deliveries", len(data["Deliveries_Dispatch"]), "Inbound / outbound delivery records"),
    ("purple", "▤", "Purchase Orders", len(data["Purchase_Replenish"]), "Replenishment records"),
    ("red", "!", "Findings", len(dq) + len(anomalies), "Data-quality + process issues"),
    ("green", "⌁", "RCA Cases", len(cases), "Cross-system cases correlated"),
]
for col, (tone, icon, label, value, desc) in zip(overview_cols, overview_cards):
    with col:
        st.markdown(
            f"""
            <div class="overview-card {tone}">
                <div class="icon">{icon}</div>
                <div class="label">{label}</div>
                <div class="value">{value:,}</div>
                <div class="desc">{desc}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

priority_items = []
if critical_count:
    priority_items.append(f"<span class='priority-dot red'></span><b>{critical_count}</b> Critical")
if high_count:
    priority_items.append(f"<span class='priority-dot amber'></span><b>{high_count}</b> High")
if pending:
    priority_items.append(f"<span class='priority-dot blue'></span><b>{pending}</b> Pending approval")
if priority_items:
    st.markdown(f"<div class='priority-strip'><span class='priority-label'>Needs attention</span>{'<span class=\"priority-sep\"> · </span>'.join(priority_items)}</div>", unsafe_allow_html=True)
else:
    st.markdown("<div class='priority-strip ok'><span class='priority-label'>Status</span><b>All clear</b> · No critical/high RCA cases or pending approvals</div>", unsafe_allow_html=True)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
st.markdown("""
<div class="overview-note">
<b>Next:</b> use <b>Control Tower</b> to review issues, <b>Root Cause AI</b> to understand a case, and <b>Approvals</b> when a decision is required.
</div>
""", unsafe_allow_html=True)

# Compact navigation context
st.markdown(
    "<div class='muted'>Investigation workspace · select a tab to continue</div>",
    unsafe_allow_html=True,
)

tabs=st.tabs([
    "Overview",
    "Control Tower",
    "Root Cause AI",
    "Trace Graph",
    "Approvals",
    "Copilot",
    "Data Explorer",
    "Audit",
])

with tabs[0]:
    st.subheader("Control Tower Overview")
    st.caption("Start with the health picture, then move into the investigation workflow.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"""
            <div class="card">
                <div style="font-size:.78rem;color:#667085;font-weight:700">01 · FIND</div>
                <div style="font-size:1.2rem;font-weight:800;margin:5px 0">What needs attention?</div>
                <div style="color:#697386;font-size:.86rem;line-height:1.45">
                    Review <b>{len(dq)}</b> data-quality findings and
                    <b>{len(anomalies)}</b> process/inventory anomalies.
                </div>
            </div>
            """, unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f"""
            <div class="card">
                <div style="font-size:.78rem;color:#667085;font-weight:700">02 · UNDERSTAND</div>
                <div style="font-size:1.2rem;font-weight:800;margin:5px 0">Why is it happening?</div>
                <div style="color:#697386;font-size:.86rem;line-height:1.45">
                    Trace <b>{len(cases)}</b> cross-system cases across
                    material, inventory, deliveries, POs and vendors.
                </div>
            </div>
            """, unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            f"""
            <div class="card">
                <div style="font-size:.78rem;color:#667085;font-weight:700">03 · DECIDE</div>
                <div style="font-size:1.2rem;font-weight:800;margin:5px 0">What should happen next?</div>
                <div style="color:#697386;font-size:.86rem;line-height:1.45">
                    <b>{pending}</b> cases are awaiting human approval.
                    Proposed actions remain simulated until a person approves them.
                </div>
            </div>
            """, unsafe_allow_html=True
        )

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.markdown("### Recommended path")
    st.markdown(
        """
        <div class="workflow">
            <div class="workflow-step"><span class="num">1</span><strong>Control Tower</strong></div>
            <span class="workflow-arrow">→</span>
            <div class="workflow-step"><span class="num">2</span><strong>Root Cause AI</strong></div>
            <span class="workflow-arrow">→</span>
            <div class="workflow-step"><span class="num">3</span><strong>Trace Graph</strong></div>
            <span class="workflow-arrow">→</span>
            <div class="workflow-step"><span class="num">4</span><strong>Approvals</strong></div>
            <span class="workflow-arrow">→</span>
            <div class="workflow-step"><span class="num">5</span><strong>Audit</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.info(
        "Tip: Use Copilot for natural-language questions such as "
        "\"Why is this material short?\" or \"Explain DQ-0102\". "
        "Use Data Explorer when you need to inspect the underlying workbook records."
    )

with tabs[1]:
    st.subheader("Prioritized operational worklist")
    st.caption("Start here: review Critical/High findings, open Root Cause AI, then approve the proposed fix.")

    # Fixed-scope coverage: bad/missing master data and inventory/process anomalies.
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Data quality", len(dq))
    c2.metric("Process anomalies", len(anomalies))
    c3.metric("Root-cause cases", len(cases))
    pending = sum(
        1 for _, _case in cases.iterrows()
        if st.session_state.actions.get(str(_case.get("case_id", "")).strip(), {}).get("status") == "Pending"
    ) if cases is not None and not cases.empty else 0
    c4.metric("Pending approval", pending)

    st.markdown("### Data Quality")
    if dq.empty:
        st.success("No data-quality findings.")
    else:
        dq_view = dq[["issue_id","severity","entity","title","detail","evidence"]].copy()
        dq_view["evidence"] = dq_view["evidence"].apply(evidence_text)
        dq_view.columns = ["ID","Severity","Record","Issue","Explanation","Actual values"]
        st.dataframe(dq_view, width="stretch", hide_index=True)
        st.download_button(
            "Export data-quality findings",
            dq.to_csv(index=False).encode("utf-8"),
            "nexuschain_data_quality_findings.csv",
            "text/csv"
        )

    st.markdown("### Explain a Data Quality Finding")
    dq_ids = dq["issue_id"].astype(str).tolist()
    dq_choice = st.selectbox(
        "Select a finding to investigate",
        dq_ids,
        format_func=lambda x: (
            f"{x} · "
            f"{dq.loc[dq['issue_id'].astype(str).eq(x), 'severity'].iloc[0]} · "
            f"{dq.loc[dq['issue_id'].astype(str).eq(x), 'entity'].iloc[0]} · "
            f"{dq.loc[dq['issue_id'].astype(str).eq(x), 'title'].iloc[0]}"
        ),
        key="dq_explain_choice"
    )
    if st.button("🔎 Explain selected finding with Copilot", type="primary", key="explain_dq"):
        selected_finding = dq[dq["issue_id"].astype(str).eq(str(dq_choice))].iloc[0]
        finding_case = build_finding_context(selected_finding, data, dq, anomalies)
        with st.spinner("Copilot is checking the exact finding and connected workbook records..."):
            st.markdown(copilot_answer(
                f"Explain {dq_choice} in detail. Start with the exact finding, then explain the direct evidence, why it matters, related findings, and the safest next step. Do not mix related findings into the exact finding.",
                finding_case
            ))

    st.markdown("### Inventory & Process Anomalies")
    if anomalies.empty:
        st.success("No inventory/process anomalies.")
    else:
        an_view = anomalies[["issue_id","severity","entity","title","detail","evidence"]].copy()
        an_view["evidence"] = an_view["evidence"].apply(evidence_text)
        an_view.columns = ["ID","Severity","Record","Issue","Explanation","Actual values"]
        st.dataframe(an_view,width="stretch", hide_index=True)
        st.download_button(
            "Export anomaly findings",
            anomalies.to_csv(index=False).encode("utf-8"),
            "nexuschain_anomaly_findings.csv",
            "text/csv"
        )

    st.markdown("### Correlated root causes")
    if cases.empty:
        st.info("No cross-system root-cause cases detected.")
    else:
        df=cases[["case_id","material","severity","impact_score","signals","root_cause","recommended_action"]].copy()
        df["signals"]=df["signals"].apply(lambda x:", ".join(x))
        df.columns=["Case","Material","Severity","Impact","Signals","Root cause","Recommended fix"]
        st.dataframe(df,width="stretch",hide_index=True)
        st.download_button(
            "Export detected issues + proposed fixes",
            df.to_csv(index=False).encode("utf-8"),
            "nexuschain_detected_issues_and_fixes.csv",
            "text/csv"
        )

with tabs[2]:
    st.subheader("AI Root Cause Analysis")
    st.caption("Decision-focused view — only the evidence needed to understand and act on the selected case.")

    if cases.empty:
        st.info("No correlated cases available.")
    else:
        labels = [f"{r.case_id} · {r.material} · {r.severity} · {r.impact_score}/100" for _, r in cases.iterrows()]
        idx = st.selectbox("Case", range(len(labels)), format_func=lambda i: labels[i], key="rca_case_select")
        case = cases.iloc[idx].to_dict()
        cid = str(case.get("case_id", ""))
        severity = str(case.get("severity", "Unknown"))
        sev_class = "critical" if severity.lower() == "critical" else "high" if severity.lower() == "high" else "medium"

        st.markdown(f"""
        <div class='rca-header'>
          <div><div class='rca-kicker'>CASE</div><div class='rca-title'>{cid}</div><div class='rca-material'>{case.get('material','')}</div></div>
          <div class='rca-meta'><span class='severity-pill {sev_class}'>{severity}</span><span class='impact-pill'>Impact {case.get('impact_score',0)}/100</span></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"<div class='ai rca-finding'><div class='ai-label'>Root cause</div>{case.get('root_cause','No root-cause explanation available.')}</div>", unsafe_allow_html=True)

        signals = case.get("signals", [])
        if isinstance(signals, (list, tuple)):
            signals = [str(x) for x in signals if str(x).strip()]
        elif str(signals).strip():
            signals = [str(signals)]
        else:
            signals = []

        if signals:
            st.markdown("**Key evidence**")
            for signal in signals[:4]:
                st.markdown(f"• {signal}")

        st.markdown("**Recommended action**")
        st.markdown(f"<div class='good compact-action'>{case.get('recommended_action','Review the linked records before corrective action.')}</div>", unsafe_allow_html=True)

        if st.button("Generate AI explanation", type="primary", key=f"generate_rca_{cid}"):
            with st.spinner("AI is synthesizing the case evidence..."):
                st.session_state.ai_cache[cid] = generate_root_cause(case)
        if cid in st.session_state.ai_cache:
            st.markdown(st.session_state.ai_cache[cid])

        evidence = case.get("evidence", {}) or {}
        nonempty_evidence = [(sheet, records) for sheet, records in evidence.items() if records]
        if nonempty_evidence:
            with st.expander(f"Supporting records · {sum(len(records) for _, records in nonempty_evidence)} linked rows"):
                for sheet, records in nonempty_evidence:
                    st.markdown(f"**{sheet}** · {len(records)} rows")
                    st.dataframe(pd.DataFrame(records), width="stretch", hide_index=True)

with tabs[3]:
    st.subheader("Relationship Trace Graph")
    st.caption("Follow one material across the six operational sheets. Relationships are built from workbook keys.")
    if cases.empty:
        st.info("No correlated cases available.")
    else:
        mat_options=cases["material"].tolist()
        selected=st.selectbox("Material to trace",mat_options,format_func=lambda x: f"{x} · {next((r.severity for _,r in cases.iterrows() if r.material==x), '')}")
        mm=data["Material_Master"]; iv=data["Inventory_Stock"]; bb=data["Warehouse_Bin"]; dd=data["Deliveries_Dispatch"]; pp=data["Purchase_Replenish"]; vv=data["Vendor_Master"]
        mm1 = mm[mm["Material"].astype(str) == str(selected)]
        iv1=iv[iv["Material"].astype(str)==str(selected)]
        bb1=bb[bb["Assigned Material"].astype(str)==str(selected)]
        dd1=dd[dd["Material"].astype(str)==str(selected)]
        pp1=pp[pp["Material"].astype(str)==str(selected)]
        vendors=set(pp1["Vendor"].astype(str)) if not pp1.empty else set()
        vv1=vv[vv["Vendor"].astype(str).isin(vendors)]
        st.markdown(f"<div class='chain'><span class='node'>Material Master<br><small>{len(mm1)} row</small></span><span class='arrow'>→</span><span class='node'>Inventory<br><small>{len(iv1)} rows</small></span><span class='arrow'>→</span><span class='node'>Warehouse Bin<br><small>{len(bb1)} rows</small></span><span class='arrow'>→</span><span class='node'>Deliveries<br><small>{len(dd1)} rows</small></span><span class='arrow'>→</span><span class='node'>Purchase Orders<br><small>{len(pp1)} rows</small></span><span class='arrow'>→</span><span class='node'>Vendor<br><small>{len(vv1)} rows</small></span></div>",unsafe_allow_html=True)
        st.markdown("### How the records are joined")
        join_df=pd.DataFrame([
            ["Material_Master ↔ Inventory_Stock","Material + Plant","Compare lifecycle/master data with stock"],
            ["Material_Master ↔ Deliveries_Dispatch","Material + Plant","Compare demand with available stock"],
            ["Material_Master ↔ Purchase_Replenish","Material + Plant","Check replenishment and PO status"],
            ["Material_Master ↔ Warehouse_Bin","Assigned Material + Plant/location","Check storage and capacity"],
            ["Purchase_Replenish ↔ Vendor_Master","Vendor","Check supplier governance"],
            ["Inventory_Stock ↔ Deliveries_Dispatch","Material + Plant","Demand vs available stock"],
        ],columns=["Sheets","Business key","Why it is correlated"])
        st.dataframe(join_df,width="stretch",hide_index=True)
        st.markdown("### Connected evidence for this material")
        for title,df,cols in [
            ("Material Master",mm1,list(mm.columns)),
            ("Inventory",iv1,["Material","Plant","Storage Location","Batch","Qty On Hand","Blocked Qty","In-Transit Qty","Batch Expiry","Last Movement Date"]),
            ("Warehouse Bins",bb1,["Bin","Plant","Storage Type","Capacity","Occupied","Bin Status"]),
            ("Deliveries",dd1,["Delivery","Plant","Order Qty","Ship-To","Route","Planned GI Date","Status"]),
            ("Purchase Orders",pp1,["Purchase Order","Plant","Vendor","PO Qty","Expected Delivery","PO Status"]),
            ("Vendor Master",vv1,list(vv.columns)),
        ]:
            cols=[c for c in cols if c in df.columns]
            with st.expander(f"{title} · {len(df)} linked rows"):
                st.dataframe(df[cols],width="stretch",hide_index=True)

with tabs[4]:
    st.subheader("Human approval gate")
    st.caption("The Action Agent proposes. A human decides. The app only simulates execution.")
    if cases.empty: st.info("No actions.")
    for _,case in cases.iterrows():
        cid=case["case_id"]
        state=st.session_state.actions.get(cid,{"status":"Pending","approver":"","note":"","action":case["recommended_action"]})
        with st.expander(f"{cid} · {case['material']} · {case['severity']} · {case['impact_score']}/100"):
            st.write(case["root_cause"])
            action=st.text_area("Proposed action",state["action"],key=f"action_{cid}")
            approver=st.text_input("Approver name / role",state["approver"],key=f"approver_{cid}")
            note=st.text_area("Decision note",state["note"],key=f"note_{cid}")
            x,y,z=st.columns(3)
            if x.button("Approve",key=f"approve_{cid}"):
                if not approver.strip():
                    st.error("Approver is required.")
                else:
                    now=datetime.now().isoformat(timespec="seconds")
                    st.session_state.actions[cid]={"status":"Approved","approver":approver,"note":note,"action":action}
                    st.session_state.audit.append({"timestamp":now,"case":cid,"status":"Approved","agent":"Action Agent","approver":approver,"what":action,"why":case["root_cause"]})
                    st.rerun()
            if y.button("Simulate Execute",key=f"simulate_{cid}"):
                if not approver.strip():
                    st.error("Approver is required for simulation.")
                else:
                    now=datetime.now().isoformat(timespec="seconds")
                    st.session_state.actions[cid]={"status":"Simulated","approver":approver,"note":note,"action":action}
                    st.session_state.audit.append({"timestamp":now,"case":cid,"status":"Simulated","agent":"Action Agent","approver":approver,"what":action,"why":case["root_cause"]})
                    st.rerun()
            if z.button("Reject",key=f"reject_{cid}"):
                now=datetime.now().isoformat(timespec="seconds")
                st.session_state.actions[cid]={"status":"Rejected","approver":approver or "Operator","note":note,"action":action}
                st.session_state.audit.append({"timestamp":now,"case":cid,"status":"Rejected","agent":"Action Agent","approver":approver or "Operator","what":action,"why":case["root_cause"]})
                st.rerun()
            st.write(f"**Current status:** {state['status']}")

with tabs[5]:
    st.subheader("AI Warehouse Copilot")
    st.caption("Ask about any finding, material, delivery, PO, vendor, or workbook-wide issue.")
    q=st.text_input(
        "Ask the control tower",
        placeholder="Explain DQ-0102 in detail  •  Why is MAT-100030 blocked?  •  Why is DLV-800011 overdue?"
    )
    if q:
        import re
        broad_terms = [
            "missing", "data quality", "expired", "stale", "overdue", "shortage",
            "anomal", "issue", "problem", "blocked", "obsolete", "capacity", "vendor"
        ]
        ids=set(re.findall(r"[A-Z]{2,12}-\d{4,8}[A-Z]?",q.upper()))

        # Case-insensitive field/column understanding. The operator can type
        # "Base UoM", "base uom", "BASE UOM", etc. and Copilot will find
        # the matching workbook column/findings without requiring an issue ID.
        def _norm(s):
            return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()

        q_norm = _norm(q)
        column_matches = []
        for sheet_name, df in data.items():
            if df is None or df.empty:
                continue
            for col in df.columns:
                cn = _norm(col)
                if cn and (cn == q_norm or cn in q_norm or q_norm in cn):
                    column_matches.append((sheet_name, col))

        # If the question names a known column/field, focus on that field first.
        # This works even when the wording differs only by capitalization.
        field_findings = []
        for df_name, df in [("Data Quality", dq), ("Anomalies", anomalies)]:
            if df is None or df.empty:
                continue
            for _, r in df.iterrows():
                hay = " ".join([
                    str(r.get("title", "")),
                    str(r.get("detail", "")),
                    str(r.get("evidence", "")),
                ])
                if any(_norm(col) and _norm(col) in _norm(hay) for _, col in column_matches):
                    field_findings.append(r)

        field_handled = False
        if not ids and field_findings:
            field_handled = True
            # Build an evidence-grounded answer from the exact matching field.
            rows = []
            for r in field_findings[:50]:
                rows.append({
                    "ID": r.get("issue_id"),
                    "Severity": r.get("severity"),
                    "Record": r.get("entity"),
                    "Issue": r.get("title"),
                    "Explanation": r.get("detail"),
                    "Actual values": r.get("evidence"),
                })

            matched_fields = ", ".join(f"{sheet}.{col}" for sheet, col in column_matches[:10])
            st.markdown(f"### Field investigation: {matched_fields}")
            st.caption("Case-insensitive match — capitalization does not matter.")
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
            if st.button("🤖 Explain these findings with Copilot", key="explain_field_findings"):
                synthetic = {
                    "finding_type": "Field investigation",
                    "issue_id": ", ".join(str(r.get("issue_id")) for r in field_findings[:20]),
                    "severity": ", ".join(sorted(set(str(r.get("severity")) for r in field_findings[:20]))),
                    "entity": ", ".join(str(r.get("entity")) for r in field_findings[:20]),
                    "title": f"Findings related to field(s): {matched_fields}",
                    "detail": "The operator asked about a workbook field without specifying an issue ID.",
                    "exact_finding_evidence": rows,
                    "material": None,
                    "connected_workbook_records": {
                        sheet: data[sheet][[col]].head(100).to_dict("records")
                        for sheet, col in column_matches[:10]
                        if sheet in data and col in data[sheet].columns
                    },
                    "related_findings": rows,
                }
                with st.spinner("Copilot is explaining the matching field findings..."):
                    st.markdown(copilot_answer(q, synthetic))
        # Exact DQ-/AN- finding IDs and case/material questions are handled
        # only when a field-specific query was not already handled above.
        if not field_handled:
            finding_hit = None
            for df in [dq, anomalies]:
                if df is not None and not df.empty:
                    for ident in ids:
                        rows = df[df["issue_id"].astype(str).str.upper().eq(ident)]
                        if not rows.empty:
                            finding_hit = rows.iloc[0]
                            break
                if finding_hit is not None:
                    break

            if finding_hit is not None:
                finding_case = build_finding_context(finding_hit, data, dq, anomalies)
                with st.spinner("Copilot is checking the exact finding and connected workbook records..."):
                    st.markdown(copilot_answer(q, finding_case))
            else:
                hit = None
                for _, r in cases.iterrows():
                    hay = json.dumps(r.to_dict(), default=str).upper()
                    if any(i in hay for i in ids):
                        hit = r.to_dict()
                        break
                if hit is None and cases.shape[0]:
                    words = [w for w in re.findall(r"[A-Z0-9-]{5,}", q.upper())]
                    for _, r in cases.iterrows():
                        if any(w in json.dumps(r.to_dict(), default=str).upper() for w in words):
                            hit = r.to_dict()
                            break
                if hit:
                    with st.spinner("Analyzing correlated evidence..."):
                        st.markdown(copilot_answer(q, hit))
                else:
                    with st.spinner("Checking the entire workbook..."):
                        st.markdown(copilot_workbook_answer(q, dq, anomalies, data))

with tabs[6]:
    st.subheader("Data Explorer")
    visible_sheets=[s for s in data.keys() if s not in {"README","Data_Dictionary"}]
    sheet=st.selectbox("Sheet",visible_sheets)
    st.dataframe(data[sheet],width="stretch",hide_index=True)

with tabs[7]:
    st.subheader("Audit Trail")
    if st.session_state.audit:
        st.dataframe(pd.DataFrame(st.session_state.audit),width="stretch",hide_index=True)
    else:
        st.info("No human decisions recorded in this session.")
