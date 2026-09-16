

from __future__ import annotations
import os, json
import base64
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st

from agents import load_workbook, run_pipeline, SNAPSHOT_DATE
from llm import generate_root_cause, copilot_answer, copilot_workbook_answer, enabled

st.set_page_config(page_title="IntelliWarehouse AI", page_icon="◈", layout="wide")

# Warehouse background image hosted on Vecteezy.
# Using the public image URL keeps the repository free of image assets.
BG_URL = "https://static.vecteezy.com/system/resources/previews/030/592/227/large_2x/retail-warehouse-full-of-shelves-with-goods-in-cardboard-boxes-and-packages-logistics-sorting-and-distribution-facility-for-product-delivery-generative-ai-photo.jpeg"

bg_layer = (
    "linear-gradient(rgba(238,244,250,.76),rgba(238,244,250,.76)), "
    f"url('{BG_URL}')"
)

# -------------------------------------------------------------------
# HCI-first visual system
# - Visibility: high contrast and clear hierarchy
# - Recognition: icons + labels in navigation
# - Consistency: reusable card/pill/button patterns
# - Feedback: clear active/hover states
# - Aesthetics: soft warehouse background with readable surfaces
# -------------------------------------------------------------------
st.markdown("""
<style>
:root{
    --navy:#14395f;
    --blue:#1769b0;
    --ink:#233952;
    --muted:#66788f;
    --line:#d8e2ed;
    --panel:rgba(255,255,255,.94);
    --panel-soft:rgba(248,251,255,.90);
}

html, body, [class*="css"]{
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* Background: visible, but subordinate to information */
.stApp{
    background:
        linear-gradient(rgba(238,244,249,.86),rgba(238,244,249,.86)),
        url('https://static.vecteezy.com/system/resources/previews/030/592/227/large_2x/retail-warehouse-full-of-shelves-with-goods-in-cardboard-boxes-and-packages-logistics-sorting-and-distribution-facility-for-product-delivery-generative-ai-photo.jpeg')
        center center / cover fixed no-repeat !important;
}
[data-testid="stAppViewContainer"]{
    background:transparent !important;
}
[data-testid="stHeader"]{
    background:rgba(255,255,255,.88) !important;
}
.block-container{
    max-width:1320px !important;
    padding-top:1.15rem !important;
    padding-bottom:2.4rem !important;
}

/* Sidebar */
section[data-testid="stSidebar"]{
    background:rgba(241,246,251,.97) !important;
    border-right:1px solid #d6e1ec !important;
}
section[data-testid="stSidebar"] .block-container{
    padding:1.2rem 1rem 1.5rem !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3{
    color:var(--navy) !important;
    font-weight:800 !important;
}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] .stCaption{
    color:#5e728a !important;
}
section[data-testid="stSidebar"] .stDivider{
    border-color:#ccd9e6 !important;
}

/* Hero */
.hero{
    background:linear-gradient(135deg,#0b2a50 0%,#174a86 58%,#2a67ad 100%);
    color:#fff !important;
    border-radius:24px;
    padding:28px 34px 24px;
    margin:0 0 14px;
    box-shadow:0 16px 34px rgba(20,52,88,.18);
}
.hero h1{
    color:#fff !important;
    font-size:2.35rem !important;
    line-height:1.08 !important;
    margin:0 !important;
    font-weight:850 !important;
    letter-spacing:-.035em !important;
}
.hero p{
    color:#e8f1fb !important;
    font-size:1rem !important;
    line-height:1.45 !important;
    margin:.65rem 0 0 !important;
    font-weight:600 !important;
}

/* ===== Sidebar workspace navigation ===== */
.page-kicker{
    font-size:.72rem;
    font-weight:850;
    letter-spacing:.08em;
    color:#70839a;
    text-transform:uppercase;
    margin:.2rem 0 .15rem;
}
.page-hint{
    color:#6e8096;
    font-size:.86rem;
    margin:0 0 10px;
}
.brand{
    display:flex;
    align-items:center;
    gap:10px;
    padding:2px 0 16px;
}
.brand-mark{
    width:38px;
    height:38px;
    border-radius:11px;
    display:flex;
    align-items:center;
    justify-content:center;
    color:#fff;
    background:linear-gradient(135deg,#1c72c3,#3da9dc);
    font-size:22px;
    box-shadow:0 5px 14px rgba(22,91,145,.18);
}
.brand-title{
    color:#12365f;
    font-weight:850;
    font-size:1rem;
}
.brand-subtitle{
    color:#72849a;
    font-size:.69rem;
    margin-top:2px;
}
.sidebar-section-title{
    color:#74869b;
    font-size:.68rem;
    letter-spacing:.09em;
    font-weight:850;
    margin:.85rem 0 .45rem;
}
section[data-testid="stSidebar"] [data-testid="stRadio"]{
    background:rgba(255,255,255,.58);
    border:1px solid #d9e4ee;
    border-radius:14px;
    padding:6px;
    box-shadow:0 4px 12px rgba(20,52,88,.05);
}
section[data-testid="stSidebar"] [data-testid="stRadio"] > label{
    display:none !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"]{
    gap:2px !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label{
    min-height:40px !important;
    padding:8px 9px !important;
    margin:0 !important;
    border-radius:9px !important;
    color:#2d4661 !important;
    font-size:.84rem !important;
    font-weight:720 !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:hover{
    background:#edf5fc !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked){
    background:#e4f1fc !important;
    color:#07599e !important;
    box-shadow:inset 3px 0 0 #1c74bd !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] input{
    accent-color:#1c74bd !important;
}

/* Typography / page hierarchy */
h1,h2,h3,h4{
    color:var(--navy) !important;
    font-weight:800 !important;
}
h2{font-size:1.55rem !important;}
h3{font-size:1.16rem !important;}
.stCaption, .muted{color:var(--muted) !important;}
.section-subtitle{color:#6b7c92 !important;}
.section-title{color:var(--navy) !important;font-size:1.45rem !important;font-weight:820 !important;}

/* Surface components */
.card,.overview-card,.health-card{
    background:var(--panel) !important;
    border:1px solid var(--line) !important;
    box-shadow:0 6px 18px rgba(20,52,88,.07) !important;
}
.overview-card{
    border-radius:16px !important;
    padding:15px 16px 14px !important;
    min-height:134px !important;
}
.overview-card .label{
    color:#61738a !important;
    font-size:.87rem !important;
    font-weight:700 !important;
}
.overview-card .value{
    color:#172c46 !important;
    font-size:1.9rem !important;
    font-weight:850 !important;
}
.overview-card .desc{
    color:#738399 !important;
    font-size:.78rem !important;
}
.priority-strip{
    background:rgba(255,255,255,.94) !important;
    border:1px solid var(--line) !important;
    border-radius:13px !important;
    box-shadow:0 3px 12px rgba(20,52,88,.06) !important;
}
.overview-note{
    background:rgba(235,243,252,.94) !important;
    border:1px solid #d1e0ef !important;
    color:#506783 !important;
    border-radius:13px !important;
}

/* Inputs, buttons and expanders */
.stButton > button{
    border-radius:9px !important;
    font-weight:750 !important;
    color:#123b66 !important;
    background:#fff !important;
    border:1px solid #b9cbdd !important;
}
.stButton > button[kind="primary"]{
    color:#fff !important;
    background:#1769b0 !important;
    border-color:#1769b0 !important;
}
.stButton > button:hover{
    border-color:#2d72af !important;
    box-shadow:0 3px 9px rgba(20,52,88,.10) !important;
}
div[data-testid="stExpander"]{
    background:rgba(255,255,255,.84) !important;
    border:1px solid #cedbe8 !important;
    border-radius:12px !important;
}

/* Data tables */
div[data-testid="stDataFrame"]{
    border:1px solid #d3dfeb !important;
    border-radius:12px !important;
    overflow:hidden !important;
    background:rgba(255,255,255,.95) !important;
}
div[data-testid="stDataFrame"] *{
    font-size:13px !important;
}

/* RCA */
.rca-header{
    background:rgba(255,255,255,.96) !important;
    border:1px solid #d8e2ed !important;
    box-shadow:0 6px 18px rgba(20,52,88,.07) !important;
}
.ai{
    background:rgba(246,242,255,.95) !important;
    border:1px solid #ddd2f7 !important;
}
.good{
    background:rgba(237,250,242,.95) !important;
    border:1px solid #c9ead5 !important;
}

/* Responsive */
@media (max-width: 1100px){
    .hero{padding:23px 24px 20px !important;}
    .hero h1{font-size:1.9rem !important;}
    div[data-baseweb="tab-list"] button[data-baseweb="tab"]{
        font-size:13px !important;
        padding-left:32px !important;
        padding-right:9px !important;
    }
    div[data-baseweb="tab-list"] button[data-baseweb="tab"] > div,
    div[data-baseweb="tab-list"] button[data-baseweb="tab"] p{
        font-size:13px !important;
    }
    div[data-baseweb="tab-list"] button[data-baseweb="tab"]::before{
        left:9px !important;
        font-size:16px !important;
    }
}
</style>
""", unsafe_allow_html=True)








if "actions" not in st.session_state: st.session_state.actions={}
if "audit" not in st.session_state: st.session_state.audit=[]
if "ai_cache" not in st.session_state: st.session_state.ai_cache={}


st.markdown("""
<div class="hero">
<h1>◈IntelliWarehouse AI</h1>
<p>Detect → Correlate → Explain → Impact → Approve</p>
</div>
""", unsafe_allow_html=True)

st.markdown(
    "<div class='page-kicker'>WORKSPACE</div>"
    "<div class='page-hint'>Choose a workspace from the sidebar to investigate, explain, trace, approve, or inspect records.</div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        "<div class='brand'><div class='brand-mark'>◈</div>"
        "<div><div class='brand-title'>IntelliWarehouse AI</div>"
        "<div class='brand-subtitle'>Warehouse intelligence workspace</div></div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='sidebar-section-title'>WORKSPACE</div>", unsafe_allow_html=True)
    nav_options = [
        "🏠  Overview",
        "📊  Operations",
        "🧠  Root Cause AI",
        "🔗  Trace Graph",
        "✅  Approvals",
        "💬  Copilot",
        "🗄️  Data Explorer",
        "🧾  Audit",
    ]
    selected_nav = st.radio(
        "Workspace",
        nav_options,
        index=0,
        label_visibility="collapsed",
    )

    st.markdown("<div class='sidebar-section-title'>DATA SOURCE</div>", unsafe_allow_html=True)
    default_path = Path(__file__).parent / "Warehouse_AI_Hackathon_Synthetic_Dataset_FINAL_2.xlsx"
    uploaded = st.file_uploader("Upload warehouse workbook", type=["xlsx"])
    path = uploaded if uploaded is not None else default_path
    st.caption("Snapshot: 05 Sep 2026")

    model_name = st.secrets.get('OPENAI_MODEL', os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'))
    if enabled():
        st.success(f"LLM enabled · {model_name}")
    else:
        st.warning("LLM not enabled — deterministic evidence-grounded fallback is active.")
        st.caption("Configure VW Group LLMaaS secrets in Streamlit Cloud → Settings → Secrets.")

    st.markdown("<div class='sidebar-section-title'>GOVERNANCE</div>", unsafe_allow_html=True)
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

# Overview attention metrics are computed once after the workbook pipeline.
critical_count = 0
high_count = 0
if cases is not None and not cases.empty and "severity" in cases.columns:
    severity = cases["severity"].astype(str).str.lower()
    critical_count = int((severity == "critical").sum())
    high_count = int((severity == "high").sum())

pending = sum(
    1 for _, _case in cases.iterrows()
    if st.session_state.actions.get(
        str(_case.get("case_id", "")).strip(), {}
    ).get("status") == "Pending"
) if cases is not None and not cases.empty else 0

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

# Navigation is rendered directly below the hero for immediate visibility.


if selected_nav == '🏠  Overview':
    st.markdown("<div class='section-title'>Operations overview</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-subtitle'>Start with the warehouse health picture, then move into the investigation workflow.</div>",
        unsafe_allow_html=True,
    )

    overview_cols = st.columns(6)
    overview_cards = [
        ("blue", "▦", "Materials", len(data["Material_Master"]), "Master-data records in scope"),
        ("teal", "◫", "Inventory", len(data["Inventory_Stock"]), "Stock records monitored"),
        ("amber", "↗", "Deliveries", len(data["Deliveries_Dispatch"]), "Inbound / outbound records"),
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
        st.markdown(
            f"<div class='priority-strip'><span class='priority-label'>Needs attention</span>{'<span class=\"priority-sep\"> · </span>'.join(priority_items)}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='priority-strip ok'><span class='priority-label'>Status</span><b>All clear</b> · No critical/high RCA cases or pending approvals</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"""<div class="card">
                <div style="font-size:.76rem;color:#6a7b90;font-weight:800;letter-spacing:.04em">01 · FIND</div>
                <div style="font-size:1.12rem;font-weight:820;color:#203b5e;margin:5px 0">What needs attention?</div>
                <div style="color:#687b92;font-size:.84rem;line-height:1.45">
                    Review <b>{len(dq)}</b> data-quality findings and <b>{len(anomalies)}</b> process/inventory anomalies.
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""<div class="card">
                <div style="font-size:.76rem;color:#6a7b90;font-weight:800;letter-spacing:.04em">02 · UNDERSTAND</div>
                <div style="font-size:1.12rem;font-weight:820;color:#203b5e;margin:5px 0">Why is it happening?</div>
                <div style="color:#687b92;font-size:.84rem;line-height:1.45">
                    Trace <b>{len(cases)}</b> cross-system cases across materials, inventory, deliveries, POs and vendors.
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""<div class="card">
                <div style="font-size:.76rem;color:#6a7b90;font-weight:800;letter-spacing:.04em">03 · DECIDE</div>
                <div style="font-size:1.12rem;font-weight:820;color:#203b5e;margin:5px 0">What should happen next?</div>
                <div style="color:#687b92;font-size:.84rem;line-height:1.45">
                    <b>{pending}</b> cases await human approval. Proposed actions remain simulated until approved.
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='overview-note'><b>Recommended path:</b> Operations → Root Cause AI → Trace Graph → Approvals → Audit</div>",
        unsafe_allow_html=True,
    )
    st.info(
        "Use Copilot for natural-language questions such as \"Why is this material short?\" or \"Explain DQ-0102\". "
        "Use Data Explorer when you need the underlying workbook records."
    )

if selected_nav == '📊  Operations':
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

if selected_nav == '🧠  Root Cause AI':
    st.subheader("Root Cause AI")
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

if selected_nav == '🔗  Trace Graph':
    st.subheader("Relationship trace")
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

if selected_nav == '✅  Approvals':
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

if selected_nav == '💬  Copilot':
    st.subheader("Warehouse Copilot")
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

if selected_nav == '🗄️  Data Explorer':
    st.subheader("Data Explorer")
    visible_sheets=[s for s in data.keys() if s not in {"README","Data_Dictionary"}]
    sheet=st.selectbox("Sheet",visible_sheets)
    st.dataframe(data[sheet],width="stretch",hide_index=True)

if selected_nav == '🧾  Audit':
    st.subheader("Audit trail")
    if st.session_state.audit:
        st.dataframe(pd.DataFrame(st.session_state.audit),width="stretch",hide_index=True)
    else:
        st.info("No human decisions recorded in this session.")
