from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from agents import SNAPSHOT_DATE, load_workbook, run_pipeline
from llm import (
    copilot_answer,
    copilot_workbook_answer,
    enabled,
    generate_root_cause,
)

st.set_page_config(
    page_title="IntelliWarehouse AI",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
BG_URL = (
    "https://static.vecteezy.com/system/resources/previews/030/592/227/"
    "large_2x/retail-warehouse-full-of-shelves-with-goods-in-cardboard-boxes-"
    "and-packages-logistics-sorting-and-distribution-facility-for-product-"
    "delivery-generative-ai-photo.jpeg"
)
DEFAULT_WORKBOOK = Path(__file__).parent / "Warehouse_AI_Hackathon_Synthetic_Dataset_FINAL_2.xlsx"

NAV = {
    "Overview": "🏠",
    "Data Quality": "🔎",
    "Inventory & Process": "⚙️",
    "Correlated Cases": "🧠",
    "Root Cause AI": "🧩",
    "Trace Graph": "🔗",
    "Approvals": "✅",
    "Copilot": "💬",
    "Data Explorer": "🗄️",
    "Audit": "🧾",
}

# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------
if "active_workspace" not in st.session_state:
    st.session_state.active_workspace = "Overview"
if "actions" not in st.session_state:
    st.session_state.actions = {}
if "audit" not in st.session_state:
    st.session_state.audit = []
if "ai_cache" not in st.session_state:
    st.session_state.ai_cache = {}
if "ai_error" not in st.session_state:
    st.session_state.ai_error = None

# -----------------------------------------------------------------------------
# Styling — single CSS block, no tab hacks / raw CSS outside strings
# -----------------------------------------------------------------------------
st.markdown(
    f"""
<style>
:root {{
    --navy:#153b63;
    --blue:#2c74b8;
    --muted:#70839a;
    --line:#d7e2ec;
    --panel:rgba(255,255,255,.95);
}}

/* App background */
.stApp {{
    background:
      linear-gradient(rgba(239,245,250,.80),rgba(239,245,250,.80)),
      url('{BG_URL}') center center / cover fixed no-repeat !important;
}}
[data-testid="stAppViewContainer"] {{ background:transparent !important; }}
[data-testid="stHeader"] {{ background:rgba(255,255,255,.88) !important; }}
.block-container {{ max-width:1420px; padding-top:1.1rem; padding-bottom:3rem; }}

/* Sidebar */
section[data-testid="stSidebar"] {{
    background:rgba(239,245,250,.98) !important;
    border-right:1px solid #d4e0eb !important;
}}
section[data-testid="stSidebar"] > div:first-child {{ padding-top:1.15rem !important; }}
.brand {{ display:flex; align-items:center; gap:11px; padding:4px 2px 19px; }}
.brand-mark {{
    width:43px; height:43px; border-radius:12px; display:flex; align-items:center; justify-content:center;
    color:#fff; background:linear-gradient(135deg,#1876c8,#39a8d8); font-size:24px;
    box-shadow:0 6px 16px rgba(21,85,140,.18);
}}
.brand-title {{ color:#123c66; font-size:1.02rem; font-weight:850; line-height:1.15; }}
.brand-subtitle {{ color:#73869c; font-size:.73rem; margin-top:3px; }}
.sidebar-section-title,.sidebar-group-label {{
    color:#74889e; font-size:.66rem; letter-spacing:.10em; font-weight:850; margin:12px 2px 6px;
}}
.sidebar-group {{ color:#647a92; font-size:.66rem; letter-spacing:.10em; font-weight:850; margin:4px 2px 5px; }}
.sidebar-group-label {{ margin-top:14px; }}
.sidebar-current {{
    margin:10px 2px; padding:7px 9px; border-radius:9px; background:#e6f1fa;
    color:#56708a; font-size:.70rem;
}}
.sidebar-current b {{ color:#0c5a9e; }}
section[data-testid="stSidebar"] .stButton {{ margin:2px 0 !important; }}
section[data-testid="stSidebar"] .stButton > button {{
    min-height:40px !important; padding:8px 11px !important; border-radius:10px !important;
    text-align:left !important; justify-content:flex-start !important; font-size:.86rem !important;
    font-weight:700 !important; width:100% !important;
}}
section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {{
    color:#536b84 !important; background:transparent !important; border:1px solid transparent !important;
    box-shadow:none !important;
}}
section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {{
    color:#154f7e !important; background:#edf5fc !important; border-color:#dbe7f1 !important;
}}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
    color:#0b579b !important; background:#dcecfb !important; border:1px solid #c2dbee !important;
    box-shadow:inset 3px 0 0 #1c77bb !important;
}}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] {{
    background:#fff !important; border:1px solid #d9e3ed !important; border-radius:12px !important; padding:8px !important;
}}

/* Hero */
.hero {{
    margin:3px 0 13px; padding:30px 34px 25px; border-radius:24px;
    color:#fff; background:linear-gradient(135deg,#0b2853 0%,#174783 55%,#2a67b1 100%);
    box-shadow:0 12px 28px rgba(11,40,83,.18);
}}
.hero h1 {{ color:#fff !important; font-size:2.25rem; font-weight:850; margin:0; letter-spacing:-.035em; }}
.hero p {{ color:#e9f1fb !important; font-size:1rem; font-weight:650; margin:.45rem 0 0; }}

/* Main hierarchy */
.workspace-kicker {{ color:#6f8298; font-size:.67rem; font-weight:850; letter-spacing:.10em; text-transform:uppercase; }}
.page-title {{ color:#153f68; font-size:1.70rem; font-weight:850; margin-top:2px; }}
.page-subtitle {{ color:#6f8299; font-size:.84rem; margin:4px 0 14px; }}
h1,h2,h3,h4 {{ color:#153d66 !important; }}
.stCaption {{ color:#71839a !important; }}

/* Overview cards */
.overview-card {{
    min-height:136px; padding:16px 17px 14px; border-radius:16px;
    background:rgba(255,255,255,.96); border:1px solid var(--line);
    box-shadow:0 5px 15px rgba(22,54,88,.06);
}}
.overview-card .icon {{
    width:36px; height:36px; border-radius:11px; display:flex; align-items:center; justify-content:center;
    font-size:18px; font-weight:800; margin-bottom:10px;
}}
.overview-card .label {{ color:#60758c; font-size:.80rem; font-weight:750; }}
.overview-card .value {{ color:#153b63; font-size:1.72rem; font-weight:850; line-height:1.05; margin:3px 0 6px; }}
.overview-card .desc {{ color:#78899d; font-size:.72rem; line-height:1.35; }}
.blue .icon {{ background:#e7f0ff; color:#2359a8; }}
.teal .icon {{ background:#e4f8f5; color:#087f73; }}
.amber .icon {{ background:#fff3d8; color:#a66a00; }}
.purple .icon {{ background:#f0eaff; color:#6f42c1; }}
.red .icon {{ background:#ffe8e7; color:#c23b35; }}
.green .icon {{ background:#e5f7eb; color:#24824a; }}

/* Operational status cards */
.ops-status-card {{
    min-height:112px; padding:14px 16px 13px 19px; border-radius:14px; background:rgba(255,255,255,.97);
    border:1px solid #d7e2ec; box-shadow:0 5px 14px rgba(19,52,85,.06); position:relative; overflow:hidden;
}}
.ops-status-card::before {{ content:""; position:absolute; left:0; top:0; bottom:0; width:4px; }}
.ops-status-card.dq::before {{ background:#d84b45; }}
.ops-status-card.process::before {{ background:#dd941e; }}
.ops-status-card.rca::before {{ background:#7448c6; }}
.ops-status-card.approval::before {{ background:#2c74b8; }}
.ops-top {{ display:flex; align-items:center; gap:8px; }}
.ops-step {{
    width:27px; height:27px; border-radius:8px; background:#eef4fa; color:#6a8098;
    display:flex; align-items:center; justify-content:center; font-size:.65rem; font-weight:850;
}}
.ops-status-card.dq .ops-step {{ background:#fdeceb; color:#b43f39; }}
.ops-status-card.process .ops-step {{ background:#fff2dd; color:#b9780d; }}
.ops-status-card.rca .ops-step {{ background:#f0eaff; color:#6740b4; }}
.ops-status-card.approval .ops-step {{ background:#e8f2fb; color:#2465a2; }}
.ops-title {{ color:#3f5570; font-size:.79rem; font-weight:800; }}
.ops-value {{ color:#153b63; font-size:2.05rem; font-weight:850; line-height:1; margin-top:9px; }}
.ops-sub {{ color:#7a899d; font-size:.70rem; margin-top:6px; }}

/* Attention */
.attention-panel {{
    display:flex; align-items:center; justify-content:space-between; gap:16px; padding:10px 14px; margin:13px 0 14px;
    border-radius:12px; background:rgba(255,255,255,.96); border:1px solid #d8e2ec;
    box-shadow:0 4px 10px rgba(22,54,88,.05);
}}
.attention-heading {{ display:flex; flex-direction:column; gap:2px; min-width:165px; }}
.attention-title {{ color:#173d64; font-size:.80rem; font-weight:850; }}
.attention-caption {{ color:#8a98a8; font-size:.64rem; }}
.attention-items {{ display:flex; align-items:center; justify-content:flex-end; gap:8px; flex-wrap:wrap; }}
.attention-item {{ display:inline-flex; align-items:center; gap:6px; padding:5px 9px; border-radius:999px; font-size:.70rem; font-weight:750; border:1px solid #dde5ed; }}
.attention-item.critical {{ background:#fff0ef; color:#b23d37; border-color:#f0cecc; }}
.attention-item.high {{ background:#fff5e5; color:#99670d; border-color:#f0ddb9; }}
.attention-item.pending {{ background:#edf5fc; color:#2c6399; border-color:#d1e1ef; }}
.attention-dot {{ width:7px; height:7px; border-radius:50%; display:inline-block; }}
.attention-item.critical .attention-dot {{ background:#d54b45; }}
.attention-item.high .attention-dot {{ background:#dc951d; }}
.attention-item.pending .attention-dot {{ background:#3178bd; }}
.attention-panel.clear {{ background:rgba(241,250,246,.96); border-color:#d6ebe0; }}
.attention-clear {{ color:#2e6b57; font-size:.72rem; font-weight:700; }}

/* Workflow */
.workflow-heading {{ color:#6d8097; font-size:.67rem; font-weight:850; letter-spacing:.09em; text-transform:uppercase; margin:3px 0 1px; }}
.workflow-subheading {{ color:#8a98a8; font-size:.68rem; margin-bottom:7px; }}
.workflow-card {{
    min-height:160px; padding:14px 15px 13px; border-radius:14px; background:rgba(255,255,255,.97);
    border:1px solid #d6e1eb; box-shadow:0 5px 14px rgba(18,54,95,.06); position:relative; overflow:hidden;
}}
.workflow-card::before {{ content:""; position:absolute; left:0; top:0; bottom:0; width:4px; }}
.workflow-card.find::before {{ background:#2f75b9; }}
.workflow-card.understand::before {{ background:#7549c5; }}
.workflow-card.decide::before {{ background:#15986f; }}
.workflow-top {{ display:flex; justify-content:space-between; align-items:center; }}
.workflow-icon {{ width:33px; height:33px; border-radius:9px; display:flex; align-items:center; justify-content:center; background:#edf5fb; font-size:18px; }}
.workflow-card.understand .workflow-icon {{ background:#f1ebff; }}
.workflow-card.decide .workflow-icon {{ background:#eaf8f1; }}
.workflow-step {{ color:#8b99a9; font-size:.64rem; font-weight:850; }}
.workflow-kicker {{ color:#718399; font-size:.61rem; font-weight:850; letter-spacing:.08em; margin-top:10px; }}
.workflow-title {{ color:#183e65; font-size:1.00rem; font-weight:850; line-height:1.18; margin-top:3px; }}
.workflow-body {{ color:#71849a; font-size:.74rem; line-height:1.40; margin-top:7px; }}
.workflow-destination {{ color:#2b6da9; font-size:.70rem; font-weight:800; margin-top:10px; }}
.overview-help {{ display:flex; align-items:center; gap:8px; padding:9px 12px; margin-top:12px; border-radius:11px; border:1px solid #d5e3f2; background:rgba(239,247,255,.91); color:#4f6b88; font-size:.71rem; line-height:1.35; }}
.help-icon {{ width:18px; height:18px; flex:0 0 18px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:#2b73ba; color:#fff; font-size:.65rem; font-weight:850; }}

/* Investigation cards / filters */
.findings-header {{ margin:5px 0 10px; }}
.findings-kicker {{ color:#7448c6; font-size:.67rem; font-weight:850; letter-spacing:.10em; }}
.findings-title {{ color:#183e65; font-size:1.42rem; font-weight:850; margin-top:2px; }}
.findings-subtitle {{ color:#71839a; font-size:.78rem; margin-top:3px; }}
.finding-severity {{ min-height:84px; padding:13px 15px; border-radius:13px; background:rgba(255,255,255,.96); border:1px solid #d9e3ed; box-shadow:0 4px 12px rgba(22,54,88,.05); position:relative; overflow:hidden; }}
.finding-severity::before {{ content:""; position:absolute; left:0; top:0; bottom:0; width:4px; }}
.finding-severity.critical::before {{ background:#d64545; }}
.finding-severity.high::before {{ background:#e39a20; }}
.finding-severity.medium::before {{ background:#4679be; }}
.finding-severity.low::before {{ background:#6e7f92; }}
.finding-severity-label {{ color:#6d7d92; font-size:.75rem; font-weight:750; }}
.finding-severity-value {{ color:#173b63; font-size:1.65rem; font-weight:850; line-height:1.05; margin-top:5px; }}
.card {{ background:rgba(255,255,255,.94); border:1px solid #dce5ee; border-radius:14px; padding:16px; box-shadow:0 5px 14px rgba(18,54,95,.05); }}
.good {{ background:#eef9f4; border:1px solid #d6ede1; border-radius:12px; padding:12px; }}
.warn {{ background:#fff7e8; border:1px solid #f0dfb8; border-radius:12px; padding:12px; }}

/* RCA */
.rca-case-strip {{ display:flex; align-items:center; justify-content:space-between; gap:18px; margin:7px 0 13px; padding:15px 17px; border:1px solid #d5e1ec; border-radius:14px; background:rgba(255,255,255,.97); box-shadow:0 5px 14px rgba(18,54,95,.06); }}
.rca-label,.rca-panel-kicker {{ color:#7a8a9e; font-size:.62rem; font-weight:850; letter-spacing:.09em; }}
.rca-case-id {{ color:#173e67; font-size:1.28rem; font-weight:850; margin-top:2px; }}
.rca-material {{ color:#75869a; font-size:.76rem; margin-top:2px; }}
.rca-case-right {{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; }}
.rca-severity,.rca-impact {{ display:inline-flex; padding:7px 10px; border-radius:999px; font-size:.73rem; font-weight:800; border:1px solid #d7e1eb; background:#f6f8fb; color:#485c74; }}
.rca-severity.critical {{ background:#fff0ef; color:#b83f39; border-color:#f2cfcc; }}
.rca-severity.high {{ background:#fff5e4; color:#a76a09; border-color:#f1ddbc; }}
.rca-severity.medium {{ background:#eef4fc; color:#326aa3; border-color:#cfdded; }}
.rca-panel {{ padding:15px 16px; background:rgba(255,255,255,.96); border:1px solid #d7e2ec; border-radius:14px; box-shadow:0 5px 14px rgba(18,54,95,.05); margin-bottom:12px; }}
.rca-panel-head {{ display:flex; align-items:center; gap:9px; margin-bottom:10px; }}
.rca-panel-icon {{ width:31px; height:31px; border-radius:8px; display:flex; align-items:center; justify-content:center; background:#eef4fa; font-size:16px; }}
.rca-panel-title {{ color:#183f67; font-size:.96rem; font-weight:850; margin-top:2px; }}
.rca-cause {{ border-left:4px solid #7448c6; }}
.rca-evidence {{ border-left:4px solid #2f73b7; }}
.rca-action {{ border-left:4px solid #15986f; }}
.rca-impact-panel {{ border-left:4px solid #d48b1b; }}
.rca-cause-copy {{ color:#344f6f; font-size:.88rem; line-height:1.55; }}
.rca-evidence-row {{ display:flex; align-items:flex-start; gap:8px; padding:7px 0; color:#3d5570; font-size:.79rem; line-height:1.35; border-bottom:1px solid #edf1f5; }}
.rca-evidence-row:last-child {{ border-bottom:0; }}
.rca-check {{ color:#2b78bb; font-weight:900; }}
.rca-action-copy {{ color:#315960; font-size:.83rem; line-height:1.48; padding:11px 12px; background:#eef9f4; border:1px solid #d5ece1; border-radius:10px; }}
.rca-impact-score {{ color:#183e66; font-size:1.80rem; font-weight:850; line-height:1; margin:3px 0 10px; }}
.rca-impact-score span {{ color:#7b8c9f; font-size:.76rem; font-weight:700; }}
.rca-impact-track {{ height:8px; border-radius:99px; background:#e8eef4; overflow:hidden; }}
.rca-impact-fill {{ height:100%; border-radius:99px; background:#d48b1b; }}
.rca-impact-note {{ color:#8090a2; font-size:.68rem; margin-top:6px; }}
.rca-ai-box {{ padding:13px 15px; margin:2px 0 8px; border:1px solid #cedded; border-radius:13px; background:linear-gradient(135deg,rgba(238,246,255,.97),rgba(248,245,255,.97)); }}
.rca-ai-kicker,.ai-output-title {{ color:#7044c5; font-size:.63rem; font-weight:850; letter-spacing:.09em; }}
.rca-ai-title {{ color:#183f67; font-size:.95rem; font-weight:850; margin-top:2px; }}
.rca-ai-copy {{ color:#73859a; font-size:.72rem; margin-top:4px; line-height:1.35; }}
.ai-output-title {{ margin:10px 0 5px; display:none; }}
.ai-brief-header {{ display:flex; align-items:flex-start; justify-content:space-between; gap:16px; padding-bottom:13px; margin-bottom:4px; border-bottom:1px solid #e4eaf1; }}
.ai-decision-brief-surface {{
    margin:12px 0 18px;
    padding:22px 24px 24px;
    background:#ffffff !important;
    background-color:#ffffff !important;
    color:#243b55 !important;
    border:1px solid #cbd8e5;
    border-radius:18px;
    box-shadow:0 12px 32px rgba(24,63,103,.14);
    opacity:1 !important;
    backdrop-filter:none !important;
}}
.ai-decision-brief-surface .ai-brief-header {{
    background:#ffffff;
}}
.ai-decision-brief-surface .ai-section-card {{
    margin-top:17px;
    padding:15px 17px 16px;
    background:#ffffff !important;
    background-color:#ffffff !important;
    border:1px solid #e2e9f0;
    border-radius:13px;
}}
.ai-decision-brief-surface .ai-section-card.cause {{ border-left:4px solid #7448c6; }}
.ai-decision-brief-surface .ai-section-card.factors {{ border-left:4px solid #2f73b7; }}
.ai-decision-brief-surface .ai-section-card.impact {{ border-left:4px solid #d48b1b; }}
.ai-decision-brief-surface .ai-section-card.action {{ border-left:4px solid #15986f; }}
.ai-decision-brief-surface .ai-section-card.confidence {{ border-left:4px solid #62778d; }}
.ai-decision-brief-surface .ai-section-title {{
    margin:0 0 8px;
    color:#173f67 !important;
    font-size:.92rem;
    font-weight:900;
}}
.ai-decision-brief-surface .ai-section-body {{
    color:#26384d !important;
    font-size:.90rem;
    line-height:1.62;
}}
.ai-decision-brief-surface .ai-section-body p,
.ai-decision-brief-surface .ai-section-body li {{
    color:#26384d !important;
}}
.ai-decision-brief-surface .ai-section-body p {{ margin:.15rem 0 .65rem; }}
.ai-decision-brief-surface .ai-section-body ul,
.ai-decision-brief-surface .ai-section-body ol {{ margin:.25rem 0 .3rem 1.2rem; padding-left:1.05rem; }}
.ai-decision-brief-surface .ai-section-body li {{ margin:.42rem 0; padding-left:.2rem; }}
.ai-decision-brief-surface strong {{ color:#183f67 !important; }}
.ai-decision-brief-surface code {{
    color:#183f67;
    background:#f2f6fa;
    padding:1px 5px;
    border-radius:5px;
}}

/* RCA AI output surface: keep the live generated content readable over the warehouse background. */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ai-brief-header) {{
    background:rgba(255,255,255,.975) !important;
    border:1px solid #cfdbe7 !important;
    border-radius:18px !important;
    box-shadow:0 10px 28px rgba(18,54,95,.10) !important;
    backdrop-filter:blur(3px);
}}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ai-brief-header) .ai-section p,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ai-brief-header) .ai-section li {{
    color:#243b55 !important;
}}
.ai-brief-kicker {{ color:#7044c5; font-size:.64rem; font-weight:900; letter-spacing:.10em; }}
.ai-brief-heading {{ color:#173f67; font-size:1.04rem; font-weight:850; margin-top:4px; }}
.ai-live-pill {{ flex:0 0 auto; color:#197a59; background:#ecf8f2; border:1px solid #cfeade; border-radius:999px; padding:5px 9px; font-size:.64rem; font-weight:900; letter-spacing:.05em; }}
.ai-section {{ margin-top:15px; }}
.ai-section-title {{ display:flex; align-items:center; gap:8px; color:#173f67; font-size:.84rem; font-weight:900; letter-spacing:.02em; margin-bottom:5px; }}
.ai-section-icon {{ width:25px; height:25px; border-radius:7px; display:inline-flex; align-items:center; justify-content:center; background:#eef4fa; font-size:13px; }}
.ai-section.cause .ai-section-icon {{ background:#f1ecfb; }}
.ai-section.factors .ai-section-icon {{ background:#eef6fb; }}
.ai-section.impact .ai-section-icon {{ background:#fff5e5; }}
.ai-section.action .ai-section-icon {{ background:#ebf8f2; }}
.ai-section.confidence .ai-section-icon {{ background:#f1f4f8; }}
.ai-brief-header + div p {{ margin-top:0.2rem; }}

.ai-brief-title-row {{ display:flex; align-items:center; gap:8px; margin:9px 0 2px; padding:7px 10px; border-radius:9px; background:rgba(255,255,255,.90); border:1px solid #dce5ed; color:#183d64; font-size:.79rem; font-weight:850; }}
.ai-brief-title-row.cause {{ border-left:4px solid #7448c6; }}
.ai-brief-title-row.factors {{ border-left:4px solid #2f73b7; }}
.ai-brief-title-row.impact {{ border-left:4px solid #d48b1b; }}
.ai-brief-title-row.action {{ border-left:4px solid #15986f; }}
.ai-brief-title-row.confidence {{ border-left:4px solid #62778d; }}
.ai-brief-icon {{ font-size:15px; }}

/* Trace / approvals */
.trace-node {{ padding:13px 12px; border-radius:12px; background:rgba(255,255,255,.95); border:1px solid #dbe4ec; text-align:center; }}
.trace-node strong {{ color:#1a456d; font-size:.79rem; }}
.trace-node small {{ color:#7c8da0; font-size:.67rem; }}
.join-table {{ font-size:.78rem; }}
.approval-card {{ padding:14px 15px; border:1px solid #d9e3ec; border-radius:13px; background:rgba(255,255,255,.95); margin-bottom:10px; }}

/* Buttons */
.stButton > button {{ border-radius:9px !important; font-weight:750 !important; border:1px solid #b9cbe0 !important; color:#12365f !important; background:#fff !important; }}
.stButton > button[kind="primary"] {{ color:#fff !important; background:#1f70b8 !important; border-color:#1f70b8 !important; }}

@media (max-width: 1000px) {{
    .hero h1 {{ font-size:1.8rem; }}
    .rca-case-strip {{ flex-direction:column; align-items:flex-start; }}
}}

.rca-context-row{{
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-top:14px;
    padding-top:10px;
    border-top:1px solid #e5ebf1;
    color:#71839a;
    font-size:.73rem;
}}
.rca-context-row b{{
    color:#173f66;
    font-size:.92rem;
}}
.rca-awaiting{{
    display:flex;
    align-items:center;
    gap:12px;
    margin-top:11px;
    padding:16px 17px;
    border:1px dashed #bfd1e3;
    border-radius:14px;
    background:rgba(246,250,254,.90);
}}
.rca-awaiting-icon{{
    width:36px;
    height:36px;
    border-radius:10px;
    display:flex;
    align-items:center;
    justify-content:center;
    background:#eef5fb;
    font-size:18px;
}}
.rca-awaiting-title{{
    color:#1a4168;
    font-size:.87rem;
    font-weight:850;
}}
.rca-awaiting-copy{{
    color:#71849a;
    font-size:.74rem;
    line-height:1.4;
    margin-top:3px;
}}


.copilot-result-label{{
    margin:10px 0 5px;
    color:#1f6da9;
    font-size:.66rem;
    font-weight:850;
    letter-spacing:.10em;
}}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Sidebar navigation
# -----------------------------------------------------------------------------
def nav_button(label: str) -> None:
    icon = NAV[label]
    active = st.session_state.active_workspace == label
    if st.button(
        f"{icon}  {label}",
        key=f"nav_{label}",
        type="primary" if active else "secondary",
        use_container_width=True,
    ):
        st.session_state.active_workspace = label
        st.rerun()


with st.sidebar:
    st.markdown(
        "<div class='brand'><div class='brand-mark'>◈</div>"
        "<div><div class='brand-title'>IntelliWarehouse AI</div>"
        "<div class='brand-subtitle'>Warehouse intelligence workspace</div></div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='sidebar-group'>CORE</div>", unsafe_allow_html=True)
    nav_button("Overview")

    st.markdown("<div class='sidebar-group-label'>OPERATIONS</div>", unsafe_allow_html=True)
    nav_button("Data Quality")
    nav_button("Inventory & Process")
    nav_button("Correlated Cases")

    st.markdown("<div class='sidebar-group-label'>AI & WORKFLOW</div>", unsafe_allow_html=True)
    nav_button("Root Cause AI")
    nav_button("Trace Graph")
    nav_button("Approvals")
    nav_button("Copilot")

    st.markdown("<div class='sidebar-group-label'>DATA & GOVERNANCE</div>", unsafe_allow_html=True)
    nav_button("Data Explorer")
    nav_button("Audit")

    st.markdown(
        f"<div class='sidebar-current'>Current: <b>{st.session_state.active_workspace}</b></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='sidebar-section-title'>DATA SOURCE</div>", unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload warehouse workbook", type=["xlsx"])
    workbook_path = uploaded if uploaded is not None else DEFAULT_WORKBOOK
    st.caption(f"Snapshot: {SNAPSHOT_DATE.strftime('%d %b %Y') if hasattr(SNAPSHOT_DATE, 'strftime') else SNAPSHOT_DATE}")

    model_name = st.secrets.get("OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o"))
    if enabled():
        st.success(f"LLM enabled · {model_name}")
    else:
        st.warning("LLM not enabled")
        st.caption("Configure VW IDP + LLM API credentials in Streamlit Secrets.")

    st.markdown("<div class='sidebar-section-title'>GOVERNANCE</div>", unsafe_allow_html=True)
    st.caption("Human approval required · Simulated actions · Audit retained")

# -----------------------------------------------------------------------------
# Load deterministic warehouse intelligence
# -----------------------------------------------------------------------------
try:
    raw = load_workbook(workbook_path)
    data, graph, dq, anomalies, cases = run_pipeline(raw)
except Exception as exc:
    st.error(f"Could not load workbook: {exc}")
    st.stop()

# Default approval records for every case.
if cases is not None and not cases.empty:
    for _, row in cases.iterrows():
        cid = str(row.get("case_id", "")).strip()
        if cid and cid not in st.session_state.actions:
            st.session_state.actions[cid] = {
                "status": "Pending",
                "approver": "",
                "note": "",
                "action": row.get("recommended_action", "Review the linked records before corrective action."),
            }

pending = sum(
    1
    for _, row in cases.iterrows()
    if st.session_state.actions.get(str(row.get("case_id", "")).strip(), {}).get("status") == "Pending"
) if cases is not None and not cases.empty else 0
critical_count = int((cases["severity"].astype(str).str.lower() == "critical").sum()) if not cases.empty and "severity" in cases.columns else 0
high_count = int((cases["severity"].astype(str).str.lower() == "high").sum()) if not cases.empty and "severity" in cases.columns else 0

# -----------------------------------------------------------------------------
# Shared helpers
# -----------------------------------------------------------------------------
def evidence_text(value) -> str:
    if not isinstance(value, dict):
        return str(value)
    parts = []
    for key, val in value.items():
        if isinstance(val, (list, tuple)):
            rendered = ", ".join(map(str, val))
        elif val is None or (not isinstance(val, dict) and pd.isna(val)):
            rendered = "blank"
        else:
            rendered = str(val)
        parts.append(f"{key}={rendered}")
    return " · ".join(parts)


def build_finding_context(finding) -> dict:
    f = finding.to_dict() if hasattr(finding, "to_dict") else dict(finding)
    entity = str(f.get("entity", "")).strip()
    ev = f.get("evidence", {}) if isinstance(f.get("evidence"), dict) else {}

    material = None
    if entity.upper().startswith("MAT-"):
        material = entity.split("|")[0].strip()
    elif ev.get("Material"):
        material = str(ev["Material"]).strip()
    else:
        match = re.search(r"MAT-\d+[A-Z]?", entity.upper())
        if match:
            material = match.group(0)

    connected = {}
    if material:
        for sheet, column in [
            ("Material_Master", "Material"),
            ("Inventory_Stock", "Material"),
            ("Warehouse_Bin", "Assigned Material"),
            ("Deliveries_Dispatch", "Material"),
            ("Purchase_Replenish", "Material"),
        ]:
            frame = data.get(sheet, pd.DataFrame())
            if not frame.empty and column in frame.columns:
                connected[sheet] = frame[frame[column].astype(str).eq(material)].head(25).to_dict("records")
            else:
                connected[sheet] = []

        po_rows = pd.DataFrame(connected.get("Purchase_Replenish", []))
        vdf = data.get("Vendor_Master", pd.DataFrame())
        if not po_rows.empty and "Vendor" in po_rows.columns and not vdf.empty and "Vendor" in vdf.columns:
            vendors = set(po_rows["Vendor"].astype(str))
            connected["Vendor_Master"] = vdf[vdf["Vendor"].astype(str).isin(vendors)].head(10).to_dict("records")
        else:
            connected["Vendor_Master"] = []
    else:
        connected["Direct Evidence"] = [ev]

    related = []
    for frame in [dq, anomalies]:
        if frame is None or frame.empty:
            continue
        for _, row in frame.iterrows():
            if str(row.get("issue_id", "")) == str(f.get("issue_id", "")):
                continue
            if material and material in str(row.get("entity", "")).split("|"):
                related.append({
                    "issue_id": row.get("issue_id"),
                    "severity": row.get("severity"),
                    "title": row.get("title"),
                    "detail": row.get("detail"),
                    "evidence": row.get("evidence"),
                })

    return {
        "finding_type": "Data Quality" if str(f.get("issue_id", "")).startswith("DQ-") else "Anomaly",
        "issue_id": f.get("issue_id"),
        "severity": f.get("severity"),
        "entity": entity,
        "title": f.get("title"),
        "detail": f.get("detail"),
        "exact_finding_evidence": ev,
        "material": material,
        "connected_workbook_records": connected,
        "related_findings": related[:30],
    }


def page_header(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"<div class='workspace-kicker'>{kicker}</div>"
        f"<div class='page-title'>{title}</div>"
        f"<div class='page-subtitle'>{subtitle}</div>",
        unsafe_allow_html=True,
    )


def severity_cards(frame: pd.DataFrame) -> None:
    sev = frame["severity"].astype(str).str.strip().str.title() if not frame.empty and "severity" in frame.columns else pd.Series(dtype=str)
    counts = {x: int((sev == x).sum()) for x in ["Critical", "High", "Medium", "Low"]}
    cols = st.columns(4)
    for col, (label, tone) in zip(cols, [("Critical", "critical"), ("High", "high"), ("Medium", "medium"), ("Low", "low")]):
        with col:
            st.markdown(
                f"<div class='finding-severity {tone}'><div class='finding-severity-label'>{label}</div>"
                f"<div class='finding-severity-value'>{counts[label]:,}</div></div>",
                unsafe_allow_html=True,
            )


def clean_ai_text(raw_text: str) -> str:
    text = str(raw_text or "").strip()
    text = text.replace("\\###", "###")
    text = re.sub(r"\[svg\]\([^)]*\)", "", text, flags=re.I)
    text = re.sub(r"<svg[\s\S]*?</svg>", "", text, flags=re.I)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def render_rca_ai_output(raw_text: str) -> None:
    """Render the live model response once inside a fully opaque RCA surface."""
    import html

    text = clean_ai_text(raw_text)
    if not text:
        st.info("No AI explanation was returned.")
        return

    aliases = {
        "primary root cause": "Primary Root Cause",
        "root cause": "Primary Root Cause",
        "contributing factors": "Contributing Factors",
        "evidence": "Contributing Factors",
        "evidence chain": "Contributing Factors",
        "operational impact": "Operational Impact",
        "business impact": "Operational Impact",
        "recommended action": "Recommended Action",
        "recommended actions": "Recommended Action",
        "confidence": "Confidence",
    }

    sections: dict[str, list[str]] = {}
    current: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer, current
        if current:
            body = "\n".join(buffer).strip()
            if body:
                sections.setdefault(current, []).append(body)
        buffer = []

    for line in text.splitlines():
        match = re.match(r"^\s*#{2,4}\s*(.+?)\s*$", line)
        if match:
            flush()
            raw_title = re.sub(r"[*_`]+", "", match.group(1)).strip().rstrip(":")
            current = aliases.get(raw_title.lower()) or raw_title.title()
        elif current:
            buffer.append(line)
    flush()

    if not sections:
        sections = {"AI Explanation": [text]}

    order = [
        ("Primary Root Cause", "cause", "🧠"),
        ("Contributing Factors", "factors", "🔎"),
        ("Operational Impact", "impact", "📊"),
        ("Recommended Action", "action", "✅"),
        ("Confidence", "confidence", "✓"),
        ("AI Explanation", "general", "✨"),
    ]

    def md_inline(value: str) -> str:
        value = html.escape(value, quote=False)
        value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
        value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
        return value

    def body_html(body: str) -> str:
        out = []
        ul = False
        ol = False

        def close():
            nonlocal ul, ol
            if ul:
                out.append("</ul>")
                ul = False
            if ol:
                out.append("</ol>")
                ol = False

        for raw in body.splitlines():
            line = raw.strip()
            if not line:
                close()
                continue
            mb = re.match(r"^[-*•]\s+(.*)$", line)
            mo = re.match(r"^\d+[.)]\s+(.*)$", line)
            if mb:
                if ol:
                    close()
                if not ul:
                    out.append("<ul>")
                    ul = True
                out.append(f"<li>{md_inline(mb.group(1))}</li>")
            elif mo:
                if ul:
                    close()
                if not ol:
                    out.append("<ol>")
                    ol = True
                out.append(f"<li>{md_inline(mo.group(1))}</li>")
            else:
                close()
                out.append(f"<p>{md_inline(line)}</p>")
        close()
        return "".join(out)

    cards = []
    rendered = set()
    for title, tone, icon in order:
        if title not in sections:
            continue
        rendered.add(title)
        body = "\n\n".join(x for x in sections[title] if x).strip()
        cards.append(
            f"<section class='ai-section-card {tone}'>"
            f"<div class='ai-section-title'><span class='ai-section-icon'>{icon}</span>{html.escape(title)}</div>"
            f"<div class='ai-section-body'>{body_html(body)}</div>"
            f"</section>"
        )

    for title, bodies in sections.items():
        if title in rendered:
            continue
        body = "\n\n".join(x for x in bodies if x).strip()
        cards.append(
            f"<section class='ai-section-card general'>"
            f"<div class='ai-section-title'><span class='ai-section-icon'>•</span>{html.escape(title)}</div>"
            f"<div class='ai-section-body'>{body_html(body)}</div>"
            f"</section>"
        )

    st.markdown(
        "<div class='ai-decision-brief-surface'>"
        "<div class='ai-brief-header'>"
        "<div><div class='ai-brief-kicker'>LIVE AI-GENERATED DECISION BRIEF</div>"
        "<div class='ai-brief-heading'>Case explanation generated from linked evidence</div></div>"
        "<div class='ai-live-pill'>● LIVE</div></div>"
        + "".join(cards)
        + "</div>",
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Global hero + workspace breadcrumb
# -----------------------------------------------------------------------------
st.markdown(
    "<div class='hero'><h1>◈ IntelliWarehouse AI</h1>"
    "<p>Detect → Correlate → Explain → Impact → Approve</p></div>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<div class='workspace-kicker'>WORKSPACE / {st.session_state.active_workspace}</div>",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Overview
# -----------------------------------------------------------------------------
if st.session_state.active_workspace == "Overview":
    page_header(
        "OPERATIONS OVERVIEW",
        "Warehouse health at a glance",
        "Start with the operational picture, then move through finding, understanding, and decision workspaces.",
    )

    overview_cards = [
        ("blue", "▦", "Materials", len(data.get("Material_Master", [])), "Master-data records in scope"),
        ("teal", "◫", "Inventory", len(data.get("Inventory_Stock", [])), "Stock records monitored"),
        ("amber", "↗", "Deliveries", len(data.get("Deliveries_Dispatch", [])), "Inbound / outbound delivery records"),
        ("purple", "▤", "Purchase Orders", len(data.get("Purchase_Replenish", [])), "Replenishment records"),
        ("red", "!", "Findings", len(dq) + len(anomalies), "Data-quality + process issues"),
        ("green", "⌁", "RCA Cases", len(cases), "Cross-system cases correlated"),
    ]
    cols = st.columns(6, gap="small")
    for col, (tone, icon, label, value, desc) in zip(cols, overview_cards):
        with col:
            st.markdown(
                f"<div class='overview-card {tone}'><div class='icon'>{icon}</div>"
                f"<div class='label'>{label}</div><div class='value'>{value:,}</div><div class='desc'>{desc}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div class='workflow-heading' style='margin-top:14px'>INVESTIGATION STATUS</div>", unsafe_allow_html=True)
    status_cards = [
        ("dq", "01", "Data quality", len(dq), "Findings requiring review"),
        ("process", "02", "Process anomalies", len(anomalies), "Operational exceptions"),
        ("rca", "03", "Root-cause cases", len(cases), "Correlated investigations"),
        ("approval", "04", "Pending approval", pending, "Awaiting human decision"),
    ]
    status_cols = st.columns(4, gap="small")
    for col, (tone, step, title, value, sub) in zip(status_cols, status_cards):
        with col:
            st.markdown(
                f"<div class='ops-status-card {tone}'><div class='ops-top'><span class='ops-step'>{step}</span>"
                f"<span class='ops-title'>{title}</span></div><div class='ops-value'>{value:,}</div>"
                f"<div class='ops-sub'>{sub}</div></div>",
                unsafe_allow_html=True,
            )

    attention = []
    if critical_count:
        attention.append(f"<div class='attention-item critical'><span class='attention-dot'></span><b>{critical_count}</b> Critical</div>")
    if high_count:
        attention.append(f"<div class='attention-item high'><span class='attention-dot'></span><b>{high_count}</b> High</div>")
    if pending:
        attention.append(f"<div class='attention-item pending'><span class='attention-dot'></span><b>{pending}</b> Pending approval</div>")

    if attention:
        st.markdown(
            "<div class='attention-panel'><div class='attention-heading'><span class='attention-title'>Needs attention</span>"
            "<span class='attention-caption'>Items requiring operator review</span></div>"
            f"<div class='attention-items'>{''.join(attention)}</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='attention-panel clear'><div class='attention-heading'><span class='attention-title'>Status</span>"
            "<span class='attention-caption'>Current operational health</span></div>"
            "<div class='attention-clear'>✓ No critical or high-priority items are currently flagged.</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div class='workflow-heading'>INVESTIGATION WORKFLOW</div><div class='workflow-subheading'>Three decisions, three destinations</div>", unsafe_allow_html=True)
    workflow = [
        ("find", "01", "🔎", "FIND", "What needs attention?", f"<b>{len(dq):,}</b> data-quality findings and <b>{len(anomalies):,}</b> process/inventory anomalies.", "Data Quality"),
        ("understand", "02", "🧠", "UNDERSTAND", "Why is it happening?", f"<b>{len(cases):,}</b> correlated cases connect materials, inventory, deliveries, POs and vendors.", "Correlated Cases"),
        ("decide", "03", "✅", "DECIDE", "What should happen next?", f"<b>{pending:,}</b> cases await human approval. Proposed actions remain simulated until approved.", "Approvals"),
    ]
    cols = st.columns(3, gap="medium")
    for col, item in zip(cols, workflow):
        tone, step, icon, kicker, title, body, destination = item
        with col:
            st.markdown(
                f"<div class='workflow-card {tone}'><div class='workflow-top'><div class='workflow-icon'>{icon}</div>"
                f"<div class='workflow-step'>{step}</div></div><div class='workflow-kicker'>{kicker}</div>"
                f"<div class='workflow-title'>{title}</div><div class='workflow-body'>{body}</div>"
                f"<div class='workflow-destination'>Open {destination} →</div></div>",
                unsafe_allow_html=True,
            )
    st.markdown(
        "<div class='overview-help'><span class='help-icon'>i</span><div><b>Next step:</b> use the sidebar to move from findings → correlation → root cause → trace → human approval.</div></div>",
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# Data Quality
# -----------------------------------------------------------------------------
elif st.session_state.active_workspace == "Data Quality":
    page_header("FINDINGS", "Data-quality findings", "Prioritize the records that need investigation, then open one finding for evidence.")
    if dq.empty:
        st.success("No data-quality findings.")
    else:
        severity_cards(dq)
        c1, c2, c3 = st.columns([1, 1, 1.8])
        with c1:
            severity_filter = st.selectbox("Severity", ["All", "Critical", "High", "Medium", "Low"], key="dq_severity")
        with c2:
            entity_options = ["All"] + sorted(dq["entity"].astype(str).dropna().unique().tolist())
            entity_filter = st.selectbox("Record", entity_options, key="dq_entity")
        with c3:
            search = st.text_input("Search finding", placeholder="ID, issue, record, or explanation", key="dq_search")

        filtered = dq.copy()
        if severity_filter != "All":
            filtered = filtered[filtered["severity"].astype(str).str.title() == severity_filter]
        if entity_filter != "All":
            filtered = filtered[filtered["entity"].astype(str) == entity_filter]
        if search.strip():
            q = search.strip().lower()
            mask = False
            for col in ["issue_id", "entity", "title", "detail"]:
                if col in filtered.columns:
                    mask = mask | filtered[col].astype(str).str.lower().str.contains(q, na=False)
            filtered = filtered[mask]

        st.caption(f"Showing {len(filtered):,} of {len(dq):,} data-quality findings")
        view = filtered[["issue_id", "severity", "entity", "title", "detail"]].copy()
        view.columns = ["ID", "Severity", "Record", "Issue", "Explanation"]
        view["Explanation"] = view["Explanation"].astype(str).str.replace(r"\s+", " ", regex=True).str.slice(0, 150)
        st.dataframe(view, width="stretch", hide_index=True, height=330)
        st.download_button("Export findings", filtered.to_csv(index=False).encode("utf-8"), "intelliwarehouse_data_quality_findings.csv", "text/csv")

        st.markdown("### Explain a finding")
        choice = st.selectbox(
            "Finding",
            filtered["issue_id"].astype(str).tolist() or dq["issue_id"].astype(str).tolist(),
            key="dq_explain_choice",
        )
        if st.button("Explain selected finding", type="primary", key="dq_explain"):
            row = dq[dq["issue_id"].astype(str).eq(str(choice))].iloc[0]
            context = build_finding_context(row)
            with st.spinner("Copilot is checking the exact finding and connected records..."):
                try:
                    st.markdown(copilot_answer(f"Explain {choice} in detail. Start with the exact finding, direct evidence, why it matters, related risks, and safest next step.", context))
                except Exception as exc:
                    st.error(f"Copilot error: {exc}")

# -----------------------------------------------------------------------------
# Inventory & Process
# -----------------------------------------------------------------------------
elif st.session_state.active_workspace == "Inventory & Process":
    page_header("OPERATIONS", "Inventory & process anomalies", "Review operational exceptions, identify high-impact issues, and inspect the records behind them.")
    if anomalies.empty:
        st.success("No inventory/process anomalies.")
    else:
        severity_cards(anomalies)
        c1, c2, c3 = st.columns([1, 1, 1.8])
        with c1:
            severity_filter = st.selectbox("Severity", ["All", "Critical", "High", "Medium", "Low"], key="an_severity")
        with c2:
            entity_options = ["All"] + sorted(anomalies["entity"].astype(str).dropna().unique().tolist())
            entity_filter = st.selectbox("Record", entity_options, key="an_entity")
        with c3:
            search = st.text_input("Search anomaly", placeholder="ID, issue, record, or explanation", key="an_search")

        filtered = anomalies.copy()
        if severity_filter != "All":
            filtered = filtered[filtered["severity"].astype(str).str.title() == severity_filter]
        if entity_filter != "All":
            filtered = filtered[filtered["entity"].astype(str) == entity_filter]
        if search.strip():
            q = search.strip().lower()
            mask = False
            for col in ["issue_id", "entity", "title", "detail"]:
                if col in filtered.columns:
                    mask = mask | filtered[col].astype(str).str.lower().str.contains(q, na=False)
            filtered = filtered[mask]

        st.caption(f"Showing {len(filtered):,} of {len(anomalies):,} inventory/process anomalies")
        view = filtered[["issue_id", "severity", "entity", "title", "detail"]].copy()
        view.columns = ["ID", "Severity", "Record", "Issue", "Explanation"]
        view["Explanation"] = view["Explanation"].astype(str).str.replace(r"\s+", " ", regex=True).str.slice(0, 150)
        st.dataframe(view, width="stretch", hide_index=True, height=360)
        st.download_button(
            "Export anomalies",
            filtered.to_csv(index=False).encode("utf-8"),
            "intelliwarehouse_inventory_process_anomalies.csv",
            "text/csv",
        )

        st.markdown("### Explain an inventory / process anomaly")
        anomaly_choices = (
            filtered["issue_id"].astype(str).tolist()
            or anomalies["issue_id"].astype(str).tolist()
        )
        anomaly_choice = st.selectbox(
            "Anomaly",
            anomaly_choices,
            key="an_explain_choice",
        )

        if st.button(
            "Explain selected anomaly",
            type="primary",
            key="an_explain",
        ):
            row = anomalies[
                anomalies["issue_id"].astype(str).eq(str(anomaly_choice))
            ].iloc[0]
            context = build_finding_context(row)

            with st.spinner(
                "Copilot is checking the exact anomaly and connected records..."
            ):
                try:
                    answer = copilot_answer(
                        (
                            f"Explain {anomaly_choice} in detail. "
                            "Start with the exact anomaly, direct workbook evidence, "
                            "the likely operational cause, why it matters, related "
                            "inventory/process risks, and the safest next step. "
                            "Use exact quantities, IDs, statuses and dates from the evidence."
                        ),
                        context,
                    )
                    st.markdown(
                        "<div class='copilot-result-label'>AI COPILOT ANALYSIS</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(answer)
                except Exception as exc:
                    st.error(f"Copilot error: {exc}")

# -----------------------------------------------------------------------------
# Correlated Cases
# -----------------------------------------------------------------------------
elif st.session_state.active_workspace == "Correlated Cases":
    page_header("OPERATIONS", "Correlated root-cause cases", "Prioritize cross-system cases by severity and impact before opening Root Cause AI.")
    if cases.empty:
        st.info("No correlated cases detected.")
    else:
        severity_cards(cases)
        c1, c2, c3 = st.columns([1, 1, 1.8])
        with c1:
            severity_filter = st.selectbox("Severity", ["All", "Critical", "High", "Medium", "Low"], key="case_severity")
        with c2:
            materials = ["All"] + sorted(cases["material"].astype(str).dropna().unique().tolist())
            material_filter = st.selectbox("Material", materials, key="case_material")
        with c3:
            search = st.text_input("Search case", placeholder="Case ID, material, signal, or root cause", key="case_search")

        filtered = cases.copy()
        if severity_filter != "All":
            filtered = filtered[filtered["severity"].astype(str).str.title() == severity_filter]
        if material_filter != "All":
            filtered = filtered[filtered["material"].astype(str) == material_filter]
        if search.strip():
            q = search.strip().lower()
            mask = False
            for col in ["case_id", "material", "signals", "root_cause"]:
                if col in filtered.columns:
                    mask = mask | filtered[col].astype(str).str.lower().str.contains(q, na=False)
            filtered = filtered[mask]

        st.caption(f"Showing {len(filtered):,} of {len(cases):,} correlated cases")
        view = filtered[["case_id", "material", "severity", "impact_score", "signals", "root_cause", "recommended_action"]].copy()
        view["signals"] = view["signals"].apply(lambda x: ", ".join(map(str, x)) if isinstance(x, (list, tuple)) else str(x))
        view["root_cause"] = view["root_cause"].astype(str).str.replace(r"\s+", " ", regex=True).str.slice(0, 125)
        view["recommended_action"] = view["recommended_action"].astype(str).str.replace(r"\s+", " ", regex=True).str.slice(0, 110)
        view.columns = ["Case", "Material", "Severity", "Impact", "Signals", "Root cause", "Recommended fix"]
        st.dataframe(view, width="stretch", hide_index=True, height=360)
        st.download_button("Export correlated cases", filtered.to_csv(index=False).encode("utf-8"), "intelliwarehouse_correlated_cases.csv", "text/csv")

# -----------------------------------------------------------------------------
# Root Cause AI
# -----------------------------------------------------------------------------
elif st.session_state.active_workspace == "Root Cause AI":
    page_header(
        "AI INVESTIGATION",
        "Root Cause AI",
        "Select a correlated case, then generate an AI decision brief from the linked evidence.",
    )

    if cases.empty:
        st.info("No correlated cases available.")
    else:
        labels = [
            f"{r.case_id} · {r.material} · {r.severity} · {int(r.impact_score)}/100"
            for _, r in cases.iterrows()
        ]

        idx = st.selectbox(
            "Select case",
            range(len(labels)),
            format_func=lambda i: labels[i],
            key="rca_case",
        )
        case = cases.iloc[idx].to_dict()
        cid = str(case.get("case_id", ""))
        previous_case = st.session_state.get("rca_selected_case_id")
        if previous_case != cid:
            st.session_state.rca_selected_case_id = cid
            st.session_state.ai_error = None
        material = str(case.get("material", ""))
        severity = str(case.get("severity", "Unknown")).title()
        impact = int(case.get("impact_score", 0) or 0)

        sev_tone = (
            "critical"
            if severity.lower() == "critical"
            else "high"
            if severity.lower() == "high"
            else "medium"
        )

        st.markdown(
            f"""
            <div class="rca-case-strip">
                <div>
                    <div class="rca-label">SELECTED CASE</div>
                    <div class="rca-case-id">{cid}</div>
                    <div class="rca-material">Material · {material}</div>
                </div>
                <div class="rca-case-right">
                    <span class="rca-severity {sev_tone}">{severity}</span>
                    <span class="rca-impact">Impact <b>{impact}/100</b></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        signals = case.get("signals", [])
        if isinstance(signals, (list, tuple)):
            signals = [str(x).strip() for x in signals if str(x).strip()]
        elif str(signals).strip():
            signals = [str(signals).strip()]
        else:
            signals = []

        # Evidence context only. Do not show the deterministic root_cause or
        # recommended_action fields on this page.
        left, right = st.columns([1.45, 1], gap="medium")

        with left:
            st.markdown(
                """
                <div class="rca-panel rca-evidence">
                    <div class="rca-panel-head">
                        <span class="rca-panel-icon">🔎</span>
                        <div>
                            <div class="rca-panel-kicker">EVIDENCE INPUT</div>
                            <div class="rca-panel-title">Signals supplied to AI</div>
                        </div>
                    </div>
                """,
                unsafe_allow_html=True,
            )
            if signals:
                for signal in signals[:8]:
                    st.markdown(
                        f"<div class='rca-evidence-row'><span class='rca-check'>✓</span><span>{signal}</span></div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    "<div class='rca-muted'>No case-level signals recorded.</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

        with right:
            linked = [(sheet, rows) for sheet, rows in (case.get("evidence", {}) or {}).items() if rows]
            total_linked = sum(len(rows) for _, rows in linked)

            st.markdown(
                f"""
                <div class="rca-panel rca-impact-panel">
                    <div class="rca-panel-head">
                        <span class="rca-panel-icon">📊</span>
                        <div>
                            <div class="rca-panel-kicker">CASE CONTEXT</div>
                            <div class="rca-panel-title">Impact & evidence coverage</div>
                        </div>
                    </div>
                    <div class="rca-impact-score">{impact}<span>/100</span></div>
                    <div class="rca-impact-track"><div class="rca-impact-fill" style="width:{max(0,min(100,impact))}%"></div></div>
                    <div class="rca-context-row">
                        <span>Linked records</span><b>{total_linked}</b>
                    </div>
                    <div class="rca-impact-note">The AI brief is generated from this selected case and its linked evidence.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            """
            <div class="rca-ai-box">
                <div class="rca-ai-kicker">GENERATIVE ANALYSIS</div>
                <div class="rca-ai-title">Generate one evidence-grounded decision brief</div>
                <div class="rca-ai-copy">The RCA below is rendered only from the live VW Group LLMaaS response. No deterministic case finding is shown as the RCA.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Generate AI explanation",
            type="primary",
            key=f"generate_rca_{cid}",
            use_container_width=False,
        ):
            with st.spinner("Generating Root Cause AI analysis..."):
                try:
                    result = generate_root_cause(case)
                    st.session_state.ai_cache[cid] = result
                    st.session_state.ai_error = None
                except Exception as exc:
                    st.session_state.ai_cache.pop(cid, None)
                    st.session_state.ai_error = str(exc)

        if st.session_state.get("ai_error"):
            st.error(
                "AI generation failed. No fallback case findings are shown. "
                f"Details: {st.session_state.ai_error}"
            )

        if cid in st.session_state.ai_cache:
            render_rca_ai_output(st.session_state.ai_cache[cid])
        else:
            st.markdown(
                """
                <div class="rca-awaiting">
                    <div class="rca-awaiting-icon">✨</div>
                    <div>
                        <div class="rca-awaiting-title">AI analysis ready to run</div>
                        <div class="rca-awaiting-copy">Generate the brief to populate this workspace with the model's root cause, contributing factors, operational impact, recommended action, and confidence.</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if linked:
            with st.expander(f"Supporting records · {total_linked} linked rows"):
                for sheet, rows in linked:
                    st.markdown(f"**{sheet}** · {len(rows)} rows")
                    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

# -----------------------------------------------------------------------------
# Trace Graph
# -----------------------------------------------------------------------------
elif st.session_state.active_workspace == "Trace Graph":
    page_header("CORRELATION", "Trace Graph", "Follow one material across master data, inventory, storage, deliveries, replenishment, and vendor records.")
    if cases.empty:
        st.info("No correlated cases available.")
    else:
        material = st.selectbox("Material to trace", cases["material"].astype(str).tolist(), key="trace_material")
        mm = data["Material_Master"]
        iv = data["Inventory_Stock"]
        bb = data["Warehouse_Bin"]
        dd = data["Deliveries_Dispatch"]
        pp = data["Purchase_Replenish"]
        vv = data["Vendor_Master"]

        mm1 = mm[mm["Material"].astype(str).eq(material)]
        iv1 = iv[iv["Material"].astype(str).eq(material)]
        bb1 = bb[bb["Assigned Material"].astype(str).eq(material)]
        dd1 = dd[dd["Material"].astype(str).eq(material)]
        pp1 = pp[pp["Material"].astype(str).eq(material)]
        vendors = set(pp1["Vendor"].astype(str)) if not pp1.empty and "Vendor" in pp1.columns else set()
        vv1 = vv[vv["Vendor"].astype(str).isin(vendors)]

        trace_cols = st.columns(6, gap="small")
        chain = [
            ("Material", len(mm1)), ("Inventory", len(iv1)), ("Warehouse Bin", len(bb1)),
            ("Deliveries", len(dd1)), ("Purchase Orders", len(pp1)), ("Vendor", len(vv1)),
        ]
        for col, (name, count) in zip(trace_cols, chain):
            with col:
                st.markdown(f"<div class='trace-node'><strong>{name}</strong><br><small>{count} linked rows</small></div>", unsafe_allow_html=True)
        st.markdown("### Connected evidence")
        datasets = [
            ("Material Master", mm1), ("Inventory", iv1), ("Warehouse Bins", bb1),
            ("Deliveries", dd1), ("Purchase Orders", pp1), ("Vendor Master", vv1),
        ]
        for title, frame in datasets:
            with st.expander(f"{title} · {len(frame)} linked rows"):
                st.dataframe(frame, width="stretch", hide_index=True)

# -----------------------------------------------------------------------------
# Approvals
# -----------------------------------------------------------------------------
elif st.session_state.active_workspace == "Approvals":
    page_header("GOVERNED ACTION", "Human approval gate", "The Action Agent proposes. A human decides. Execution remains simulated.")
    if cases.empty:
        st.info("No cases awaiting action.")
    for _, row in cases.iterrows():
        cid = str(row["case_id"])
        state = st.session_state.actions.get(cid, {"status": "Pending", "approver": "", "note": "", "action": row["recommended_action"]})
        with st.expander(f"{cid} · {row['material']} · {row['severity']} · {int(row['impact_score'])}/100"):
            st.markdown(f"**Root cause:** {row['root_cause']}")
            action = st.text_area("Proposed action", state["action"], key=f"approval_action_{cid}")
            approver = st.text_input("Approver name / role", state["approver"], key=f"approval_person_{cid}")
            note = st.text_area("Decision note", state["note"], key=f"approval_note_{cid}")
            c1, c2, c3 = st.columns(3)
            if c1.button("Approve", key=f"approve_{cid}"):
                if not approver.strip():
                    st.error("Approver is required.")
                else:
                    now = datetime.now().isoformat(timespec="seconds")
                    st.session_state.actions[cid] = {"status": "Approved", "approver": approver, "note": note, "action": action}
                    st.session_state.audit.append({"timestamp": now, "case": cid, "status": "Approved", "agent": "Action Agent", "approver": approver, "what": action, "why": row["root_cause"]})
                    st.rerun()
            if c2.button("Simulate Execute", key=f"simulate_{cid}"):
                if not approver.strip():
                    st.error("Approver is required for simulation.")
                else:
                    now = datetime.now().isoformat(timespec="seconds")
                    st.session_state.actions[cid] = {"status": "Simulated", "approver": approver, "note": note, "action": action}
                    st.session_state.audit.append({"timestamp": now, "case": cid, "status": "Simulated", "agent": "Action Agent", "approver": approver, "what": action, "why": row["root_cause"]})
                    st.rerun()
            if c3.button("Reject", key=f"reject_{cid}"):
                now = datetime.now().isoformat(timespec="seconds")
                operator = approver.strip() or "Operator"
                st.session_state.actions[cid] = {"status": "Rejected", "approver": operator, "note": note, "action": action}
                st.session_state.audit.append({"timestamp": now, "case": cid, "status": "Rejected", "agent": "Action Agent", "approver": operator, "what": action, "why": row["root_cause"]})
                st.rerun()
            st.caption(f"Current status: {state['status']}")

# -----------------------------------------------------------------------------
# Copilot
# -----------------------------------------------------------------------------
elif st.session_state.active_workspace == "Copilot":
    page_header("AI ASSISTANT", "AI Warehouse Copilot", "Ask about findings, materials, inventory, deliveries, POs, vendors, or workbook-wide issues.")
    question = st.text_input(
        "Ask the warehouse",
        placeholder="Explain DQ-0102 · Why is MAT-100030 blocked? · How many overdue deliveries?",
        key="copilot_question",
    )
    if question:
        with st.spinner("Copilot is analyzing the workbook..."):
            try:
                st.markdown(copilot_workbook_answer(question, dq, anomalies, data))
            except Exception as exc:
                st.error(f"Copilot error: {exc}")

# -----------------------------------------------------------------------------
# Data Explorer
# -----------------------------------------------------------------------------
elif st.session_state.active_workspace == "Data Explorer":
    page_header("SOURCE DATA", "Data Explorer", "Inspect the workbook records underlying the AI detections and correlated cases.")
    visible = [name for name in data if name not in {"README", "Data_Dictionary"}]
    sheet = st.selectbox("Sheet", visible, key="explorer_sheet")
    frame = data[sheet]
    st.caption(f"{len(frame):,} rows · {len(frame.columns):,} columns")
    st.dataframe(frame, width="stretch", hide_index=True, height=520)
    st.download_button("Export selected sheet", frame.to_csv(index=False).encode("utf-8"), f"{sheet}.csv", "text/csv")

# -----------------------------------------------------------------------------
# Audit
# -----------------------------------------------------------------------------
elif st.session_state.active_workspace == "Audit":
    page_header("GOVERNANCE", "Audit Trail", "Review human decisions and simulated actions recorded during this session.")
    if st.session_state.audit:
        st.dataframe(pd.DataFrame(st.session_state.audit), width="stretch", hide_index=True, height=460)
        st.download_button("Export audit trail", pd.DataFrame(st.session_state.audit).to_csv(index=False).encode("utf-8"), "intelliwarehouse_audit.csv", "text/csv")
    else:
        st.info("No human decisions recorded in this session.")
