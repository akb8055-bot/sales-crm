import json
import base64
import calendar
import html
import os
import re
from copy import deepcopy
from io import BytesIO
from datetime import date, datetime, timezone
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Custom Sales CRM", page_icon="📈", layout="wide")

APP_RELEASE = "2026-07-31-r5"
DOWNLOADS_DIR = Path.home() / "Downloads"
COMPANY_LOGO_SOURCE = DOWNLOADS_DIR / "WhatsApp_Image_2026-07-08_at_15.51.12__1_-removebg-preview.png"
COMPANY_LOGO_FALLBACK = DOWNLOADS_DIR / "WhatsApp Image 2026-07-08 at 15.51.12.jpeg"

DATA_FILE = Path(__file__).parent / "crm_data.json"
SUPABASE_TABLE = "crm_state"
SUPABASE_ROW_ID = "default"
STATUSES = [
    "New Lead",
    "Contacted",
    "Qualified",
    "Proposal Sent",
    "Negotiation",
    "Won",
    "Lost",
]
QUOTE_STATUSES = ["Draft", "Sent", "Accepted", "Rejected"]
CONNECTED_STATUSES = {"Contacted", "Qualified", "Proposal Sent", "Negotiation", "Won"}


SAMPLE_DATA = {
    "customers": [],
    "prospects": [],
    "quotations": [],
    "technical_drawings": [],
    "purchase_orders": [],
    "tasks": [],
    "prospect_attachments": {},
    "customer_attachments": {},
    "activity_log": [],
}


def _get_secret_or_env(name: str, default: str = "") -> str:
    value = ""
    try:
        value = str(st.secrets.get(name, "")).strip()
    except Exception:
        value = ""
    if value:
        return value
    return os.getenv(name, default).strip()


@st.cache_resource(show_spinner=False)
def get_supabase_client() -> Any | None:
    url = _get_secret_or_env("SUPABASE_URL")
    key = _get_secret_or_env("SUPABASE_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client
    except Exception:
        return None

    try:
        return create_client(url, key)
    except Exception:
        return None


def _is_supabase_enabled() -> bool:
    return bool(get_supabase_client())


def _load_local_data() -> dict[str, Any]:
    if not DATA_FILE.exists():
        default_data = deepcopy(SAMPLE_DATA)
        _save_local_data(default_data)
        return default_data

    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_local_data(data: dict[str, Any]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _load_supabase_data() -> dict[str, Any] | None:
    client = get_supabase_client()
    if client is None:
        return None

    table_name = _get_secret_or_env("SUPABASE_TABLE", SUPABASE_TABLE) or SUPABASE_TABLE
    row_id = _get_secret_or_env("SUPABASE_ROW_ID", SUPABASE_ROW_ID) or SUPABASE_ROW_ID
    try:
        result = client.table(table_name).select("payload").eq("id", row_id).limit(1).execute()
    except Exception:
        return None

    rows = getattr(result, "data", None) or []
    if not rows:
        return None

    payload = rows[0].get("payload")
    if isinstance(payload, dict):
        return payload
    return None


def _save_supabase_data(data: dict[str, Any]) -> bool:
    client = get_supabase_client()
    if client is None:
        return False

    table_name = _get_secret_or_env("SUPABASE_TABLE", SUPABASE_TABLE) or SUPABASE_TABLE
    row_id = _get_secret_or_env("SUPABASE_ROW_ID", SUPABASE_ROW_ID) or SUPABASE_ROW_ID
    record = {
        "id": row_id,
        "payload": data,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        client.table(table_name).upsert(record).execute()
        return True
    except Exception:
        return False


def style_app() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

            :root {
                --ink: #0f2130;
                --muted: #5f7283;
                --paper: #f4f8fb;
                --glass: rgba(255, 255, 255, 0.88);
                --accent: #0f9d90;
                --accent-2: #ff8f00;
                --accent-3: #0b6acb;
                --ok: #1f9d55;
                --warn: #d97706;
            }

            .stApp {
                font-family: 'Plus Jakarta Sans', sans-serif;
                color: var(--ink);
                background:
                    radial-gradient(circle at 8% 4%, rgba(15, 157, 144, 0.16), transparent 31%),
                    radial-gradient(circle at 92% 7%, rgba(255, 143, 0, 0.13), transparent 34%),
                    linear-gradient(165deg, #f9fcff 0%, #eef5fb 52%, #f7f9f4 100%);
            }

            .block-container {
                padding-top: 1.2rem !important;
                padding-bottom: 2.1rem !important;
                max-width: 1320px;
            }

            h1, h2, h3 {
                letter-spacing: -0.02em;
                color: var(--ink);
            }

            @keyframes fadeUp {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .hero {
                background: linear-gradient(135deg, #103d5d 0%, #0f7f74 58%, #2c8ad6 100%);
                border-radius: 22px;
                padding: 22px 26px;
                color: #effbff;
                margin-bottom: 14px;
                border: 1px solid rgba(255, 255, 255, 0.22);
                box-shadow: 0 18px 40px rgba(8, 24, 41, 0.26);
                animation: fadeUp 0.45s ease-out;
            }

            .hero-eyebrow {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 6px 10px;
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.12);
                color: #ebfffd;
                font-size: 0.78rem;
                text-transform: uppercase;
                letter-spacing: 0.12em;
                margin-bottom: 12px;
            }

            .hero-title {
                margin: 0;
                font-size: 2.05rem;
                line-height: 1.1;
            }

            .hero p {
                margin: 4px 0 0;
                color: #ccf0ed;
            }

            .hero-subtitle {
                max-width: 68ch;
                font-size: 0.96rem;
                line-height: 1.55;
                color: #d5f6f1;
                margin-top: 10px;
            }

            .workspace-hero {
                position: relative;
                overflow: hidden;
                background: linear-gradient(140deg, rgba(255,255,255,0.94) 0%, rgba(241,249,255,0.94) 56%, rgba(238,250,246,0.94) 100%);
                border: 1px solid rgba(16, 61, 85, 0.12);
                border-radius: 20px;
                padding: 16px 18px;
                margin: 0 0 12px;
                box-shadow: 0 12px 28px rgba(10, 34, 50, 0.08);
                animation: fadeUp 0.45s ease-out;
            }

            .workspace-hero::before {
                content: '';
                position: absolute;
                left: 0;
                top: 0;
                bottom: 0;
                width: 5px;
                background: linear-gradient(180deg, var(--accent-3), var(--accent));
            }

            .workspace-kicker {
                display: inline-block;
                font-size: 0.72rem;
                text-transform: uppercase;
                letter-spacing: 0.13em;
                color: #235171;
                background: rgba(15, 126, 114, 0.10);
                border: 1px solid rgba(15, 126, 114, 0.18);
                border-radius: 999px;
                padding: 4px 10px;
                margin-bottom: 8px;
                font-weight: 700;
            }

            .workspace-title {
                margin: 0;
                color: #112f45;
                letter-spacing: -0.02em;
                font-size: 1.35rem;
                font-weight: 800;
            }

            .workspace-copy {
                margin: 6px 0 0;
                color: #4e6373;
                font-size: 0.92rem;
                line-height: 1.5;
                max-width: 90ch;
            }

            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 12px;
                margin: 12px 0 6px;
            }

            .stat-card {
                background: rgba(255, 255, 255, 0.93);
                border: 1px solid rgba(13, 40, 60, 0.08);
                border-radius: 18px;
                padding: 16px 18px 16px 20px;
                box-shadow: 0 14px 30px rgba(11, 33, 49, 0.09);
                position: relative;
                overflow: hidden;
                animation: fadeUp 0.42s ease-out;
            }

            .stat-card:nth-child(2) { animation-delay: 0.05s; }
            .stat-card:nth-child(3) { animation-delay: 0.1s; }
            .stat-card:nth-child(4) { animation-delay: 0.15s; }
            .stat-card:nth-child(5) { animation-delay: 0.2s; }
            .stat-card:nth-child(6) { animation-delay: 0.25s; }

            .stat-card::before {
                content: '';
                position: absolute;
                inset: 0 auto 0 0;
                width: 4px;
                background: linear-gradient(180deg, var(--accent), var(--accent-2));
            }

            .stat-label {
                color: var(--muted);
                font-size: 0.8rem;
                text-transform: uppercase;
                letter-spacing: 0.12em;
                margin-bottom: 8px;
            }

            .stat-value {
                font-size: 1.55rem;
                font-weight: 700;
                letter-spacing: -0.03em;
                margin-bottom: 4px;
            }

            .stat-footnote {
                color: var(--muted);
                font-size: 0.88rem;
            }

            .section-card {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(16, 42, 58, 0.09);
                border-radius: 20px;
                padding: 18px;
                box-shadow: 0 16px 32px rgba(10, 27, 41, 0.08);
                margin-bottom: 4px;
                animation: fadeUp 0.4s ease-out;
            }

            .section-card h3 {
                margin-top: 0;
            }

            .status-strip {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                gap: 10px;
                margin: 10px 0 0;
            }

            .status-pill {
                border-radius: 14px;
                padding: 10px 12px;
                background: #f4fbff;
                border: 1px solid rgba(15, 51, 73, 0.08);
            }

            .status-pill .label {
                display: block;
                color: var(--muted);
                font-size: 0.76rem;
                text-transform: uppercase;
                letter-spacing: 0.12em;
                margin-bottom: 5px;
            }

            .status-pill .value {
                font-weight: 700;
                font-size: 1rem;
            }

            .empty-state {
                border: 1px dashed rgba(15, 30, 42, 0.18);
                border-radius: 16px;
                padding: 16px;
                background: rgba(255, 255, 255, 0.75);
                color: var(--muted);
            }

            .timeline-item {
                padding: 12px 0;
                border-bottom: 1px solid rgba(15, 30, 42, 0.08);
            }

            .timeline-item:last-child {
                border-bottom: 0;
                padding-bottom: 0;
            }

            .timeline-meta {
                color: var(--muted);
                font-size: 0.82rem;
                margin-top: 4px;
            }

            .chart-shell {
                background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(244,251,255,0.9));
                border: 1px solid rgba(14, 27, 39, 0.10);
                border-radius: 22px;
                padding: 18px 18px 10px;
                box-shadow:
                    0 18px 34px rgba(9, 27, 38, 0.11),
                    0 0 0 1px rgba(255,255,255,0.45) inset,
                    0 0 24px rgba(11, 106, 203, 0.10);
            }

            .chart-shell::before {
                content: '';
                display: block;
                height: 4px;
                border-radius: 999px;
                margin: -6px 0 14px;
                background: linear-gradient(90deg, #0ea5a4 0%, #38bdf8 45%, #f97316 100%);
                box-shadow: 0 0 18px rgba(14, 165, 164, 0.45);
            }

            .report-hero {
                background: linear-gradient(135deg, rgba(18, 70, 110, 0.96), rgba(14, 126, 114, 0.92));
                color: #effdf9;
                border-radius: 22px;
                padding: 18px 20px;
                border: 1px solid rgba(255,255,255,0.14);
                box-shadow: 0 18px 36px rgba(10, 24, 38, 0.18);
                margin-bottom: 14px;
            }

            .report-hero h3 {
                margin: 0;
                font-size: 1.3rem;
            }

            .report-hero p {
                margin: 6px 0 0;
                color: #d6fbf7;
                line-height: 1.5;
            }

            .report-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 12px;
                margin: 12px 0 16px;
            }

            .report-card {
                background: rgba(255,255,255,0.93);
                border: 1px solid rgba(15, 30, 42, 0.08);
                border-radius: 18px;
                padding: 16px 18px;
                box-shadow: 0 12px 24px rgba(15, 31, 45, 0.08);
            }

            .report-card .kpi-label {
                color: var(--muted);
                font-size: 0.76rem;
                text-transform: uppercase;
                letter-spacing: 0.12em;
                margin-bottom: 8px;
            }

            .report-card .kpi-value {
                font-size: 1.45rem;
                font-weight: 700;
                margin-bottom: 6px;
            }

            .report-card .kpi-note {
                color: var(--muted);
                font-size: 0.9rem;
                line-height: 1.45;
            }

            .report-section {
                background: rgba(255,255,255,0.88);
                border: 1px solid rgba(15, 30, 42, 0.08);
                border-radius: 20px;
                padding: 18px;
                box-shadow: 0 12px 24px rgba(15, 31, 45, 0.06);
                margin-bottom: 14px;
            }

            .report-section h4 {
                margin-top: 0;
            }

            .report-note {
                background: linear-gradient(90deg, rgba(14,165,164,0.10), rgba(249,115,22,0.08));
                border-left: 4px solid var(--accent);
                border-radius: 12px;
                padding: 12px 14px;
                color: var(--ink);
                margin: 12px 0 0;
            }

            .metric-card {
                background: var(--glass);
                border: 1px solid rgba(16, 30, 42, 0.08);
                border-radius: 16px;
                padding: 14px;
                backdrop-filter: blur(6px);
            }

            .pipeline-card {
                background: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(16, 58, 82, 0.12);
                border-radius: 12px;
                padding: 10px;
                margin-bottom: 10px;
                box-shadow: 0 8px 18px rgba(14, 33, 48, 0.08);
            }

            .pipeline-card.heat-cool {
                border-left: 4px solid rgba(56, 189, 248, 0.9);
            }

            .pipeline-card.heat-warm {
                border-left: 4px solid rgba(249, 115, 22, 0.9);
            }

            .pipeline-card.heat-hot {
                border-left: 4px solid rgba(239, 68, 68, 0.9);
                box-shadow: 0 12px 24px rgba(239, 68, 68, 0.14);
            }

            .pipeline-title {
                font-weight: 700;
                margin-bottom: 6px;
            }

            .pipeline-badge {
                display: inline-flex;
                border-radius: 999px;
                padding: 3px 10px;
                font-size: 0.68rem;
                text-transform: uppercase;
                letter-spacing: 0.09em;
                font-weight: 800;
                margin-bottom: 7px;
                border: 1px solid rgba(17, 58, 83, 0.2);
                color: #13415f;
                background: #e6f2fc;
            }

            .badge-qualified {
                background: rgba(11, 106, 203, 0.12);
                color: #0e4b8a;
                border-color: rgba(11, 106, 203, 0.28);
            }

            .badge-proposal {
                background: rgba(249, 115, 22, 0.12);
                color: #9a460e;
                border-color: rgba(249, 115, 22, 0.28);
            }

            .badge-negotiation {
                background: rgba(234, 179, 8, 0.14);
                color: #8c5e02;
                border-color: rgba(234, 179, 8, 0.32);
            }

            .pipeline-board {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 12px;
                margin-top: 10px;
            }

            .pipeline-lane {
                background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(246,251,255,0.93));
                border: 1px solid rgba(16, 60, 88, 0.12);
                border-radius: 16px;
                padding: 12px;
                box-shadow: 0 10px 24px rgba(12, 32, 46, 0.08);
                min-height: 120px;
            }

            .pipeline-lane.focus-qualified {
                border-color: rgba(11, 106, 203, 0.34);
                box-shadow: 0 12px 28px rgba(11, 106, 203, 0.16);
            }

            .pipeline-lane.focus-proposal {
                border-color: rgba(249, 115, 22, 0.34);
                box-shadow: 0 12px 28px rgba(249, 115, 22, 0.15);
            }

            .pipeline-lane-head {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 10px;
                margin-bottom: 8px;
            }

            .pipeline-lane-title {
                color: #12344b;
                font-size: 0.82rem;
                text-transform: uppercase;
                letter-spacing: 0.1em;
                font-weight: 800;
            }

            .pipeline-count {
                background: rgba(15, 126, 114, 0.12);
                border: 1px solid rgba(15, 126, 114, 0.25);
                color: #10596a;
                border-radius: 999px;
                font-size: 0.74rem;
                font-weight: 800;
                padding: 2px 10px;
            }

            .pipeline-empty {
                color: #688093;
                font-size: 0.84rem;
                border: 1px dashed rgba(16, 58, 82, 0.2);
                border-radius: 10px;
                padding: 10px;
                background: rgba(255,255,255,0.7);
            }

            .mono {
                font-family: 'JetBrains Mono', monospace;
                color: var(--muted);
                font-size: 0.83rem;
            }

            .stButton > button {
                border-radius: 12px !important;
                border: 1px solid rgba(15, 90, 128, 0.22) !important;
                background: linear-gradient(180deg, #ffffff, #f1f8fd) !important;
                color: #143449 !important;
                font-weight: 700 !important;
                letter-spacing: 0.01em !important;
                box-shadow: 0 8px 16px rgba(15, 53, 76, 0.10) !important;
            }

            .stButton > button:hover {
                border-color: rgba(15, 124, 166, 0.45) !important;
                transform: translateY(-1px);
            }

            div[data-baseweb="select"] > div,
            .stTextInput input,
            .stTextArea textarea,
            .stDateInput input,
            .stNumberInput input {
                border-radius: 10px !important;
                border: 1px solid rgba(18, 62, 88, 0.18) !important;
                background: rgba(255, 255, 255, 0.95) !important;
            }

            .stDataFrame, .stDataEditor {
                border: 1px solid rgba(16, 46, 68, 0.10) !important;
                border-radius: 14px !important;
                overflow: hidden;
            }

            .table-shell {
                background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(247,252,255,0.94));
                border: 1px solid rgba(16, 46, 68, 0.11);
                border-radius: 18px;
                padding: 12px 12px 8px;
                box-shadow: 0 14px 26px rgba(13, 35, 49, 0.08);
                margin-bottom: 12px;
            }

            .table-head {
                display: flex;
                justify-content: space-between;
                align-items: baseline;
                gap: 12px;
                margin: 2px 2px 10px;
            }

            .table-title {
                font-size: 0.88rem;
                text-transform: uppercase;
                letter-spacing: 0.12em;
                color: #1f4a67;
                font-weight: 800;
            }

            .table-meta {
                color: #5f7283;
                font-size: 0.82rem;
            }

            .dynamic-table {
                background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(246,251,255,0.95));
                border: 1px solid rgba(16, 46, 68, 0.12);
                border-radius: 18px;
                padding: 10px;
                box-shadow: 0 14px 30px rgba(11, 34, 49, 0.08);
                margin: 8px 0 12px;
                max-width: 100%;
                box-sizing: border-box;
                animation: fadeUp 0.35s ease-out;
            }

            .dynamic-table.compact .dynamic-row {
                padding: 6px;
                gap: 6px;
            }

            .dynamic-table.compact .dynamic-value {
                font-size: 0.79rem;
                line-height: 1.24;
            }

            .dynamic-table.compact .dynamic-row.header .dynamic-value {
                font-size: 0.68rem;
            }

            .dynamic-table.strict-columns {
                overflow-x: auto;
                overflow-y: hidden;
                padding-bottom: 8px;
            }

            .dynamic-grid-table {
                border-collapse: separate;
                border-spacing: 0;
                width: max-content;
                min-width: 100%;
                border: 1px solid rgba(18, 57, 80, 0.14);
                border-radius: 12px;
                overflow: hidden;
            }

            .dynamic-grid-table th,
            .dynamic-grid-table td {
                padding: 10px 12px;
                border-bottom: 1px solid rgba(16, 60, 90, 0.10);
                border-right: 1px solid rgba(16, 60, 90, 0.08);
                text-align: left;
                vertical-align: top;
                white-space: nowrap;
            }

            .dynamic-table.compact .dynamic-grid-table th,
            .dynamic-table.compact .dynamic-grid-table td {
                padding: 7px 9px;
                font-size: 0.78rem;
            }

            .dynamic-grid-table th:last-child,
            .dynamic-grid-table td:last-child {
                border-right: 0;
            }

            .dynamic-grid-table th {
                background: linear-gradient(180deg, #e8f3ff, #deeeff);
                color: #163952;
                font-size: 0.74rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                font-weight: 800;
                position: sticky;
                top: 0;
                z-index: 1;
            }

            .dynamic-grid-table th:first-child,
            .dynamic-grid-table td:first-child {
                position: sticky;
                left: 0;
                z-index: 2;
                background: #edf6ff;
            }

            .dynamic-grid-table th:first-child {
                z-index: 3;
                background: #deeeff;
            }

            .dynamic-grid-table td {
                background: rgba(255,255,255,0.94);
                color: #13354b;
                font-size: 0.85rem;
                line-height: 1.35;
            }

            .dynamic-grid-table tr:hover td {
                background: rgba(238, 248, 255, 0.98);
            }

            .dynamic-head {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 10px;
                margin: 2px 2px 10px;
            }

            .dynamic-title {
                text-transform: uppercase;
                letter-spacing: 0.12em;
                color: #1a4663;
                font-size: 0.76rem;
                font-weight: 800;
            }

            .dynamic-meta {
                color: #5f7283;
                font-size: 0.8rem;
            }

            .dynamic-row {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                gap: 8px;
                border-radius: 12px;
                padding: 8px;
                margin-bottom: 8px;
                border: 1px solid rgba(18, 59, 84, 0.10);
                background: rgba(255,255,255,0.9);
            }

            .dynamic-table.strict-columns .dynamic-row {
                grid-template-columns: repeat(var(--cols), minmax(170px, 1fr));
                min-width: calc(var(--cols) * 170px);
                width: max-content;
            }

            .dynamic-row.header {
                background: linear-gradient(180deg, #e8f3ff, #deeeff);
                border-color: rgba(20, 66, 95, 0.20);
                padding: 7px 8px;
            }

            .dynamic-cell {
                min-width: 0;
                overflow-wrap: anywhere;
            }

            .dynamic-label {
                display: none;
                font-size: 0.7rem;
                text-transform: uppercase;
                letter-spacing: 0.09em;
                color: #618097;
                margin-bottom: 3px;
                font-weight: 700;
            }

            .dynamic-value {
                color: #13354b;
                font-size: 0.86rem;
                line-height: 1.35;
                white-space: normal;
                overflow: visible;
                text-overflow: unset;
                word-break: break-word;
            }

            .dynamic-row.header .dynamic-value {
                color: #163952;
                font-size: 0.75rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                font-weight: 800;
            }

            .dynamic-row:hover {
                border-color: rgba(15, 110, 150, 0.28);
                box-shadow: 0 8px 18px rgba(12, 47, 67, 0.12);
            }

            @media (max-width: 900px) {
                .dynamic-table:not(.strict-columns) .dynamic-row {
                    grid-template-columns: repeat(2, minmax(130px, 1fr));
                }

                .dynamic-table:not(.strict-columns) .dynamic-row.header {
                    display: none;
                }

                .dynamic-table:not(.strict-columns) .dynamic-label {
                    display: block;
                }
            }

            div[data-testid="stDataFrame"] [role="grid"],
            div[data-testid="stDataEditor"] [role="grid"] {
                border-radius: 12px !important;
                border: 1px solid rgba(17, 53, 76, 0.14) !important;
            }

            div[data-testid="stDataFrame"] [role="columnheader"],
            div[data-testid="stDataEditor"] [role="columnheader"] {
                background: linear-gradient(180deg, #eaf5ff, #e0effd) !important;
                color: #163952 !important;
                font-weight: 700 !important;
                border-bottom: 1px solid rgba(16, 62, 92, 0.15) !important;
            }

            div[data-testid="stDataFrame"] [role="gridcell"],
            div[data-testid="stDataEditor"] [role="gridcell"] {
                border-bottom: 1px solid rgba(16, 60, 90, 0.08) !important;
                background: rgba(255,255,255,0.92) !important;
            }

            div[data-testid="stDataEditor"] input {
                background: rgba(255,255,255,0.98) !important;
            }

            .stSidebar {
                background: linear-gradient(180deg, #0f3448 0%, #14526e 42%, #123147 100%);
            }

            .stSidebar * {
                color: #e9fffb !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def render_workspace_hero(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class='workspace-hero'>
            <div class='workspace-kicker'>{html.escape(eyebrow)}</div>
            <h3 class='workspace-title'>{html.escape(title)}</h3>
            <p class='workspace-copy'>{html.escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _fmt_dynamic_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        if pd.isna(value):
            return ""
        if value.is_integer():
            return f"{int(value):,}"
        return f"{value:,.2f}"
    text = str(value).strip()
    parsed = safe_parse_date(text)
    if parsed and (" " in text or "T" in text or len(text) > 10):
        return parsed.isoformat()
    return text


def render_dynamic_table(
    df: pd.DataFrame,
    title: str,
    key: str,
    max_rows: int = 120,
    strict_columns: bool = False,
    enable_compact_toggle: bool = True,
) -> pd.DataFrame:
    if df is None or df.empty:
        st.info("No records available.")
        return df

    working = df.copy().fillna("")
    query = st.text_input(
        f"Search {title}",
        key=f"search_{key}",
        placeholder="Filter across all columns...",
    ).strip()

    if query:
        mask = working.astype(str).apply(lambda col: col.str.contains(query, case=False, na=False))
        working = working[mask.any(axis=1)]

    compact_mode = st.session_state.get(f"compact_{key}", False)
    if enable_compact_toggle:
        compact_mode = st.toggle(
            f"Compact mode for {title}",
            key=f"compact_{key}",
            help="Reduce row height and text sizing for denser table scanning.",
        )

    display_df = working.head(max_rows)
    cols = list(display_df.columns)
    col_count = max(1, len(cols))

    if strict_columns:
        header_html = "".join(
            f"<th>{html.escape(str(col).replace('_', ' ').title())}</th>"
            for col in cols
        )
        body_html = []
        for _, row in display_df.iterrows():
            row_html = "".join(
                f"<td>{html.escape(_fmt_dynamic_value(row.get(col, '')))}</td>"
                for col in cols
            )
            body_html.append(f"<tr>{row_html}</tr>")

        st.markdown(
            f"""
            <div class='dynamic-table strict-columns{' compact' if compact_mode else ''}'>
                <div class='dynamic-head'>
                    <div class='dynamic-title'>{html.escape(title)}</div>
                    <div class='dynamic-meta'>{len(working)} rows{f" | showing {len(display_df)}" if len(working) > len(display_df) else ""}</div>
                </div>
                <table class='dynamic-grid-table'>
                    <thead><tr>{header_html}</tr></thead>
                    <tbody>{''.join(body_html)}</tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return working

    header_cells = "".join(
        f"<div class='dynamic-cell'><div class='dynamic-value'>{html.escape(str(col).replace('_', ' ').title())}</div></div>"
        for col in cols
    )

    body_rows = []
    for _, row in display_df.iterrows():
        row_cells = []
        for col in cols:
            label = html.escape(str(col).replace("_", " ").title())
            value = html.escape(_fmt_dynamic_value(row.get(col, "")))
            row_cells.append(
                f"<div class='dynamic-cell'><div class='dynamic-label'>{label}</div><div class='dynamic-value'>{value}</div></div>"
            )
        body_rows.append(f"<div class='dynamic-row' style='--cols: {col_count};'>{''.join(row_cells)}</div>")

    table_class = "dynamic-table strict-columns" if strict_columns else "dynamic-table"
    if compact_mode:
        table_class += " compact"

    st.markdown(
        f"""
        <div class='{table_class}'>
            <div class='dynamic-head'>
                <div class='dynamic-title'>{html.escape(title)}</div>
                <div class='dynamic-meta'>{len(working)} rows{f" | showing {len(display_df)}" if len(working) > len(display_df) else ""}</div>
            </div>
            <div class='dynamic-row header' style='--cols: {col_count};'>{header_cells}</div>
            {''.join(body_rows)}
        </div>
        """,
        unsafe_allow_html=True,
    )
    return working


def today_iso() -> str:
    return str(date.today())


def load_data() -> dict[str, Any]:
    cloud_data = _load_supabase_data()
    if cloud_data is not None:
        return cloud_data

    local_data = _load_local_data()
    if _is_supabase_enabled():
        _save_supabase_data(local_data)
    return local_data


def ensure_schema(data: dict[str, Any]) -> bool:
    changed = False
    if "customers" not in data:
        data["customers"] = []
        changed = True
    if "prospects" not in data:
        data["prospects"] = []
        changed = True
    if "quotations" not in data:
        data["quotations"] = []
        changed = True
    if "technical_drawings" not in data or not isinstance(data.get("technical_drawings"), list):
        data["technical_drawings"] = []
        changed = True
    if "purchase_orders" not in data or not isinstance(data.get("purchase_orders"), list):
        data["purchase_orders"] = []
        changed = True
    if "tasks" not in data or not isinstance(data.get("tasks"), list):
        data["tasks"] = []
        changed = True
    if "prospect_attachments" not in data or not isinstance(data.get("prospect_attachments"), dict):
        data["prospect_attachments"] = {}
        changed = True
    if "customer_attachments" not in data or not isinstance(data.get("customer_attachments"), dict):
        data["customer_attachments"] = {}
        changed = True
    if "activity_log" not in data or not isinstance(data.get("activity_log"), list):
        data["activity_log"] = []
        changed = True

    cleaned_customers = sanitize_customers(data["customers"])
    if len(cleaned_customers) != len(data["customers"]):
        data["customers"] = cleaned_customers
        changed = True

    for prospect in data["prospects"]:
        normalized_estimated = pd.to_numeric(pd.Series([prospect.get("estimated_value", 0)]), errors="coerce").fillna(0.0).iloc[0]
        if prospect.get("estimated_value") != float(normalized_estimated):
            prospect["estimated_value"] = float(normalized_estimated)
            changed = True

        if "connected_at" not in prospect:
            if prospect.get("status") in CONNECTED_STATUSES:
                prospect["connected_at"] = prospect.get("updated_at", today_iso())[:10]
            else:
                prospect["connected_at"] = ""
            changed = True

    for quote in data["quotations"]:
        normalized_quote = pd.to_numeric(pd.Series([quote.get("quote_value", 0)]), errors="coerce").fillna(0.0).iloc[0]
        if quote.get("quote_value") != float(normalized_quote):
            quote["quote_value"] = float(normalized_quote)
            changed = True
        links = quote.get("linked_drawing_ids", [])
        if isinstance(links, str):
            parsed_links = [x.strip() for x in links.split(",") if x.strip()]
            quote["linked_drawing_ids"] = parsed_links
            changed = True
        elif not isinstance(links, list):
            quote["linked_drawing_ids"] = []
            changed = True

    for po in data["purchase_orders"]:
        normalized_po = pd.to_numeric(pd.Series([po.get("po_value", 0)]), errors="coerce").fillna(0.0).iloc[0]
        if po.get("po_value") != float(normalized_po):
            po["po_value"] = float(normalized_po)
            changed = True

    for drawing in data["technical_drawings"]:
        if "uploaded_at" in drawing:
            drawing["uploaded_at"] = str(drawing.get("uploaded_at", ""))[:10]
        if "linked_quote_ids" not in drawing or not isinstance(drawing.get("linked_quote_ids"), list):
            drawing["linked_quote_ids"] = []
            changed = True

    return changed


def save_data(data: dict[str, Any]) -> None:
    if _save_supabase_data(data):
        return
    _save_local_data(data)


def save_data_and_refresh(data: dict[str, Any]) -> None:
    save_data(data)
    st.rerun()


def next_id(prefix: str, existing_ids: list[str]) -> str:
    nums = []
    for item_id in existing_ids:
        if item_id.startswith(prefix):
            try:
                nums.append(int(item_id.split("-")[-1]))
            except ValueError:
                pass
    new_num = max(nums, default=0) + 1
    return f"{prefix}-{new_num:04d}"


def latest_quote_map(quotations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_prospect: dict[str, dict[str, Any]] = {}
    sorted_quotes = sorted(quotations, key=lambda q: q.get("created_date", ""), reverse=True)
    for quote in sorted_quotes:
        prospect_id = quote.get("prospect_id", "")
        if prospect_id and prospect_id not in by_prospect:
            by_prospect[prospect_id] = quote
    return by_prospect


def safe_parse_date(value: str) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def date_in_range(value: str, start: date, end: date) -> bool:
    parsed = safe_parse_date(value)
    return bool(parsed and start <= parsed <= end)


def csv_bytes(df: pd.DataFrame) -> bytes:
    if df.empty:
        return b""
    return df.to_csv(index=False).encode("utf-8")


def is_blank_customer(customer: dict[str, Any]) -> bool:
    keys = ["company_name", "contact_name", "email", "phone", "industry", "city", "country"]
    return all(str(customer.get(k, "")).strip() == "" for k in keys)


def sanitize_customers(customers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for customer in customers:
        if not isinstance(customer, dict):
            continue
        if is_blank_customer(customer):
            continue
        cleaned.append(customer)
    return cleaned


def normalize_linked_ids(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str):
        return [x.strip() for x in raw.split(",") if x.strip()]
    return []


def _parse_money_value(raw_value: str) -> float | None:
    cleaned = raw_value.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_date_from_text(raw: str) -> date | None:
    cleaned = raw.strip().replace(",", " ")
    patterns = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d %m %Y",
        "%d %b %Y",
        "%d %B %Y",
    ]

    candidate_tokens = re.findall(r"\d{1,4}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}", cleaned)
    for token in candidate_tokens:
        token_clean = " ".join(token.split())
        for fmt in patterns:
            try:
                parsed = datetime.strptime(token_clean, fmt).date()
                return parsed
            except ValueError:
                continue
    return None


def _extract_quote_prefill_from_text(text: str) -> dict[str, Any]:
    lines = [ln.strip() for ln in text.splitlines() if ln and ln.strip()]
    short_lines = [ln for ln in lines if len(ln) <= 110]

    title = ""
    quote_number = ""
    valid_until: date | None = None
    confidence = 0.0
    evidence = ""

    subject_patterns = [
        re.compile(r"(?i)^subject\s*[:\-]\s*(.+)$"),
        re.compile(r"(?i)^quotation\s*(?:for|to|subject)?\s*[:\-]\s*(.+)$"),
    ]

    for ln in short_lines[:20]:
        for pattern in subject_patterns:
            m = pattern.search(ln)
            if m:
                title = m.group(1).strip()
                confidence = 0.95
                evidence = ln
                break
        if title:
            break

    if not title:
        for ln in short_lines[:15]:
            if "quotation" in ln.lower() and len(ln) > 10:
                title = ln
                confidence = 0.65
                evidence = ln
                break

    quote_no_pattern = re.compile(r"(?i)\b(?:quotation|quote)\s*(?:no|number|#|ref(?:erence)?)\s*[:#\-]?\s*([A-Z0-9\-\/]+)")
    for ln in short_lines[:30]:
        m = quote_no_pattern.search(ln)
        if m:
            quote_number = m.group(1).strip()
            confidence = max(confidence, 0.7)
            if not evidence:
                evidence = ln
            break

    valid_until_pattern = re.compile(r"(?i)\b(?:valid\s*until|expiry|expiration|exp\.?\s*date)\s*[:\-]?\s*(.+)$")
    for ln in short_lines[:40]:
        m = valid_until_pattern.search(ln)
        if m:
            parsed_date = _extract_date_from_text(m.group(1))
            if parsed_date:
                valid_until = parsed_date
                confidence = max(confidence, 0.7)
                if not evidence:
                    evidence = ln
                break

    currency = ""
    amount: float | None = None
    amount_score = 0.0

    money_pattern_1 = re.compile(r"\b(AED|USD|EUR|GBP)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)\b", re.IGNORECASE)
    money_pattern_2 = re.compile(r"\b([0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*(AED|USD|EUR|GBP)\b", re.IGNORECASE)
    priority_words = ("total", "grand", "amount", "net", "quotation value", "final")

    for ln in short_lines[:80]:
        line_score = 0.55
        if any(word in ln.lower() for word in priority_words):
            line_score += 0.30

        matches = list(money_pattern_1.finditer(ln))
        if not matches:
            matches = list(money_pattern_2.finditer(ln))

        for match in matches:
            if len(match.groups()) != 2:
                continue
            if match.re is money_pattern_1:
                ccy = match.group(1).upper()
                value_raw = match.group(2)
            else:
                value_raw = match.group(1)
                ccy = match.group(2).upper()

            parsed = _parse_money_value(value_raw)
            if parsed is None:
                continue
            if parsed > 0 and line_score >= amount_score:
                amount = parsed
                currency = ccy
                amount_score = line_score
                evidence = ln if not evidence else evidence

    combined_confidence = max(confidence, amount_score)
    return {
        "title": title,
        "quote_number": quote_number,
        "value": amount,
        "currency": currency or "AED",
        "valid_until": valid_until,
        "confidence": max(0.0, min(1.0, combined_confidence)),
        "evidence": evidence,
        "source": "text",
    }


def _extract_quote_prefill_with_ocr(pdf_bytes: bytes) -> dict[str, Any]:
    try:
        import pypdfium2 as pdfium
        import pytesseract
    except Exception:
        return {"title": "", "quote_number": "", "value": None, "currency": "AED", "valid_until": None, "confidence": 0.0, "evidence": "ocr_unavailable", "source": "ocr"}

    try:
        doc = pdfium.PdfDocument(BytesIO(pdf_bytes))
        if len(doc) == 0:
            return {"title": "", "quote_number": "", "value": None, "currency": "AED", "valid_until": None, "confidence": 0.0, "evidence": "ocr_empty_doc", "source": "ocr"}
        page = doc[0]
        bitmap = page.render(scale=2.0)
        pil_image = bitmap.to_pil()
        ocr_text = pytesseract.image_to_string(pil_image) or ""
        extracted = _extract_quote_prefill_from_text(ocr_text)
        extracted["source"] = "ocr"
        return extracted
    except Exception:
        return {"title": "", "quote_number": "", "value": None, "currency": "AED", "valid_until": None, "confidence": 0.0, "evidence": "ocr_parse_error", "source": "ocr"}


def _extract_quote_prefill_from_pdf_bytes(pdf_bytes: bytes) -> dict[str, Any]:
    try:
        from pypdf import PdfReader
    except Exception:
        return _extract_quote_prefill_with_ocr(pdf_bytes)

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        extracted_parts: list[str] = []
        for page in reader.pages[:2]:
            extracted_parts.append(page.extract_text() or "")
        text = "\n".join(extracted_parts).strip()
        if not text:
            return _extract_quote_prefill_with_ocr(pdf_bytes)

        parsed_text = _extract_quote_prefill_from_text(text)
        if float(parsed_text.get("confidence", 0.0) or 0.0) < 0.45:
            parsed_ocr = _extract_quote_prefill_with_ocr(pdf_bytes)
            if float(parsed_ocr.get("confidence", 0.0) or 0.0) > float(parsed_text.get("confidence", 0.0) or 0.0):
                return parsed_ocr
        return parsed_text
    except Exception:
        return _extract_quote_prefill_with_ocr(pdf_bytes)


def _infer_quote_prefill_from_uploads(uploaded_files: list[Any]) -> dict[str, Any]:
    best = {
        "title": "",
        "quote_number": "",
        "value": None,
        "currency": "AED",
        "valid_until": None,
        "confidence": 0.0,
        "evidence": "",
        "source": "",
        "file_name": "",
    }
    for fobj in uploaded_files:
        parsed = _extract_quote_prefill_from_pdf_bytes(fobj.getvalue())
        if float(parsed.get("confidence", 0.0) or 0.0) > float(best.get("confidence", 0.0) or 0.0):
            parsed["file_name"] = fobj.name
            best = parsed
    return best


def log_activity(
    data: dict[str, Any],
    activity_type: str,
    entity_type: str,
    entity_id: str,
    company_name: str,
    details: str,
    product_name: str = "",
    amount: float = 0.0,
    status: str = "",
) -> None:
    activity_log = data["activity_log"]
    existing_ids = [x.get("activity_id", "") for x in activity_log]
    activity_log.append(
        {
            "activity_id": next_id("ACT", existing_ids),
            "activity_type": activity_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "company_name": company_name,
            "details": details,
            "product_name": product_name,
            "amount": float(amount or 0),
            "status": status,
            "activity_date": today_iso(),
            "created_at": now_stamp(),
        }
    )


def render_attachment_manager(
    data: dict[str, Any],
    items: list[dict[str, Any]],
    key_prefix: str,
    id_field: str,
    name_field: str,
    attachments_key: str,
    entity_type: str,
    track_quote_value: bool = False,
) -> None:
    attachments = data[attachments_key]
    if not items:
        st.info("Create records first to upload quotation PDFs.")
        return

    upload_options = {f"{item[id_field]} | {item[name_field]}": item[id_field] for item in items}
    upload_label = st.selectbox(
        "Select record",
        list(upload_options.keys()),
        key=f"{key_prefix}_upload_prospect_select",
    )
    upload_prospect_id = upload_options[upload_label]

    uploaded_files = st.file_uploader(
        "Upload existing quotation PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        key=f"{key_prefix}_file_uploader",
    )

    quote_title = ""
    quote_value = 0.0
    quote_currency = "AED"
    quote_status = "Sent"
    quote_valid_until = date.today()
    quote_notes = ""

    if track_quote_value:
        title_key = f"{key_prefix}_quote_title"
        number_key = f"{key_prefix}_quote_number"
        value_key = f"{key_prefix}_quote_value"
        currency_key = f"{key_prefix}_quote_currency"
        status_key = f"{key_prefix}_quote_status"
        valid_until_key = f"{key_prefix}_quote_valid_until"
        notes_key = f"{key_prefix}_quote_notes"
        extract_msg_key = f"{key_prefix}_quote_extract_msg"
        extract_fp_key = f"{key_prefix}_quote_extract_fp"
        extract_preview_key = f"{key_prefix}_quote_extract_preview"

        if title_key not in st.session_state:
            st.session_state[title_key] = ""
        if number_key not in st.session_state:
            st.session_state[number_key] = ""
        if value_key not in st.session_state:
            st.session_state[value_key] = 0.0
        if currency_key not in st.session_state:
            st.session_state[currency_key] = "AED"
        if status_key not in st.session_state:
            st.session_state[status_key] = "Sent"
        if valid_until_key not in st.session_state:
            st.session_state[valid_until_key] = date.today()
        if notes_key not in st.session_state:
            st.session_state[notes_key] = ""

        if uploaded_files:
            file_signature = "|".join(f"{fobj.name}:{getattr(fobj, 'size', 0)}" for fobj in uploaded_files)
            extract_fingerprint = f"{upload_prospect_id}:{file_signature}"
            if st.session_state.get(extract_fp_key, "") != extract_fingerprint:
                inferred = _infer_quote_prefill_from_uploads(uploaded_files)
                inferred_title = str(inferred.get("title", "") or "").strip()
                inferred_number = str(inferred.get("quote_number", "") or "").strip()
                inferred_value = inferred.get("value", None)
                inferred_currency = str(inferred.get("currency", "AED") or "AED").upper()
                inferred_valid_until = inferred.get("valid_until", None)
                inferred_conf = float(inferred.get("confidence", 0.0) or 0.0)

                if inferred_title:
                    st.session_state[title_key] = inferred_title
                if inferred_number:
                    st.session_state[number_key] = inferred_number
                if isinstance(inferred_value, (int, float)) and inferred_value > 0:
                    st.session_state[value_key] = float(inferred_value)
                if inferred_currency in ["AED", "USD", "EUR", "GBP"]:
                    st.session_state[currency_key] = inferred_currency
                if isinstance(inferred_valid_until, date):
                    st.session_state[valid_until_key] = inferred_valid_until

                st.session_state[extract_preview_key] = {
                    "file_name": inferred.get("file_name", ""),
                    "source": inferred.get("source", "text"),
                    "confidence": inferred_conf,
                    "evidence": inferred.get("evidence", ""),
                    "title": inferred_title,
                    "quote_number": inferred_number,
                    "value": inferred_value,
                    "currency": inferred_currency,
                    "valid_until": inferred_valid_until,
                }

                if inferred_conf >= 0.8:
                    st.session_state[extract_msg_key] = "Auto-filled from quotation PDF with high confidence."
                elif inferred_conf >= 0.5:
                    st.session_state[extract_msg_key] = "Auto-filled from quotation PDF. Please verify before saving."
                else:
                    st.session_state[extract_msg_key] = "Could not confidently read quotation details. Please fill manually."

                st.session_state[extract_fp_key] = extract_fingerprint

        st.markdown("##### Quotation Details")
        extract_msg = st.session_state.get(extract_msg_key, "")
        if extract_msg:
            st.caption(extract_msg)

        preview = st.session_state.get(extract_preview_key, {})
        if preview:
            preview_source = "OCR fallback" if preview.get("source") == "ocr" else "PDF text"
            preview_conf = float(preview.get("confidence", 0.0) or 0.0) * 100
            preview_title = preview.get("title", "") or "Not found"
            preview_num = preview.get("quote_number", "") or "Not found"
            preview_value = preview.get("value", None)
            preview_currency = preview.get("currency", "AED")
            preview_date = preview.get("valid_until", None)
            preview_evidence = preview.get("evidence", "") or "No evidence line available"
            amount_line = f"{preview_currency} {float(preview_value):,.0f}" if isinstance(preview_value, (int, float)) else "Not found"
            date_line = str(preview_date) if isinstance(preview_date, date) else "Not found"
            st.markdown(
                f"""
                <div class='report-note'>
                    <strong>Auto Extraction Preview</strong><br/>
                    File: {preview.get('file_name', 'N/A')} | Source: {preview_source} | Confidence: {preview_conf:.0f}%<br/>
                    Subject: {preview_title}<br/>
                    Quotation Number: {preview_num}<br/>
                    Amount: {amount_line} | Valid Until: {date_line}<br/>
                    Evidence: {preview_evidence}
                </div>
                """,
                unsafe_allow_html=True,
            )

        q1, q2 = st.columns(2)
        quote_title = q1.text_input(
            "Quotation Title",
            placeholder="Enter quotation title",
            key=title_key,
        )
        quote_value = q2.number_input(
            "Quotation Value (AED)",
            min_value=0.0,
            step=1000.0,
            key=value_key,
        )

        q3, q4, q7 = st.columns(3)
        quote_currency = q3.selectbox(
            "Currency",
            ["AED", "USD", "EUR", "GBP"],
            key=currency_key,
        )
        quote_status = q4.selectbox(
            "Quotation Status",
            QUOTE_STATUSES,
            key=status_key,
        )
        quote_number = q7.text_input(
            "Quotation Number",
            placeholder="QTN-2026-001",
            key=number_key,
        )

        q5, q6 = st.columns(2)
        quote_valid_until = q5.date_input(
            "Valid Until",
            key=valid_until_key,
        )
        quote_notes = q6.text_input(
            "Notes",
            key=notes_key,
        )

    if st.button("Save Uploaded PDF Files", width="stretch", key=f"{key_prefix}_save_upload_btn"):
        if not uploaded_files:
            st.warning("Please choose one or more PDF files first.")
        else:
            files_for_prospect = attachments.setdefault(upload_prospect_id, [])
            current_ids = [f.get("file_id", "") for f in files_for_prospect]
            new_file_ids: list[str] = []
            for fobj in uploaded_files:
                new_file = {
                    "file_id": next_id("ATT", current_ids),
                    "file_name": fobj.name,
                    "mime_type": fobj.type or "application/pdf",
                    "uploaded_at": now_stamp(),
                    "content_b64": base64.b64encode(fobj.getvalue()).decode("ascii"),
                }
                files_for_prospect.append(new_file)
                current_ids.append(new_file["file_id"])
                new_file_ids.append(new_file["file_id"])
                entity_id, entity_name = upload_label.split(" | ", 1)
                log_activity(
                    data,
                    activity_type="Quotation PDF Uploaded",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    company_name=entity_name,
                    details=f"Uploaded file {fobj.name}",
                )

            if track_quote_value:
                entity_id, entity_name = upload_label.split(" | ", 1)
                new_quote = {
                    "id": next_id("Q", [q.get("id", "") for q in data["quotations"]]),
                    "prospect_id": upload_prospect_id if entity_type == "prospect" else "",
                    "customer_id": upload_prospect_id if entity_type == "customer" else "",
                    "customer_name": entity_name,
                    "source_entity_type": entity_type,
                    "source_entity_id": upload_prospect_id,
                    "product_name": quote_title or f"Uploaded quotation for {entity_name}",
                    "quote_number": quote_number,
                    "quote_value": float(quote_value or 0),
                    "currency": quote_currency,
                    "status": quote_status,
                    "created_date": today_iso(),
                    "valid_until": str(quote_valid_until),
                    "notes": quote_notes,
                    "extraction_source": st.session_state.get(extract_preview_key, {}).get("source", ""),
                    "extraction_confidence": float(st.session_state.get(extract_preview_key, {}).get("confidence", 0.0) or 0.0),
                    "extraction_evidence": st.session_state.get(extract_preview_key, {}).get("evidence", ""),
                    "attachment_count": len(uploaded_files),
                }
                data["quotations"].append(new_quote)

                # Link each newly uploaded file to the quotation record created in this upload action.
                for fmeta in files_for_prospect:
                    if fmeta.get("file_id") in new_file_ids:
                        fmeta["linked_quotation_id"] = new_quote["id"]

                log_activity(
                    data,
                    activity_type="Proposal Shared",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    company_name=entity_name,
                    details=f"Uploaded quotation file(s) recorded for AED {float(quote_value or 0):,.0f}",
                    product_name=new_quote["product_name"],
                    amount=float(quote_value or 0),
                    status=quote_status,
                )

            save_data_and_refresh(data)
            if track_quote_value:
                st.success(
                    f"Uploaded {len(uploaded_files)} PDF file(s) for {upload_label} and recorded AED {float(quote_value or 0):,.0f} as quotation value."
                )
            else:
                st.success(f"Uploaded {len(uploaded_files)} PDF file(s) for {upload_label}.")

    files = attachments.get(upload_prospect_id, [])
    if files:
        st.write("Uploaded quotation files")
        for idx, fobj in enumerate(files):
            file_bytes = base64.b64decode(fobj.get("content_b64", ""))
            d1, d2 = st.columns([4, 1])
            with d1:
                st.download_button(
                    label=f"Download {fobj.get('file_name', 'file')}",
                    data=file_bytes,
                    file_name=fobj.get("file_name", "quotation_file.pdf"),
                    mime=fobj.get("mime_type", "application/pdf"),
                    key=f"{key_prefix}_download_{upload_prospect_id}_{idx}",
                    width="stretch",
                )
            with d2:
                if st.button(
                    "Delete",
                    key=f"{key_prefix}_delete_{upload_prospect_id}_{idx}",
                    width="stretch",
                ):
                    files.pop(idx)
                    if not files:
                        attachments.pop(upload_prospect_id, None)
                    entity_id, entity_name = upload_label.split(" | ", 1)
                    log_activity(
                        data,
                        activity_type="Quotation PDF Deleted",
                        entity_type=entity_type,
                        entity_id=entity_id,
                        company_name=entity_name,
                        details=f"Deleted file {fobj.get('file_name', 'quotation_file.pdf')}",
                    )
                    save_data_and_refresh(data)
    else:
        st.caption("No quotation PDFs uploaded for this prospect yet.")


def dashboard(data: dict[str, list[dict[str, Any]]]) -> None:
    customers = sanitize_customers(data["customers"])
    prospects = data["prospects"]
    quotations = data["quotations"]
    purchase_orders = data.get("purchase_orders", [])
    activities = data.get("activity_log", [])

    total_pipeline = sum(float(p.get("estimated_value", 0) or 0) for p in prospects if p.get("status") != "Lost")
    won_value = sum(float(p.get("estimated_value", 0) or 0) for p in prospects if p.get("status") == "Won")
    po_total = sum(float(po.get("po_value", 0) or 0) for po in purchase_orders)
    open_leads = sum(1 for p in prospects if p.get("status") not in {"Won", "Lost"})
    conversion = (sum(1 for p in prospects if p.get("status") == "Won") / len(prospects) * 100) if prospects else 0
    connected = sum(1 for p in prospects if p.get("status") in CONNECTED_STATUSES)
    latest_activity = sorted(activities, key=lambda item: item.get("created_at", ""), reverse=True)[:3]
    top_status_df = (
        pd.DataFrame(prospects)["status"].value_counts().reindex(STATUSES, fill_value=0)
        if prospects
        else pd.Series([0] * len(STATUSES), index=STATUSES)
    )
    top_prospect = None
    if prospects:
        top_prospect = max(prospects, key=lambda p: float(p.get("estimated_value", 0) or 0))
    latest_quote = None
    if quotations:
        latest_quote = sorted(quotations, key=lambda q: q.get("created_date", ""), reverse=True)[0]

    st.markdown(
        """
        <div class='hero'>
            <div class='hero-eyebrow'>Sales command center</div>
            <h2 class='hero-title'>Metalys Enclosures Manufacturing</h2>
            <div class='hero-subtitle'>A premium CRM workspace for tracking customers, prospect movement, quotation value, and sales activity without losing sight of the next action.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class='dashboard-grid'>
            <div class='stat-card'>
                <div class='stat-label'>Customers</div>
                <div class='stat-value'>{len(customers)}</div>
                <div class='stat-footnote'>Active accounts in the system</div>
            </div>
            <div class='stat-card'>
                <div class='stat-label'>Prospects</div>
                <div class='stat-value'>{len(prospects)}</div>
                <div class='stat-footnote'>{connected} connected, {open_leads} open leads</div>
            </div>
            <div class='stat-card'>
                <div class='stat-label'>Open Pipeline</div>
                <div class='stat-value'>AED {total_pipeline:,.0f}</div>
                <div class='stat-footnote'>Estimated value still in motion</div>
            </div>
            <div class='stat-card'>
                <div class='stat-label'>Won Value</div>
                <div class='stat-value'>AED {won_value:,.0f}</div>
                <div class='stat-footnote'>Closed business captured so far</div>
            </div>
            <div class='stat-card'>
                <div class='stat-label'>Win Rate</div>
                <div class='stat-value'>{conversion:.1f}%</div>
                <div class='stat-footnote'>{len(quotations)} quotations issued</div>
            </div>
            <div class='stat-card'>
                <div class='stat-label'>Purchase Orders</div>
                <div class='stat-value'>{len(purchase_orders)}</div>
                <div class='stat-footnote'>AED {po_total:,.0f} confirmed value</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### At a Glance")
    glance_left, glance_mid, glance_right = st.columns(3)
    with glance_left:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("#### Pipeline Health")
        st.markdown(
            f"<div class='status-strip'><div class='status-pill'><span class='label'>Open</span><span class='value'>{open_leads}</span></div><div class='status-pill'><span class='label'>Connected</span><span class='value'>{connected}</span></div><div class='status-pill'><span class='label'>Customers</span><span class='value'>{len(customers)}</span></div></div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.caption("Use this view to spot where attention is needed first.")
        st.markdown("</div>", unsafe_allow_html=True)
    with glance_mid:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("#### Largest Active Opportunity")
        if top_prospect:
            company_name = html.escape(str(top_prospect.get("company_name", "")).strip())
            st.markdown(f"<div><strong>{company_name}</strong></div>", unsafe_allow_html=True)
            st.caption(f"{top_prospect.get('product_interest', 'No product')} | AED {float(top_prospect.get('estimated_value', 0) or 0):,.0f}")
            st.caption(f"Stage: {top_prospect.get('status', 'Unknown')} | Next action: {top_prospect.get('next_action', 'Not set') or 'Not set'}")
        else:
            st.markdown("<div class='empty-state'>Add a prospect to surface the highest-value opportunity here.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with glance_right:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("#### Latest Quotation")
        if latest_quote:
            customer_name = html.escape(str(latest_quote.get("customer_name", "")).strip())
            st.markdown(f"<div><strong>{customer_name}</strong></div>", unsafe_allow_html=True)
            st.caption(f"{latest_quote.get('product_name', '')} | {latest_quote.get('currency', 'AED')} {float(latest_quote.get('quote_value', 0) or 0):,.0f}")
            st.caption(f"Status: {latest_quote.get('status', 'Draft')} | Valid until: {latest_quote.get('valid_until', 'Not set')}")
        else:
            st.markdown("<div class='empty-state'>No quotations yet. Create one to make the dashboard more useful.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    left, right = st.columns([1.25, 1])

    with left:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.subheader("Pipeline by Status")
        chart_df = pd.DataFrame({"status": top_status_df.index, "count": top_status_df.values})
        chart_max = max(int(top_status_df.max()) if len(top_status_df) else 0, 1)
        chart = (
            alt.Chart(chart_df)
            .mark_bar(cornerRadiusTopLeft=10, cornerRadiusTopRight=10, size=36)
            .encode(
                x=alt.X("status:N", sort=STATUSES, title=None, axis=alt.Axis(labelAngle=0, labelFontSize=11)),
                y=alt.Y("count:Q", title=None, scale=alt.Scale(domain=[0, chart_max])),
                color=alt.Color(
                    "status:N",
                    sort=STATUSES,
                    scale=alt.Scale(range=["#0ea5a4", "#38bdf8", "#22c55e", "#f97316", "#eab308", "#14b8a6", "#64748b"]),
                    legend=None,
                ),
                tooltip=[alt.Tooltip("status:N", title="Status"), alt.Tooltip("count:Q", title="Leads")],
            )
            .properties(height=240)
        )
        text = (
            alt.Chart(chart_df)
            .mark_text(dy=-10, fontSize=12, fontWeight=700, color="#13202a")
            .encode(x="status:N", y="count:Q", text="count:Q")
        )
        st.markdown("<div class='chart-shell'>", unsafe_allow_html=True)
        st.altair_chart(chart + text, use_container_width=True)
        st.markdown("<div class='status-strip'>" + "".join(
            f"<div class='status-pill'><span class='label'>{status}</span><span class='value'>{int(top_status_df.get(status, 0))}</span></div>"
            for status in STATUSES
        ) + "</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.subheader("Recent Activity")
        if latest_activity:
            for item in latest_activity:
                st.markdown(
                    f"""
                    <div class='timeline-item'>
                        <strong>{item.get('activity_type', 'Activity')}</strong><br/>
                        <div class='timeline-meta'>{item.get('details', '')} · {item.get('activity_date', '')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown("<div class='empty-state'>No activity yet. Customer edits, prospect updates, and quotation creation will show up here.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### Upcoming Actions")
    action_df = pd.DataFrame(prospects)
    if not action_df.empty:
        action_df = action_df[action_df["status"].isin(["Contacted", "Qualified", "Proposal Sent", "Negotiation"])]
        action_df = action_df[["company_name", "contact_name", "status", "next_action", "expected_close_date"]]
        render_dynamic_table(action_df, "Upcoming Actions", key="dashboard_upcoming_actions", max_rows=30)
    else:
        st.markdown("<div class='empty-state'>Add prospects to surface follow-ups, proposals, and close dates here.</div>", unsafe_allow_html=True)

    st.markdown("### Recent Purchase Orders")
    if purchase_orders:
        po_df = pd.DataFrame(purchase_orders)
        if "po_value" in po_df.columns:
            po_df["po_value"] = pd.to_numeric(po_df["po_value"], errors="coerce").fillna(0.0)
        show_cols = [c for c in ["id", "po_number", "company_name", "po_value", "currency", "po_date", "status"] if c in po_df.columns]
        if "po_date" in po_df.columns:
            po_df = po_df.sort_values("po_date", ascending=False)
        render_dynamic_table(po_df.head(8)[show_cols], "Recent Purchase Orders", key="dashboard_recent_pos", max_rows=8)
    else:
        st.markdown("<div class='empty-state'>No purchase orders uploaded yet. Add one from the Purchase Orders workspace.</div>", unsafe_allow_html=True)


def customers_view(data: dict[str, list[dict[str, Any]]]) -> None:
    render_workspace_hero(
        "Workspace",
        "Customer Directory",
        "Manage strategic accounts, clean customer records, and keep account intelligence decision-ready.",
    )
    customers = sanitize_customers(data["customers"])
    if len(customers) != len(data["customers"]):
        data["customers"] = customers
        save_data_and_refresh(data)

    if customers:
        customer_df = pd.DataFrame(customers)
        render_dynamic_table(customer_df, "Customer Ledger", key="customers_ledger", max_rows=80)
        with st.expander("Edit Customer Records", expanded=False):
            edited = st.data_editor(customer_df, width="stretch", hide_index=True, num_rows="dynamic")
            if st.button("Save Customer Edits", width="stretch"):
                data["customers"] = sanitize_customers(edited.fillna("").to_dict("records"))
                save_data_and_refresh(data)

        st.markdown("### Delete Customer")
        delete_options = {f"{c.get('id', '')} | {c.get('company_name', '')}": c for c in customers}
        selected_label = st.selectbox("Select customer to delete", list(delete_options.keys()))
        selected_customer = delete_options[selected_label]
        if st.button("Delete Selected Customer", width="stretch"):
            customer_id = selected_customer.get("id", "")
            company_name = selected_customer.get("company_name", "")
            data["customers"] = [c for c in data["customers"] if c.get("id") != customer_id]
            data.get("customer_attachments", {}).pop(customer_id, None)
            log_activity(
                data,
                activity_type="Customer Deleted",
                entity_type="customer",
                entity_id=customer_id,
                company_name=company_name,
                details="Customer record deleted",
            )
            save_data_and_refresh(data)
    else:
        st.info("No customers yet. Add your first account below.")

    with st.expander("Add New Customer", expanded=False):
        with st.form("new_customer_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            company = c1.text_input("Company Name*")
            contact = c2.text_input("Primary Contact*")
            owner = c3.text_input("Account Owner", value="Adithya")

            d1, d2, d3 = st.columns(3)
            email = d1.text_input("Email")
            phone = d2.text_input("Phone")
            industry = d3.text_input("Industry")

            e1, e2, e3 = st.columns(3)
            city = e1.text_input("City")
            country = e2.text_input("Country")
            lifecycle = e3.selectbox("Lifecycle Stage", ["Active", "Onboarding", "Dormant"])

            annual_revenue = st.number_input("Annual Revenue (AED)", min_value=0.0, step=1000.0)
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Create Customer", width="stretch")

            if submitted:
                if not company or not contact:
                    st.error("Company name and primary contact are required.")
                else:
                    new_customer = {
                        "id": next_id("CUST", [c["id"] for c in customers]),
                        "company_name": company,
                        "contact_name": contact,
                        "email": email,
                        "phone": phone,
                        "industry": industry,
                        "city": city,
                        "country": country,
                        "account_owner": owner,
                        "lifecycle_stage": lifecycle,
                        "annual_revenue": annual_revenue,
                        "last_contact": str(date.today()),
                        "notes": notes,
                    }
                    data["customers"].append(new_customer)
                    log_activity(
                        data,
                        activity_type="Customer Added",
                        entity_type="customer",
                        entity_id=new_customer["id"],
                        company_name=company,
                        details="New customer account created",
                    )
                    save_data_and_refresh(data)

    st.markdown("### Upload Customer Quotation PDFs")
    st.caption("Attach quotation PDFs directly to customer accounts.")
    render_attachment_manager(
        data,
        customers,
        key_prefix="customers",
        id_field="id",
        name_field="company_name",
        attachments_key="customer_attachments",
        entity_type="customer",
        track_quote_value=True,
    )


def prospects_view(data: dict[str, list[dict[str, Any]]]) -> None:
    render_workspace_hero(
        "Workspace",
        "Prospect Tracker",
        "Track every lead with stage clarity, opportunity value, quotation context, and next-action discipline.",
    )
    prospects = data["prospects"]
    quotes_by_prospect = latest_quote_map(data["quotations"])

    if prospects:
        rows = []
        for prospect in prospects:
            row = dict(prospect)
            q = quotes_by_prospect.get(prospect["id"])
            row["quote_generated"] = "Yes" if q else "No"
            row["quote_product_name"] = q.get("product_name", "") if q else ""
            row["quote_value"] = float(q.get("quote_value", 0) or 0) if q else 0.0
            row["quotation_files"] = len(data["prospect_attachments"].get(prospect["id"], []))
            rows.append(row)

        p_df = pd.DataFrame(rows)
        p_df = p_df.drop(columns=["customer_id"], errors="ignore")
        if "created_at" in p_df.columns:
            p_df["created_date"] = p_df["created_at"].astype(str).str[:10]
            p_df = p_df.drop(columns=["created_at"], errors="ignore")

        # Order columns by business priority; keep created_date as the very last column.
        primary_cols = [
            "id",
            "company_name",
            "contact_name",
            "phone",
            "email",
            "source",
            "status",
            "next_action",
            "notes",
        ]
        secondary_cols = [
            "estimated_value",
            "expected_close_date",
            "quote_generated",
            "quote_product_name",
            "quote_value",
            "quotation_files",
            "industry",
            "product_interest",
            "connected_at",
            "updated_at",
        ]
        ordered_cols = [c for c in primary_cols if c in p_df.columns]
        ordered_cols.extend(c for c in secondary_cols if c in p_df.columns and c not in ordered_cols)
        ordered_cols.extend(c for c in p_df.columns if c not in ordered_cols)
        ordered_cols = [c for c in ordered_cols if c != "created_date"]
        if "created_date" in p_df.columns:
            ordered_cols.append("created_date")
        p_df = p_df[ordered_cols]

        st.markdown("### Saved Views")
        quick_view = st.selectbox(
            "Quick lead view",
            [
                "All Leads",
                "My Hot Leads",
                "Quotes Sent This Week",
                "Won This Month",
            ],
            key="prospects_quick_view",
        )
        status_filter = st.multiselect("Filter by Status", STATUSES, default=[])
        min_estimated = st.number_input("Minimum Estimated Value", min_value=0.0, step=1000.0, value=0.0)
        only_without_quotes = st.toggle("Only leads without quotations", value=False)

        filtered_df = p_df.copy()
        today = date.today()
        week_start = today - timedelta(days=7)
        month_start = today.replace(day=1)

        if quick_view == "My Hot Leads":
            hot_statuses = {"Qualified", "Proposal Sent", "Negotiation"}
            filtered_df = filtered_df[filtered_df["status"].isin(hot_statuses)]
            if "next_action" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["next_action"].astype(str).str.strip() != ""]
        elif quick_view == "Quotes Sent This Week":
            if "quote_generated" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["quote_generated"] == "Yes"]
            if "updated_at" in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df["updated_at"].apply(
                        lambda x: bool((parsed := safe_parse_date(str(x))) and parsed >= week_start)
                    )
                ]
        elif quick_view == "Won This Month":
            filtered_df = filtered_df[filtered_df["status"] == "Won"]
            if "updated_at" in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df["updated_at"].apply(
                        lambda x: bool((parsed := safe_parse_date(str(x))) and parsed >= month_start)
                    )
                ]

        if status_filter:
            filtered_df = filtered_df[filtered_df["status"].isin(status_filter)]
        if "estimated_value" in filtered_df.columns and min_estimated > 0:
            filtered_df = filtered_df[pd.to_numeric(filtered_df["estimated_value"], errors="coerce").fillna(0.0) >= float(min_estimated)]
        if only_without_quotes and "quote_generated" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["quote_generated"] != "Yes"]

        render_dynamic_table(
            filtered_df,
            "Live Opportunity Register",
            key="prospects_register",
            max_rows=max(1, len(filtered_df)),
            strict_columns=True,
        )
    else:
        st.info("No prospects yet. Add leads and opportunities below.")

    st.markdown("### Edit Prospect")
    if prospects:
        lead_options = {f"{p['id']} | {p['company_name']}": p for p in prospects}
        selected_label = st.selectbox(
            "Select a prospect to edit",
            ["Select prospect..."] + list(lead_options.keys()),
        )
        selected = lead_options.get(selected_label)

        if selected:
            with st.form(f"edit_prospect_{selected['id']}"):
                p1, p2, p3 = st.columns(3)
                company = p1.text_input("Company Name*", value=selected.get("company_name", ""))
                contact = p2.text_input("Contact Name*", value=selected.get("contact_name", ""))
                current_status = selected.get("status", "New Lead")
                status_index = STATUSES.index(current_status) if current_status in STATUSES else 0
                status = p3.selectbox("Status", STATUSES, index=status_index)

                q1, q2, q3 = st.columns(3)
                email = q1.text_input("Email", value=selected.get("email", ""))
                phone = q2.text_input("Phone", value=selected.get("phone", ""))
                source = q3.text_input("Lead Source", value=selected.get("source", ""))

                r1, r2, r3 = st.columns(3)
                industry = r1.text_input("Industry", value=selected.get("industry", ""))
                product_interest = r2.text_input("Product Interest", value=selected.get("product_interest", ""))
                est_value = r3.number_input(
                    "Estimated Value (AED)",
                    min_value=0.0,
                    step=1000.0,
                    value=float(selected.get("estimated_value", 0) or 0),
                )

                close_default = safe_parse_date(selected.get("expected_close_date", "")) or date.today()
                s1, s2 = st.columns(2)
                expected_close = s1.date_input("Expected Close Date", value=close_default)
                next_action = s2.text_input("Next Action", value=selected.get("next_action", ""))
                notes = st.text_area("Notes", value=selected.get("notes", ""))

                submitted_edit = st.form_submit_button("Save Prospect Changes", width="stretch")
                if submitted_edit:
                    if not company or not contact:
                        st.error("Company name and contact are required.")
                    else:
                        for prospect in data["prospects"]:
                            if prospect["id"] == selected["id"]:
                                prospect["company_name"] = company
                                prospect["contact_name"] = contact
                                prospect["status"] = status
                                prospect["email"] = email
                                prospect["phone"] = phone
                                prospect["source"] = source
                                prospect["industry"] = industry
                                prospect["product_interest"] = product_interest
                                prospect["estimated_value"] = est_value
                                prospect["expected_close_date"] = str(expected_close)
                                prospect["next_action"] = next_action
                                prospect["notes"] = notes
                                prospect["updated_at"] = now_stamp()
                                if status in CONNECTED_STATUSES and not prospect.get("connected_at"):
                                    prospect["connected_at"] = today_iso()
                                break
                        log_activity(
                            data,
                            activity_type="Prospect Updated",
                            entity_type="prospect",
                            entity_id=selected["id"],
                            company_name=company,
                            details=f"Stage updated to {status}; next action: {next_action or 'Not set'}",
                        )
                        save_data_and_refresh(data)
        else:
            st.info("Select a prospect from the dropdown to open the edit form.")

    with st.expander("Add New Prospect", expanded=False):
        with st.form("new_prospect_form", clear_on_submit=True):
            p1, p2, p3 = st.columns(3)
            company = p1.text_input("Company Name*")
            contact = p2.text_input("Contact Name*")
            status = p3.selectbox("Status", STATUSES)

            q1, q2, q3 = st.columns(3)
            email = q1.text_input("Email")
            phone = q2.text_input("Phone")
            source = q3.text_input("Lead Source")

            r1, r2, r3 = st.columns(3)
            industry = r1.text_input("Industry")
            product_interest = r2.text_input("Product Interest")
            est_value = r3.number_input("Estimated Value (AED)", min_value=0.0, step=1000.0)

            s1, s2 = st.columns(2)
            expected_close = s1.date_input("Expected Close Date", value=date.today())
            next_action = s2.text_input("Next Action")

            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Create Prospect", width="stretch")

            if submitted:
                if not company or not contact:
                    st.error("Company name and contact are required.")
                else:
                    new_prospect = {
                        "id": next_id("LEAD", [p["id"] for p in prospects]),
                        "customer_id": "",
                        "company_name": company,
                        "contact_name": contact,
                        "email": email,
                        "phone": phone,
                        "source": source,
                        "industry": industry,
                        "product_interest": product_interest,
                        "estimated_value": est_value,
                        "status": status,
                        "expected_close_date": str(expected_close),
                        "next_action": next_action,
                        "notes": notes,
                        "created_at": now_stamp(),
                        "updated_at": now_stamp(),
                        "connected_at": today_iso() if status in CONNECTED_STATUSES else "",
                    }
                    data["prospects"].append(new_prospect)
                    log_activity(
                        data,
                        activity_type="Prospect Added",
                        entity_type="prospect",
                        entity_id=new_prospect["id"],
                        company_name=company,
                        details=f"New prospect created at stage {status}",
                    )
                    save_data_and_refresh(data)


def quotations_view(data: dict[str, list[dict[str, Any]]]) -> None:
    render_workspace_hero(
        "Workspace",
        "Quotations",
        "Control pricing output, quotation lifecycle, and supporting files from a single premium command surface.",
    )
    quotes = data["quotations"]
    prospects = data["prospects"]
    drawings = data.get("technical_drawings", [])
    lead_map = {p.get("id", ""): p for p in prospects}
    attachments = data.get("prospect_attachments", {})

    total_quote_value = sum(float(q.get("quote_value", 0) or 0) for q in quotes)
    total_uploaded_files = sum(len(v) for v in attachments.values())
    k1, k2, k3 = st.columns(3)
    k1.metric("Quotation Records", len(quotes))
    k2.metric("Total Quotation Value", f"AED {total_quote_value:,.0f}")
    k3.metric("Uploaded Quotation PDFs", total_uploaded_files)

    records_tab, upload_tab, files_tab = st.tabs(["Quotation Records", "Upload by Lead", "Uploaded Files Library"])

    with records_tab:
        if quotes:
            q_df = pd.DataFrame(quotes)
            if "quote_value" in q_df.columns:
                q_df["quote_value"] = pd.to_numeric(q_df["quote_value"], errors="coerce").fillna(0.0)
            if "linked_drawing_ids" in q_df.columns:
                q_df["linked_drawing_ids"] = q_df["linked_drawing_ids"].apply(
                    lambda x: ", ".join(normalize_linked_ids(x))
                )
            q_df_view = q_df.drop(columns=["customer_id"], errors="ignore")
            render_dynamic_table(
                q_df_view,
                "Quotation Register",
                key="quotations_register",
                max_rows=90,
                strict_columns=True,
            )
            with st.expander("Edit Quotation Records", expanded=False):
                edited_quotes = st.data_editor(q_df_view, width="stretch", hide_index=True, num_rows="dynamic")
                if st.button("Save Quotation Edits", width="stretch"):
                    if "quote_value" in edited_quotes.columns:
                        edited_quotes["quote_value"] = pd.to_numeric(edited_quotes["quote_value"], errors="coerce").fillna(0.0)
                    edited_records = edited_quotes.fillna("").to_dict("records")
                    existing_customer_ids = {q.get("id", ""): q.get("customer_id", "") for q in data["quotations"]}
                    for row in edited_records:
                        row["customer_id"] = existing_customer_ids.get(row.get("id", ""), "")
                        row["linked_drawing_ids"] = normalize_linked_ids(row.get("linked_drawing_ids", []))
                    data["quotations"] = edited_records
                    save_data_and_refresh(data)
        else:
            st.info("No quotations created yet.")

        with st.expander("Generate New Quotation", expanded=False):
            with st.form("new_quote_form", clear_on_submit=True):
                lead_options = {f"{p['id']} | {p['company_name']} ({p['status']})": p for p in prospects}
                selected_label = st.selectbox("Prospect", list(lead_options.keys()) if lead_options else ["No prospects available"])
                selected_lead = lead_options.get(selected_label)
                drawings_for_lead = [d for d in drawings if d.get("prospect_id") == selected_lead.get("id", "")] if selected_lead else []

                c1, c2, c3 = st.columns(3)
                product = c1.text_input("Product Name*")
                value = c2.number_input("Quotation Value", min_value=0.0, step=1000.0)
                currency = c3.selectbox("Currency", ["AED", "USD", "EUR", "GBP"])

                d1, d2 = st.columns(2)
                quote_status = d1.selectbox("Quote Status", QUOTE_STATUSES)
                valid_until = d2.date_input("Valid Until", value=date.today())

                drawing_labels = {
                    f"{d.get('id', '')} | {d.get('drawing_title', '') or d.get('file_name', '')} | {d.get('revision', 'r0')}": d.get("id", "")
                    for d in drawings_for_lead
                }
                selected_drawing_labels = st.multiselect(
                    "Link Technical Drawing IDs",
                    list(drawing_labels.keys()),
                    help="Attach one or more mapped technical drawings for this quotation.",
                )
                selected_drawing_ids = [drawing_labels[label] for label in selected_drawing_labels]

                notes = st.text_area("Commercial Notes")
                submitted = st.form_submit_button("Create Quotation", width="stretch")

                if submitted:
                    if not selected_lead:
                        st.error("Please create a prospect first.")
                    elif not product:
                        st.error("Product name is required.")
                    else:
                        new_quote = {
                            "id": next_id("Q", [q["id"] for q in quotes]),
                            "prospect_id": selected_lead["id"],
                            "customer_name": selected_lead["company_name"],
                            "product_name": product,
                            "quote_value": value,
                            "currency": currency,
                            "status": quote_status,
                            "created_date": str(date.today()),
                            "valid_until": str(valid_until),
                            "notes": notes,
                            "linked_drawing_ids": selected_drawing_ids,
                        }
                        data["quotations"].append(new_quote)

                        for drawing in data.get("technical_drawings", []):
                            if drawing.get("id") in selected_drawing_ids:
                                linked_quote_ids = normalize_linked_ids(drawing.get("linked_quote_ids", []))
                                if new_quote["id"] not in linked_quote_ids:
                                    linked_quote_ids.append(new_quote["id"])
                                drawing["linked_quote_ids"] = linked_quote_ids

                        for p in data["prospects"]:
                            if p["id"] == selected_lead["id"] and p["status"] in {"New Lead", "Contacted", "Qualified"}:
                                p["status"] = "Proposal Sent"
                                p["updated_at"] = now_stamp()
                                if not p.get("connected_at"):
                                    p["connected_at"] = today_iso()

                        log_activity(
                            data,
                            activity_type="Proposal Shared",
                            entity_type="prospect",
                            entity_id=selected_lead["id"],
                            company_name=selected_lead["company_name"],
                            details=f"Quotation created for {product} | Drawings linked: {len(selected_drawing_ids)}",
                            product_name=product,
                            amount=float(value or 0),
                            status=quote_status,
                        )

                        save_data_and_refresh(data)


def technical_drawings_view(data: dict[str, Any]) -> None:
    render_workspace_hero(
        "Workspace",
        "Technical Drawings",
        "Map SLDs and technical files to prospects with unique IDs so quotation references stay traceable at scale.",
    )

    prospects = data.get("prospects", [])
    drawings = data.get("technical_drawings", [])

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Drawings", len(drawings))
    c2.metric("Mapped Prospects", len({d.get('prospect_id', '') for d in drawings if d.get('prospect_id', '')}))
    c3.metric("Drawings Linked to Quotes", sum(1 for d in drawings if normalize_linked_ids(d.get("linked_quote_ids", []))))

    if not prospects:
        st.info("Create prospects first to map technical drawings.")
        return

    with st.expander("Upload and Map Drawings", expanded=True):
        lead_options = {f"{p['id']} | {p['company_name']}": p for p in prospects}
        selected_label = st.selectbox("Map to Prospect", list(lead_options.keys()), key="drawings_prospect_select")
        selected_prospect = lead_options[selected_label]

        a1, a2, a3 = st.columns(3)
        drawing_title = a1.text_input("Drawing Title", placeholder="Main SLD - Basement Feeder")
        drawing_type = a2.selectbox("Drawing Type", ["SLD", "Technical Drawing", "GA", "BOQ", "Other"])
        revision = a3.text_input("Revision", value="r0")

        notes = st.text_area("Notes", placeholder="Scope, assumptions, latest updates...")
        uploaded_drawings = st.file_uploader(
            "Upload Drawing Files",
            type=["pdf", "dwg", "dxf", "png", "jpg", "jpeg", "svg"],
            accept_multiple_files=True,
            key="drawing_uploader",
        )

        if st.button("Save Drawings", width="stretch"):
            if not uploaded_drawings:
                st.warning("Please upload at least one file.")
            else:
                existing_ids = [d.get("id", "") for d in drawings]
                for file_obj in uploaded_drawings:
                    drawing_id = next_id("DRW", existing_ids)
                    existing_ids.append(drawing_id)
                    drawings.append(
                        {
                            "id": drawing_id,
                            "prospect_id": selected_prospect["id"],
                            "company_name": selected_prospect.get("company_name", ""),
                            "contact_name": selected_prospect.get("contact_name", ""),
                            "drawing_title": drawing_title or file_obj.name,
                            "drawing_type": drawing_type,
                            "revision": revision,
                            "file_name": file_obj.name,
                            "mime_type": file_obj.type or "application/octet-stream",
                            "size_kb": round((getattr(file_obj, "size", 0) or 0) / 1024, 1),
                            "uploaded_at": today_iso(),
                            "notes": notes,
                            "content_b64": base64.b64encode(file_obj.getvalue()).decode("ascii"),
                            "linked_quote_ids": [],
                        }
                    )
                    log_activity(
                        data,
                        activity_type="Technical Drawing Uploaded",
                        entity_type="prospect",
                        entity_id=selected_prospect["id"],
                        company_name=selected_prospect.get("company_name", ""),
                        details=f"{drawing_id} uploaded ({file_obj.name})",
                        status=drawing_type,
                    )
                save_data_and_refresh(data)

    if not drawings:
        st.info("No technical drawings uploaded yet.")
        return

    d_df = pd.DataFrame(drawings)
    show_cols = [
        c
        for c in [
            "id",
            "company_name",
            "prospect_id",
            "drawing_title",
            "drawing_type",
            "revision",
            "file_name",
            "uploaded_at",
            "linked_quote_ids",
            "notes",
        ]
        if c in d_df.columns
    ]
    if "linked_quote_ids" in d_df.columns:
        d_df["linked_quote_ids"] = d_df["linked_quote_ids"].apply(lambda x: ", ".join(normalize_linked_ids(x)))

    render_dynamic_table(
        d_df[show_cols],
        "Technical Drawings Register",
        key="technical_drawings_register",
        max_rows=max(1, len(d_df)),
        strict_columns=True,
    )

    draw_options = {
        f"{d.get('id', '')} | {d.get('company_name', '')} | {d.get('file_name', '')}": d.get("id", "")
        for d in drawings
    }
    selected_label = st.selectbox("Select technical drawing", list(draw_options.keys()), key="drawing_file_pick")
    selected_id = draw_options[selected_label]
    selected_item = next((d for d in drawings if d.get("id") == selected_id), None)

    if selected_item:
        b1, b2 = st.columns(2)
        with b1:
            st.download_button(
                label=f"Download {selected_item.get('file_name', 'drawing_file')}",
                data=base64.b64decode(selected_item.get("content_b64", "")),
                file_name=selected_item.get("file_name", "drawing_file"),
                mime=selected_item.get("mime_type", "application/octet-stream"),
                width="stretch",
                key=f"drawing_dl_{selected_item.get('id', '')}",
            )
        with b2:
            if st.button("Delete Selected Drawing", width="stretch", key=f"drawing_del_{selected_item.get('id', '')}"):
                drawing_id = selected_item.get("id", "")
                data["technical_drawings"] = [d for d in drawings if d.get("id") != drawing_id]
                for quote in data.get("quotations", []):
                    quote["linked_drawing_ids"] = [x for x in normalize_linked_ids(quote.get("linked_drawing_ids", [])) if x != drawing_id]
                log_activity(
                    data,
                    activity_type="Technical Drawing Deleted",
                    entity_type="prospect",
                    entity_id=selected_item.get("prospect_id", ""),
                    company_name=selected_item.get("company_name", ""),
                    details=f"Deleted drawing {drawing_id}",
                )
                save_data_and_refresh(data)

def purchase_orders_view(data: dict[str, Any]) -> None:
    render_workspace_hero(
        "Workspace",
        "Purchase Orders",
        "Capture confirmed business, reconcile PO status, and maintain auditable order documentation.",
    )
    prospects = data.get("prospects", [])
    purchase_orders = data.get("purchase_orders", [])

    if purchase_orders:
        po_df = pd.DataFrame(purchase_orders)
        if "po_value" in po_df.columns:
            po_df["po_value"] = pd.to_numeric(po_df["po_value"], errors="coerce").fillna(0.0)
        show_cols = [
            c
            for c in ["id", "po_number", "prospect_id", "company_name", "po_value", "currency", "po_date", "status", "file_name"]
            if c in po_df.columns
        ]
        render_dynamic_table(po_df[show_cols], "PO Register", key="po_register", max_rows=100)
    else:
        st.info("No purchase orders yet. Upload the first PO below.")

    with st.expander("Upload Purchase Order", expanded=True):
        lead_options = {f"{p['id']} | {p['company_name']}": p for p in prospects}
        if not lead_options:
            st.warning("Create a prospect first so a purchase order can be mapped to a lead.")
        else:
            with st.form("new_po_form", clear_on_submit=True):
                selected_label = st.selectbox("Map to Prospect Lead", list(lead_options.keys()))
                selected_lead = lead_options[selected_label]

                p1, p2, p3 = st.columns(3)
                po_number = p1.text_input("PO Number*")
                po_value = p2.number_input("PO Value", min_value=0.0, step=1000.0)
                currency = p3.selectbox("Currency", ["AED", "USD", "EUR", "GBP"])

                p4, p5 = st.columns(2)
                po_date = p4.date_input("PO Date", value=date.today())
                po_status = p5.selectbox("PO Status", ["Received", "Under Review", "Approved", "Fulfilled", "Cancelled"])

                notes = st.text_area("PO Notes")
                uploaded_po = st.file_uploader("Upload Purchase Order File", type=["pdf"], key="po_file_upload")
                submitted = st.form_submit_button("Save Purchase Order", width="stretch")

                if submitted:
                    if not po_number:
                        st.error("PO number is required.")
                    elif uploaded_po is None:
                        st.error("Please upload a PO PDF file.")
                    else:
                        new_po = {
                            "id": next_id("PO", [po.get("id", "") for po in purchase_orders]),
                            "prospect_id": selected_lead["id"],
                            "company_name": selected_lead["company_name"],
                            "po_number": po_number,
                            "po_value": float(po_value or 0),
                            "currency": currency,
                            "po_date": str(po_date),
                            "status": po_status,
                            "notes": notes,
                            "file_name": uploaded_po.name,
                            "mime_type": uploaded_po.type or "application/pdf",
                            "content_b64": base64.b64encode(uploaded_po.getvalue()).decode("ascii"),
                            "uploaded_at": now_stamp(),
                        }
                        purchase_orders.append(new_po)
                        log_activity(
                            data,
                            activity_type="Purchase Order Received",
                            entity_type="prospect",
                            entity_id=selected_lead["id"],
                            company_name=selected_lead["company_name"],
                            details=f"PO {po_number} uploaded",
                            amount=float(po_value or 0),
                            status=po_status,
                        )
                        save_data_and_refresh(data)

    if purchase_orders:
        st.markdown("### PO Files")
        po_options = {f"{po.get('id', '')} | {po.get('po_number', '')} | {po.get('company_name', '')}": po for po in purchase_orders}
        selected_po_label = st.selectbox("Select Purchase Order", list(po_options.keys()))
        selected_po = po_options[selected_po_label]
        if selected_po.get("content_b64"):
            st.download_button(
                label=f"Download {selected_po.get('file_name', 'purchase_order.pdf')}",
                data=base64.b64decode(selected_po.get("content_b64", "")),
                file_name=selected_po.get("file_name", "purchase_order.pdf"),
                mime=selected_po.get("mime_type", "application/pdf"),
                width="stretch",
            )

        if st.button("Delete Selected Purchase Order", width="stretch"):
            po_id = selected_po.get("id", "")
            data["purchase_orders"] = [po for po in purchase_orders if po.get("id") != po_id]
            log_activity(
                data,
                activity_type="Purchase Order Deleted",
                entity_type="prospect",
                entity_id=selected_po.get("prospect_id", ""),
                company_name=selected_po.get("company_name", ""),
                details=f"Deleted PO {selected_po.get('po_number', '')}",
                amount=float(selected_po.get("po_value", 0) or 0),
                status=selected_po.get("status", ""),
            )
            save_data_and_refresh(data)


def pipeline_view(data: dict[str, list[dict[str, Any]]]) -> None:
    render_workspace_hero(
        "Workspace",
        "Dynamic Sales Pipeline",
        "Move opportunities between stages in real time while preserving quote, product, and value context.",
    )

    prospects = data["prospects"]
    quotes_map = latest_quote_map(data["quotations"])

    if not prospects:
        st.info("No prospects yet.")
        return

    quick_col1, quick_col2 = st.columns([2, 1])
    with quick_col1:
        lead_lookup = {f"{p['id']} | {p['company_name']}": p for p in prospects}
        selected_lead_label = st.selectbox("Quick Stage Update", list(lead_lookup.keys()))
        selected_lead = lead_lookup[selected_lead_label]
    with quick_col2:
        new_stage = st.selectbox("New Stage", STATUSES, index=STATUSES.index(selected_lead["status"]))

    if st.button("Update Stage", width="stretch"):
        for p in data["prospects"]:
            if p["id"] == selected_lead["id"]:
                p["status"] = new_stage
                p["updated_at"] = now_stamp()
                if new_stage in CONNECTED_STATUSES and not p.get("connected_at"):
                    p["connected_at"] = today_iso()
                log_activity(
                    data,
                    activity_type="Stage Updated",
                    entity_type="prospect",
                    entity_id=p["id"],
                    company_name=p["company_name"],
                    details=f"Pipeline moved to {new_stage}",
                    status=new_stage,
                )
                break
        save_data_and_refresh(data)

    status_items_map = {status: [p for p in prospects if p.get("status") == status] for status in STATUSES}
    stage_badge_map = {
        "Qualified": "badge-qualified",
        "Proposal Sent": "badge-proposal",
        "Negotiation": "badge-negotiation",
    }

    def heat_class_for_value(value: float) -> str:
        if value >= 300000:
            return "heat-hot"
        if value >= 120000:
            return "heat-warm"
        return "heat-cool"
    st.markdown(
        "<div class='status-strip'>" + "".join(
            f"<div class='status-pill'><span class='label'>{html.escape(status)}</span><span class='value'>{len(status_items_map.get(status, []))}</span></div>"
            for status in STATUSES
        ) + "</div>",
        unsafe_allow_html=True,
    )

    def render_lane(status: str, focus_class: str = "") -> None:
        items = status_items_map.get(status, [])
        lane_class = f"pipeline-lane {focus_class}".strip()
        st.markdown(
            f"""
            <div class='{lane_class}'>
                <div class='pipeline-lane-head'>
                    <div class='pipeline-lane-title'>{html.escape(status)}</div>
                    <div class='pipeline-count'>{len(items)} leads</div>
                </div>
            """,
            unsafe_allow_html=True,
        )
        if not items:
            st.markdown("<div class='pipeline-empty'>No opportunities in this stage.</div>", unsafe_allow_html=True)
        for lead in items:
            quote = quotes_map.get(lead["id"])
            quote_line = (
                f"Quote: {quote.get('currency', 'AED')} {float(quote.get('quote_value', 0) or 0):,.0f} | {quote.get('product_name', '')}"
                if quote
                else "Quote: Not generated"
            )
            company = html.escape(str(lead.get("company_name", "")))
            contact = html.escape(str(lead.get("contact_name", "")))
            lead_id = html.escape(str(lead.get("id", "")))
            est_value = float(lead.get("estimated_value", 0) or 0)
            product = html.escape(str(lead.get("product_interest", "")))
            next_action = html.escape(str(lead.get("next_action", "Not set") or "Not set"))
            quote_line_safe = html.escape(quote_line)
            heat_class = heat_class_for_value(est_value)
            badge_class = stage_badge_map.get(status, "")
            badge_html = f"<div class='pipeline-badge {badge_class}'>{html.escape(status)}</div>" if badge_class else ""
            st.markdown(
                f"""
                <div class='pipeline-card {heat_class}'>
                    {badge_html}
                    <div class='pipeline-title'>{company}</div>
                    <div>{contact}</div>
                    <div class='mono'>{lead_id} | Est. AED {est_value:,.0f}</div>
                    <div class='mono'>{quote_line_safe}</div>
                    <div class='mono'>Product: {product}</div>
                    <div class='mono'>Next: {next_action}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### Conversion Focus")
    focus_left, focus_right = st.columns(2)
    with focus_left:
        render_lane("Qualified", "focus-qualified")
    with focus_right:
        render_lane("Proposal Sent", "focus-proposal")

    st.markdown("### Full Pipeline")
    remaining_statuses = [s for s in STATUSES if s not in {"Qualified", "Proposal Sent"}]
    row_size = 3
    for i in range(0, len(remaining_statuses), row_size):
        row_statuses = remaining_statuses[i : i + row_size]
        row_cols = st.columns(len(row_statuses))
        for col, status in zip(row_cols, row_statuses):
            with col:
                render_lane(status)


def global_search_view(data: dict[str, Any]) -> None:
    render_workspace_hero(
        "Workspace",
        "Global Search",
        "AI lead generation workspace to discover and qualify global companies, then add them directly to prospects.",
    )

    st.markdown("### AI Global Lead Generation")
    st.caption("Discover new companies from the web by niche and country, optionally qualify with GPT, then add selected ones directly to Prospects.")

    g1, g2, g3 = st.columns(3)
    niche = g1.text_input("Target Product / Niche", value="LV panel builders")
    country = g2.text_input("Country", value="Kuwait")
    max_results = int(g3.number_input("Max Leads", min_value=5, max_value=30, value=12, step=1))
    use_gpt = st.toggle("Use GPT qualification (requires OPENAI_API_KEY secret)", value=True)

    if st.button("Find Global Leads", width="stretch"):
        if not niche.strip() or not country.strip():
            st.error("Please enter both niche and country.")
        else:
            with st.spinner("Discovering and qualifying leads..."):
                candidates = _discover_web_leads(niche.strip(), country.strip(), max_results=max_results)
                if use_gpt:
                    candidates = _enrich_leads_with_gpt(candidates, niche.strip(), country.strip())
                for item in candidates:
                    item["select"] = True
                st.session_state["ai_lead_candidates"] = candidates

    ai_candidates = st.session_state.get("ai_lead_candidates", [])
    if ai_candidates:
        candidate_df = pd.DataFrame(ai_candidates)
        preferred_cols = [
            c
            for c in ["select", "company_name", "country", "website", "reason_fit", "contact_hint", "confidence", "source"]
            if c in candidate_df.columns
        ]
        edited_df = st.data_editor(
            candidate_df[preferred_cols],
            width="stretch",
            hide_index=True,
            num_rows="dynamic",
            key="ai_lead_editor",
        )

        if st.button("Add Selected Leads to Prospects", width="stretch"):
            selected_rows = edited_df[edited_df.get("select", False) == True] if "select" in edited_df.columns else edited_df
            existing_names = {str(p.get("company_name", "")).strip().lower() for p in data.get("prospects", [])}
            existing_ids = [p.get("id", "") for p in data.get("prospects", [])]

            added = 0
            skipped = 0
            for _, row in selected_rows.iterrows():
                company_name = str(row.get("company_name", "")).strip()
                if not company_name:
                    skipped += 1
                    continue
                if company_name.lower() in existing_names:
                    skipped += 1
                    continue

                website = str(row.get("website", "")).strip()
                reason_fit = str(row.get("reason_fit", "")).strip()
                contact_hint = str(row.get("contact_hint", "")).strip()
                source = str(row.get("source", "AI Lead Discovery")).strip()
                new_id = next_id("LEAD", existing_ids)
                existing_ids.append(new_id)

                new_prospect = {
                    "id": new_id,
                    "customer_id": "",
                    "company_name": company_name,
                    "contact_name": "",
                    "email": "",
                    "phone": "",
                    "source": source,
                    "industry": "",
                    "product_interest": niche.strip(),
                    "estimated_value": 0.0,
                    "status": "New Lead",
                    "expected_close_date": str(date.today() + timedelta(days=45)),
                    "next_action": "Initial outreach and qualification",
                    "notes": f"Website: {website} | Reason: {reason_fit} | Contact hint: {contact_hint}",
                    "created_at": now_stamp(),
                    "updated_at": now_stamp(),
                    "connected_at": "",
                }
                data["prospects"].append(new_prospect)
                existing_names.add(company_name.lower())
                added += 1

                log_activity(
                    data,
                    activity_type="Prospect Added",
                    entity_type="prospect",
                    entity_id=new_id,
                    company_name=company_name,
                    details=f"AI lead generation: {country.strip()} | {niche.strip()}",
                    status="New Lead",
                )

            if added > 0:
                save_data_and_refresh(data)
            else:
                st.warning(f"No new leads added. Skipped {skipped} duplicate/invalid rows.")


def lead_360_view(data: dict[str, Any]) -> None:
    render_workspace_hero(
        "Workspace",
        "Lead 360",
        "Get one complete company timeline with activities, quotations, drawings, purchase orders, and shared files.",
    )

    prospects = data.get("prospects", [])
    if not prospects:
        st.info("No prospects available yet.")
        return

    lead_options = {f"{p.get('id', '')} | {p.get('company_name', '')}": p for p in prospects}
    selected_label = st.selectbox("Select Lead", list(lead_options.keys()), key="lead_360_select")
    lead = lead_options[selected_label]
    lead_id = lead.get("id", "")
    lead_name = lead.get("company_name", "")

    quotes = [q for q in data.get("quotations", []) if q.get("prospect_id", "") == lead_id]
    drawings = [d for d in data.get("technical_drawings", []) if d.get("prospect_id", "") == lead_id]
    purchase_orders = [po for po in data.get("purchase_orders", []) if po.get("prospect_id", "") == lead_id]
    activities = [a for a in data.get("activity_log", []) if a.get("entity_id", "") == lead_id]
    uploaded_files = data.get("prospect_attachments", {}).get(lead_id, [])

    total_quote_value = sum(float(q.get("quote_value", 0) or 0) for q in quotes)
    total_po_value = sum(float(po.get("po_value", 0) or 0) for po in purchase_orders)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Lead Status", str(lead.get("status", "")))
    m2.metric("Quotations", len(quotes))
    m3.metric("Quoted Value", f"AED {total_quote_value:,.0f}")
    m4.metric("PO Value", f"AED {total_po_value:,.0f}")

    timeline_rows: list[dict[str, str]] = []

    def add_timeline(event_date: str, source: str, event: str, details: str, status: str = "", amount: float = 0.0) -> None:
        timeline_rows.append(
            {
                "date": str(event_date or ""),
                "source": source,
                "event": event,
                "details": details,
                "status": status,
                "amount": f"AED {float(amount or 0):,.0f}" if float(amount or 0) > 0 else "",
            }
        )

    add_timeline(str(lead.get("created_at", "")), "Prospect", "Lead Created", f"{lead_name} added to CRM", str(lead.get("status", "")))
    if lead.get("connected_at", ""):
        add_timeline(str(lead.get("connected_at", "")), "Prospect", "Lead Connected", "Moved into connected pipeline", str(lead.get("status", "")))
    add_timeline(str(lead.get("updated_at", "")), "Prospect", "Latest Lead Update", str(lead.get("next_action", "")) or "Lead details updated", str(lead.get("status", "")))

    for quote in quotes:
        add_timeline(
            str(quote.get("created_date", "")),
            "Quotation",
            str(quote.get("id", "")) or "Quotation Created",
            str(quote.get("product_name", "")) or "Quotation shared",
            str(quote.get("status", "")),
            float(quote.get("quote_value", 0) or 0),
        )

    for drawing in drawings:
        add_timeline(
            str(drawing.get("uploaded_at", "")),
            "Technical Drawing",
            str(drawing.get("id", "")) or "Drawing Uploaded",
            str(drawing.get("drawing_title", "")) or str(drawing.get("file_name", "")),
            str(drawing.get("drawing_type", "")),
        )

    for po in purchase_orders:
        add_timeline(
            str(po.get("po_date", "")),
            "Purchase Order",
            str(po.get("po_number", "")) or str(po.get("id", "")),
            str(po.get("notes", "")) or "Purchase order recorded",
            str(po.get("status", "")),
            float(po.get("po_value", 0) or 0),
        )

    for file_item in uploaded_files:
        add_timeline(
            str(file_item.get("uploaded_at", "")),
            "Quotation File",
            str(file_item.get("file_name", "")) or "File Uploaded",
            f"Linked quotation: {file_item.get('linked_quotation_id', 'Unlinked')}",
            "Uploaded",
        )

    for activity in activities:
        add_timeline(
            str(activity.get("activity_date", "")),
            "Activity",
            str(activity.get("activity_type", "")) or "Activity",
            str(activity.get("details", "")),
            str(activity.get("status", "")),
            float(activity.get("amount", 0) or 0),
        )

    timeline_df = pd.DataFrame(timeline_rows)
    if timeline_df.empty:
        st.info("No timeline events captured for this lead yet.")
    else:
        timeline_df["_sort_date"] = timeline_df["date"].apply(lambda x: safe_parse_date(str(x)) or date.min)
        timeline_df = timeline_df.sort_values("_sort_date", ascending=False).drop(columns=["_sort_date"])
        render_dynamic_table(
            timeline_df,
            f"Lead 360 Timeline | {lead_name}",
            key="lead_360_timeline",
            max_rows=max(1, len(timeline_df)),
            strict_columns=True,
        )

    st.markdown("### Linked Records")
    rec1, rec2 = st.columns(2)
    with rec1:
        quotes_df = pd.DataFrame(quotes)
        if quotes_df.empty:
            st.caption("No quotations linked to this lead.")
        else:
            show_cols = [c for c in ["id", "product_name", "quote_value", "status", "created_date"] if c in quotes_df.columns]
            render_dynamic_table(
                quotes_df[show_cols],
                "Lead Quotations",
                key="lead_360_quotes",
                max_rows=max(1, len(quotes_df)),
                strict_columns=True,
            )
    with rec2:
        drawings_df = pd.DataFrame(drawings)
        if drawings_df.empty:
            st.caption("No technical drawings linked to this lead.")
        else:
            show_cols = [c for c in ["id", "drawing_title", "drawing_type", "revision", "uploaded_at"] if c in drawings_df.columns]
            render_dynamic_table(
                drawings_df[show_cols],
                "Lead Drawings",
                key="lead_360_drawings",
                max_rows=max(1, len(drawings_df)),
                strict_columns=True,
            )


def followups_view(data: dict[str, Any]) -> None:
    render_workspace_hero(
        "Workspace",
        "Follow-ups",
        "Track next actions with due dates, owners, and priorities so no lead goes cold.",
    )

    tasks = data.get("tasks", [])
    prospects = data.get("prospects", [])

    today = date.today()
    overdue_count = sum(
        1
        for t in tasks
        if str(t.get("status", "Open")) != "Done"
        and (due := safe_parse_date(str(t.get("due_date", ""))))
        and due < today
    )
    open_count = sum(1 for t in tasks if str(t.get("status", "Open")) != "Done")

    m1, m2, m3 = st.columns(3)
    m1.metric("Open Follow-ups", open_count)
    m2.metric("Overdue", overdue_count)
    m3.metric("Completed", sum(1 for t in tasks if str(t.get("status", "Open")) == "Done"))

    if tasks:
        t_df = pd.DataFrame(tasks)
        if "due_date" in t_df.columns:
            t_df["_due_sort"] = t_df["due_date"].apply(lambda x: safe_parse_date(str(x)) or date.max)
            t_df = t_df.sort_values(["status", "_due_sort", "priority"], ascending=[True, True, True]).drop(columns=["_due_sort"])
        render_dynamic_table(
            t_df,
            "Follow-up Register",
            key="followup_register",
            max_rows=max(1, len(t_df)),
            strict_columns=True,
        )
    else:
        st.info("No follow-ups yet. Add your first action below.")

    with st.expander("Add Follow-up", expanded=False):
        lead_options = {f"{p.get('id', '')} | {p.get('company_name', '')}": p for p in prospects}
        with st.form("new_followup_form", clear_on_submit=True):
            lead_label = st.selectbox("Related Lead (optional)", ["General"] + list(lead_options.keys()))
            f1, f2, f3 = st.columns(3)
            owner = f1.text_input("Owner", placeholder="Sales owner")
            due_date = f2.date_input("Due Date", value=today)
            priority = f3.selectbox("Priority", ["High", "Medium", "Low"], index=1)
            title = st.text_input("Follow-up Title*", placeholder="Call procurement for technical clarifications")
            notes = st.text_area("Notes")
            status = st.selectbox("Status", ["Open", "In Progress", "Done"], index=0)
            submitted = st.form_submit_button("Create Follow-up", width="stretch")

            if submitted:
                if not title.strip():
                    st.error("Follow-up title is required.")
                else:
                    selected_lead = lead_options.get(lead_label)
                    new_task = {
                        "id": next_id("TASK", [t.get("id", "") for t in tasks]),
                        "prospect_id": selected_lead.get("id", "") if selected_lead else "",
                        "company_name": selected_lead.get("company_name", "") if selected_lead else "",
                        "title": title.strip(),
                        "owner": owner.strip(),
                        "due_date": str(due_date),
                        "priority": priority,
                        "status": status,
                        "notes": notes.strip(),
                        "created_at": now_stamp(),
                        "updated_at": now_stamp(),
                    }
                    tasks.append(new_task)
                    log_activity(
                        data,
                        activity_type="Follow-up Created",
                        entity_type="prospect" if selected_lead else "task",
                        entity_id=new_task.get("prospect_id", "") if selected_lead else new_task["id"],
                        company_name=new_task.get("company_name", ""),
                        details=f"{new_task['title']} (due {new_task['due_date']})",
                        status=new_task["status"],
                    )
                    save_data_and_refresh(data)

    if tasks:
        st.markdown("### Update Follow-up Status")
        options = {f"{t.get('id', '')} | {t.get('title', '')}": t for t in tasks}
        selected_key = st.selectbox("Select follow-up", list(options.keys()))
        selected_task = options[selected_key]

        c1, c2 = st.columns(2)
        new_status = c1.selectbox("New Status", ["Open", "In Progress", "Done"], index=["Open", "In Progress", "Done"].index(str(selected_task.get("status", "Open")) if str(selected_task.get("status", "Open")) in ["Open", "In Progress", "Done"] else "Open"))
        new_due = c2.date_input("New Due Date", value=safe_parse_date(str(selected_task.get("due_date", ""))) or today)
        if st.button("Save Follow-up Update", width="stretch"):
            for task in data.get("tasks", []):
                if task.get("id", "") == selected_task.get("id", ""):
                    task["status"] = new_status
                    task["due_date"] = str(new_due)
                    task["updated_at"] = now_stamp()
                    log_activity(
                        data,
                        activity_type="Follow-up Updated",
                        entity_type="prospect" if task.get("prospect_id", "") else "task",
                        entity_id=task.get("prospect_id", "") or task.get("id", ""),
                        company_name=task.get("company_name", ""),
                        details=f"{task.get('title', '')} moved to {new_status}",
                        status=new_status,
                    )
                    break
            save_data_and_refresh(data)


def _discover_web_leads(niche: str, country: str, max_results: int = 15) -> list[dict[str, str]]:
    search_query = f"{niche} in {country}"
    url = f"https://duckduckgo.com/html/?q={quote_plus(search_query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
    }
    req = Request(url, headers=headers)

    try:
        with urlopen(req, timeout=20) as resp:
            page = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return []

    links = re.findall(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, flags=re.IGNORECASE | re.DOTALL)
    snippets = re.findall(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', page, flags=re.IGNORECASE | re.DOTALL)

    results: list[dict[str, str]] = []
    for idx, (href, raw_title) in enumerate(links[:max_results]):
        cleaned_title = re.sub(r"<.*?>", "", raw_title)
        cleaned_title = html.unescape(cleaned_title).strip()
        website = href.strip()
        domain = urlparse(website).netloc.replace("www.", "") if website else ""
        snippet = ""
        if idx < len(snippets):
            snippet = html.unescape(re.sub(r"<.*?>", "", snippets[idx])).strip()

        company_name = cleaned_title.split("|")[0].split("-")[0].strip() or domain or "Potential Lead"
        results.append(
            {
                "company_name": company_name,
                "website": website,
                "country": country,
                "reason_fit": snippet or f"Matches query: {search_query}",
                "contact_hint": "",
                "source": f"AI Lead Discovery ({search_query})",
            }
        )
    return results


def _enrich_leads_with_gpt(raw_leads: list[dict[str, str]], niche: str, country: str) -> list[dict[str, str]]:
    api_key = _get_secret_or_env("OPENAI_API_KEY")
    model = _get_secret_or_env("OPENAI_MODEL", "gpt-4o-mini") or "gpt-4o-mini"
    if not api_key or not raw_leads:
        return raw_leads

    compact_input = [
        {
            "company_name": x.get("company_name", ""),
            "website": x.get("website", ""),
            "reason_fit": x.get("reason_fit", ""),
        }
        for x in raw_leads[:20]
    ]

    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a B2B lead qualification analyst. Return strict JSON with a single key 'leads'. "
                    "Each item must include: company_name, website, country, reason_fit, contact_hint, confidence_score (0-100)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Target niche: {niche}. Country: {country}. "
                    "From these web candidates, keep only relevant companies and improve quality. Candidates: "
                    + json.dumps(compact_input)
                ),
            },
        ],
    }

    req = Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=35) as resp:
            response_data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        parsed = json.loads(content)
        leads = parsed.get("leads", [])
        normalized: list[dict[str, str]] = []
        for lead in leads:
            normalized.append(
                {
                    "company_name": str(lead.get("company_name", "")).strip(),
                    "website": str(lead.get("website", "")).strip(),
                    "country": str(lead.get("country", country)).strip() or country,
                    "reason_fit": str(lead.get("reason_fit", "")).strip(),
                    "contact_hint": str(lead.get("contact_hint", "")).strip(),
                    "source": f"GPT Qualified ({niche} | {country})",
                    "confidence": str(lead.get("confidence_score", "")),
                }
            )
        return [x for x in normalized if x.get("company_name", "")]
    except Exception:
        return raw_leads


def insights_view(data: dict[str, list[dict[str, Any]]]) -> None:
    render_workspace_hero(
        "Workspace",
        "Revenue and Product Insights",
        "Monitor performance momentum through executive analytics and product-level value concentration.",
    )
    prospects = pd.DataFrame(data["prospects"])
    quotes = pd.DataFrame(data["quotations"])

    if not prospects.empty and "estimated_value" in prospects.columns:
        prospects["estimated_value"] = pd.to_numeric(prospects["estimated_value"], errors="coerce").fillna(0.0)
    if not quotes.empty and "quote_value" in quotes.columns:
        quotes["quote_value"] = pd.to_numeric(quotes["quote_value"], errors="coerce").fillna(0.0)

    total_pipeline = float(prospects["estimated_value"].sum()) if not prospects.empty and "estimated_value" in prospects.columns else 0.0
    total_quoted = float(quotes["quote_value"].sum()) if not quotes.empty and "quote_value" in quotes.columns else 0.0
    avg_quote = float(quotes["quote_value"].mean()) if not quotes.empty and "quote_value" in quotes.columns else 0.0
    active_leads = int(prospects[prospects["status"].isin(CONNECTED_STATUSES)].shape[0]) if not prospects.empty and "status" in prospects.columns else 0

    st.markdown(
        """
        <div class='report-hero'>
            <h3>Commercial Intelligence Snapshot</h3>
            <p>Premium analytics view of where value is building, which product lines are strongest, and how quotation momentum is moving by stage.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Pipeline Value", f"AED {total_pipeline:,.0f}")
    k2.metric("Quotation Value", f"AED {total_quoted:,.0f}")
    k3.metric("Average Quote", f"AED {avg_quote:,.0f}")
    k4.metric("Active Leads", active_leads)

    left, right = st.columns(2)

    with left:
        st.markdown("#### Pipeline by Product Interest")
        if prospects.empty:
            st.info("Prospects required for insights.")
        else:
            product_df = prospects.copy()
            product_df["product_interest"] = product_df.get("product_interest", "").replace("", "Unspecified").fillna("Unspecified")
            product_value = (
                product_df.groupby("product_interest", dropna=False)["estimated_value"]
                .sum()
                .sort_values(ascending=False)
                .head(8)
                .reset_index(name="value")
            )
            max_product = max(float(product_value["value"].max()) if not product_value.empty else 0.0, 1.0)
            product_chart = (
                alt.Chart(product_value)
                .mark_bar(cornerRadiusTopRight=8, cornerRadiusBottomRight=8, size=20)
                .encode(
                    y=alt.Y("product_interest:N", sort="-x", title=None, axis=alt.Axis(labelLimit=200)),
                    x=alt.X("value:Q", title="AED", scale=alt.Scale(domain=[0, max_product])),
                    color=alt.Color(
                        "value:Q",
                        scale=alt.Scale(domain=[0, max_product], range=["#bae6fd", "#0ea5a4"]),
                        legend=None,
                    ),
                    tooltip=[
                        alt.Tooltip("product_interest:N", title="Product"),
                        alt.Tooltip("value:Q", title="Pipeline Value", format=",.0f"),
                    ],
                )
                .properties(height=280)
            )
            product_labels = (
                alt.Chart(product_value)
                .mark_text(align="left", dx=6, color="#13202a", fontWeight=700)
                .encode(y=alt.Y("product_interest:N", sort="-x"), x="value:Q", text=alt.Text("value:Q", format=",.0f"))
            )
            st.altair_chart(product_chart + product_labels, use_container_width=True)

    with right:
        st.markdown("#### Quotation Value by Status")
        if quotes.empty:
            st.info("Quotations required for quote insights.")
        else:
            quote_df = quotes.copy()
            quote_df["status"] = quote_df.get("status", "Draft").fillna("Draft")
            quote_status = (
                quote_df.groupby("status", dropna=False)["quote_value"]
                .sum()
                .sort_values(ascending=False)
                .reset_index(name="value")
            )
            max_quote = max(float(quote_status["value"].max()) if not quote_status.empty else 0.0, 1.0)
            status_chart = (
                alt.Chart(quote_status)
                .mark_bar(cornerRadiusTopLeft=10, cornerRadiusTopRight=10, size=44)
                .encode(
                    x=alt.X("status:N", title=None, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("value:Q", title="AED", scale=alt.Scale(domain=[0, max_quote])),
                    color=alt.Color(
                        "status:N",
                        legend=None,
                        scale=alt.Scale(
                            domain=["Accepted", "Sent", "Draft", "Rejected"],
                            range=["#16a34a", "#0ea5a4", "#38bdf8", "#f97316"],
                        ),
                    ),
                    tooltip=[
                        alt.Tooltip("status:N", title="Status"),
                        alt.Tooltip("value:Q", title="Quotation Value", format=",.0f"),
                    ],
                )
                .properties(height=280)
            )
            status_labels = (
                alt.Chart(quote_status)
                .mark_text(dy=-10, fontWeight=700, color="#13202a")
                .encode(x="status:N", y="value:Q", text=alt.Text("value:Q", format=",.0f"))
            )
            st.altair_chart(status_chart + status_labels, use_container_width=True)

    stage_counts = pd.DataFrame()
    if not prospects.empty and "status" in prospects.columns:
        stage_counts = (
            prospects.groupby("status", dropna=False)
            .size()
            .rename("count")
            .reindex(STATUSES, fill_value=0)
            .reset_index()
        )

    st.markdown("#### Stage Distribution")
    if stage_counts.empty:
        st.info("No stage data available yet.")
    else:
        stage_max = max(int(stage_counts["count"].max()) if not stage_counts.empty else 0, 1)
        stage_chart = (
            alt.Chart(stage_counts)
            .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, size=26)
            .encode(
                x=alt.X("status:N", sort=STATUSES, title=None, axis=alt.Axis(labelAngle=0, labelLimit=120)),
                y=alt.Y("count:Q", title="Lead Count", scale=alt.Scale(domain=[0, stage_max])),
                color=alt.Color(
                    "status:N",
                    sort=STATUSES,
                    legend=None,
                    scale=alt.Scale(range=["#0ea5a4", "#38bdf8", "#22c55e", "#facc15", "#f97316", "#14b8a6", "#64748b"]),
                ),
                tooltip=[alt.Tooltip("status:N", title="Stage"), alt.Tooltip("count:Q", title="Leads")],
            )
            .properties(height=220)
        )
        stage_labels = alt.Chart(stage_counts).mark_text(dy=-9, color="#13202a", fontWeight=700).encode(
            x=alt.X("status:N", sort=STATUSES), y="count:Q", text="count:Q"
        )
        st.altair_chart(stage_chart + stage_labels, use_container_width=True)


def render_period_report(data: dict[str, Any], start: date, end: date, label: str, combined_view: bool = False) -> None:
    prospects = data["prospects"]
    quotations = data["quotations"]
    activities = data.get("activity_log", [])

    connected = [p for p in prospects if date_in_range(p.get("connected_at", ""), start, end)]
    proposals = [q for q in quotations if date_in_range(q.get("created_date", ""), start, end)]
    prospect_updates = [p for p in prospects if date_in_range(p.get("updated_at", ""), start, end)]
    activities_in_period = [a for a in activities if date_in_range(a.get("activity_date", ""), start, end)]
    won_projects = [p for p in prospects if p.get("status") == "Won" and date_in_range(p.get("updated_at", ""), start, end)]

    connected_df = pd.DataFrame(connected)
    proposal_total = sum(float(x.get("quote_value", 0) or 0) for x in proposals)
    won_total = sum(float(x.get("estimated_value", 0) or 0) for x in won_projects)

    st.markdown(
        f"""
        <div class='report-hero'>
            <h3>{label.title()} Sales Performance Report</h3>
            <p>Date frame: {start} to {end}. Clean executive report focused on connected leads and core outcome metrics.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class='report-grid'>
            <div class='report-card'>
                <div class='kpi-label'>Leads Connected</div>
                <div class='kpi-value'>{len(connected)}</div>
                <div class='kpi-note'>Prospects moved into active conversations during the period.</div>
            </div>
            <div class='report-card'>
                <div class='kpi-label'>Proposals Shared</div>
                <div class='kpi-value'>{len(proposals)}</div>
                <div class='kpi-note'>Quoted opportunities issued to the market.</div>
            </div>
            <div class='report-card'>
                <div class='kpi-label'>Proposal Value</div>
                <div class='kpi-value'>AED {proposal_total:,.0f}</div>
                <div class='kpi-note'>Total value presented in proposals and quotations.</div>
            </div>
            <div class='report-card'>
                <div class='kpi-label'>Won Projects</div>
                <div class='kpi-value'>{len(won_projects)} | AED {won_total:,.0f}</div>
                <div class='kpi-note'>Commercial wins captured in the selected period.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("##### Leads Connected")
    if connected_df.empty:
        st.info("No connected leads in this period.")
    else:
        connected_view = connected_df[
            ["id", "company_name", "contact_name", "status", "connected_at", "next_action", "estimated_value"]
        ]
        render_dynamic_table(connected_view, "Connected Leads", key=f"{label}_connected", max_rows=120)


def save_report_bundle_to_downloads(
    label: str,
    connected_df: pd.DataFrame,
    proposals_df: pd.DataFrame,
    next_steps_df: pd.DataFrame,
    activities_df: pd.DataFrame,
    won_df: pd.DataFrame,
) -> list[Path]:
    report_dir = DOWNLOADS_DIR / "crm_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    connected_path = report_dir / f"{label}_connected_leads_{stamp}.csv"
    proposals_path = report_dir / f"{label}_proposals_shared_{stamp}.csv"
    next_steps_path = report_dir / f"{label}_next_steps_{stamp}.csv"
    activities_path = report_dir / f"{label}_activities_{stamp}.csv"
    won_path = report_dir / f"{label}_won_projects_{stamp}.csv"

    connected_df.to_csv(connected_path, index=False)
    proposals_df.to_csv(proposals_path, index=False)
    next_steps_df.to_csv(next_steps_path, index=False)
    activities_df.to_csv(activities_path, index=False)
    won_df.to_csv(won_path, index=False)

    return [connected_path, proposals_path, next_steps_path, activities_path, won_path]


def save_report_bundle_and_refresh(
    label: str,
    connected_df: pd.DataFrame,
    proposals_df: pd.DataFrame,
    next_steps_df: pd.DataFrame,
    activities_df: pd.DataFrame,
    won_df: pd.DataFrame,
) -> list[Path]:
    return save_report_bundle_to_downloads(
        label,
        connected_df,
        proposals_df,
        next_steps_df,
        activities_df,
        won_df,
    )


def _pdf_text_block(c: Any, text: str, x: float, y: float, width: float, leading: float = 14) -> float:
    words = text.split()
    line = ""
    current_y = y
    for word in words:
        candidate = f"{line} {word}".strip()
        if c.stringWidth(candidate, "Helvetica", 10) <= width:
            line = candidate
        else:
            c.drawString(x, current_y, line)
            current_y -= leading
            line = word
    if line:
        c.drawString(x, current_y, line)
        current_y -= leading
    return current_y

def _resolve_logo_path() -> Path | None:
    for path in [COMPANY_LOGO_SOURCE, COMPANY_LOGO_FALLBACK]:
        if path.exists():
            return path
    return None


def _draw_pdf_bar_chart(
    c: Any,
    *,
    title: str,
    labels: list[str],
    values: list[float],
    x: float,
    y: float,
    width: float,
    height: float,
    bar_color: str,
    value_prefix: str = "",
) -> None:
    from reportlab.lib import colors

    c.setFillColor(colors.HexColor("#eef7ff"))
    c.roundRect(x, y, width, height, 10, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#c9e2f3"))
    c.roundRect(x, y, width, height, 10, fill=0, stroke=1)

    c.setFillColor(colors.HexColor("#0f2940"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x + 10, y + height - 16, title)

    if not labels or not values:
        c.setFillColor(colors.HexColor("#64748b"))
        c.setFont("Helvetica", 9)
        c.drawString(x + 10, y + height / 2, "No data for selected period")
        return

    chart_x = x + 10
    chart_y = y + 22
    chart_w = width - 20
    chart_h = height - 44

    c.setStrokeColor(colors.HexColor("#b9d7ea"))
    c.line(chart_x, chart_y, chart_x, chart_y + chart_h)
    c.line(chart_x, chart_y, chart_x + chart_w, chart_y)

    max_val = max(values) if values else 0
    if max_val <= 0:
        max_val = 1

    bar_count = len(values)
    slot_w = chart_w / max(1, bar_count)
    bar_w = max(8, slot_w * 0.55)

    for i, value in enumerate(values):
        bh = (value / max_val) * (chart_h - 8)
        bx = chart_x + i * slot_w + (slot_w - bar_w) / 2
        by = chart_y

        c.setFillColor(colors.HexColor(bar_color))
        c.roundRect(bx, by, bar_w, bh, 3, fill=1, stroke=0)

        c.setFillColor(colors.HexColor("#0b2235"))
        c.setFont("Helvetica", 7)
        c.drawCentredString(bx + bar_w / 2, chart_y - 10, labels[i][:6])

        c.setFillColor(colors.HexColor("#334155"))
        c.setFont("Helvetica", 7)
        value_text = f"{value_prefix}{value:,.0f}" if value >= 100 else f"{value_prefix}{value:.0f}"
        c.drawCentredString(bx + bar_w / 2, by + bh + 3, value_text)


def save_weekly_executive_pdf_to_downloads(data: dict[str, Any], start: date, end: date) -> Path:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except Exception as exc:
        raise RuntimeError("reportlab is required. Install with: pip install reportlab") from exc

    prospects = data.get("prospects", [])
    quotations = data.get("quotations", [])
    purchase_orders = data.get("purchase_orders", [])
    activities = data.get("activity_log", [])

    weekly_new_prospects = [p for p in prospects if date_in_range(p.get("created_at", ""), start, end)]
    weekly_quotes = [q for q in quotations if date_in_range(q.get("created_date", ""), start, end)]
    weekly_pos = [po for po in purchase_orders if date_in_range(po.get("po_date", ""), start, end)]
    weekly_activities = [a for a in activities if date_in_range(a.get("activity_date", ""), start, end)]

    quote_total = sum(float(q.get("quote_value", 0) or 0) for q in weekly_quotes)
    po_total = sum(float(po.get("po_value", 0) or 0) for po in weekly_pos)
    prospect_est_total = sum(float(p.get("estimated_value", 0) or 0) for p in weekly_new_prospects)

    status_counts: dict[str, int] = {}
    for p in weekly_new_prospects:
        status = p.get("status", "New Lead")
        status_counts[status] = status_counts.get(status, 0) + 1

    quote_status_counts: dict[str, int] = {}
    for q in weekly_quotes:
        status = q.get("status", "Draft")
        quote_status_counts[status] = quote_status_counts.get(status, 0) + 1

    total_days = max((end - start).days + 1, 1)
    days = [start + timedelta(days=i) for i in range(total_days)]
    day_labels = [d.strftime("%a") for d in days]
    quote_value_by_day: list[float] = []
    prospect_count_by_day: list[float] = []
    for d in days:
        q_day = [q for q in weekly_quotes if safe_parse_date(q.get("created_date", "")) == d]
        p_day = [p for p in weekly_new_prospects if safe_parse_date(p.get("created_at", "")) == d]
        quote_value_by_day.append(sum(float(q.get("quote_value", 0) or 0) for q in q_day))
        prospect_count_by_day.append(float(len(p_day)))

    top_status = sorted(status_counts.items(), key=lambda x: x[1], reverse=True)
    top_quote_status = sorted(quote_status_counts.items(), key=lambda x: x[1], reverse=True)
    top_status_text = ", ".join(f"{k}: {v}" for k, v in top_status[:4]) if top_status else "No stage movement yet"
    top_quote_text = ", ".join(f"{k}: {v}" for k, v in top_quote_status[:4]) if top_quote_status else "No quote status movement yet"

    report_dir = DOWNLOADS_DIR / "crm_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    period_label = f"{start.isoformat()}_to_{end.isoformat()}"
    out_path = report_dir / f"weekly_executive_report_{period_label}_{stamp}.pdf"

    c = canvas.Canvas(str(out_path), pagesize=A4)
    page_w, page_h = A4

    c.setFillColor(colors.HexColor("#edf7fb"))
    c.rect(0, page_h - 136, page_w, 136, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#9bdaf0"))
    c.rect(0, page_h - 144, page_w, 8, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#fbbf24"))
    c.rect(0, page_h - 150, page_w, 6, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#c7e6f2"))
    c.line(0, page_h - 136, page_w, page_h - 136)

    c.setFillColor(colors.HexColor("#0f2940"))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(34, page_h - 56, "Metalys Enclosures Manufacturing")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(34, page_h - 78, "Weekly Executive CRM Intelligence Report")
    c.setFont("Helvetica", 11)
    c.drawString(34, page_h - 96, f"Date Frame: {start} to {end}")
    c.setFillColor(colors.HexColor("#1d4f68"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(34, page_h - 114, "PREMIUM ANALYTICS VIEW")

    logo_path = _resolve_logo_path()
    if logo_path:
        try:
            c.drawImage(
                str(logo_path),
                page_w - 170,
                page_h - 118,
                width=130,
                height=84,
                mask="auto",
                preserveAspectRatio=True,
            )
        except Exception:
            pass

    card_y = page_h - 244
    card_w = (page_w - 34 * 2 - 24) / 4
    card_h = 76
    cards = [
        ("New Prospects", str(len(weekly_new_prospects)), "Weekly lead creation", "#dbeafe"),
        ("Quote Value", f"AED {quote_total:,.0f}", f"{len(weekly_quotes)} quotations", "#cffafe"),
        ("PO Value", f"AED {po_total:,.0f}", f"{len(weekly_pos)} purchase orders", "#dcfce7"),
        ("Pipeline Added", f"AED {prospect_est_total:,.0f}", "Estimated potential", "#ffedd5"),
    ]
    for i, (title, value, note, shade) in enumerate(cards):
        x = 34 + i * (card_w + 8)
        c.setFillColor(colors.HexColor(shade))
        c.roundRect(x, card_y, card_w, card_h, 10, fill=1, stroke=0)
        c.setStrokeColor(colors.HexColor("#d3e4f3"))
        c.roundRect(x, card_y, card_w, card_h, 10, fill=0, stroke=1)
        c.setFillColor(colors.HexColor("#334155"))
        c.setFont("Helvetica", 8)
        c.drawCentredString(x + card_w / 2, card_y + 58, title.upper())
        c.setFillColor(colors.HexColor("#0b2235"))
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(x + card_w / 2, card_y + 38, value)
        c.setFillColor(colors.HexColor("#475569"))
        c.setFont("Helvetica", 8)
        c.drawCentredString(x + card_w / 2, card_y + 18, note)

    insight_box_y = card_y - 66
    c.setFillColor(colors.HexColor("#f8fafc"))
    c.roundRect(34, insight_box_y, page_w - 68, 56, 10, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#dbe7f2"))
    c.roundRect(34, insight_box_y, page_w - 68, 56, 10, fill=0, stroke=1)
    c.setFillColor(colors.HexColor("#0f2940"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(44, insight_box_y + 42, "Executive Narrative")
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica", 9)
    insight = (
        f"Pipeline acceleration this week: {len(weekly_new_prospects)} new prospects and AED {quote_total:,.0f} in quotations. "
        f"Sales stage trend: {top_status_text}. Quotation trend: {top_quote_text}."
    )
    _pdf_text_block(c, insight, 44, insight_box_y + 26, page_w - 88, leading=11)

    chart_y = insight_box_y - 190
    chart_w = (page_w - 80) / 2
    _draw_pdf_bar_chart(
        c,
        title="Daily Quotation Value",
        labels=day_labels,
        values=quote_value_by_day,
        x=34,
        y=chart_y,
        width=chart_w,
        height=176,
        bar_color="#0ea5a4",
        value_prefix="",
    )
    _draw_pdf_bar_chart(
        c,
        title="Daily New Prospects",
        labels=day_labels,
        values=prospect_count_by_day,
        x=44 + chart_w,
        y=chart_y,
        width=chart_w,
        height=176,
        bar_color="#f97316",
        value_prefix="",
    )

    c.setFillColor(colors.HexColor("#0f2940"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(34, chart_y - 12, "Strategic Highlights")
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica", 9)
    highlights = [
        f"Quotation to PO ratio (value): {((po_total / quote_total) * 100):.1f}%" if quote_total > 0 else "Quotation to PO ratio: not enough quote value data",
        f"Most active prospect stage this week: {top_status[0][0]} ({top_status[0][1]})" if top_status else "No stage transitions captured this week",
        f"Most common quotation status: {top_quote_status[0][0]} ({top_quote_status[0][1]})" if top_quote_status else "No quotations created this week",
    ]
    hy = chart_y - 24
    for item in highlights:
        c.drawString(36, hy, f"- {item}"[:132])
        hy -= 12

    # Always show weekly company and quotation detail snapshots on the main page.
    detail_box_y = 108
    detail_box_h = 152
    detail_box_w = (page_w - 80) / 2

    left_box_x = 34
    right_box_x = 44 + detail_box_w

    c.setFillColor(colors.HexColor("#f8fafc"))
    c.roundRect(left_box_x, detail_box_y, detail_box_w, detail_box_h, 10, fill=1, stroke=0)
    c.roundRect(right_box_x, detail_box_y, detail_box_w, detail_box_h, 10, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#dbe7f2"))
    c.roundRect(left_box_x, detail_box_y, detail_box_w, detail_box_h, 10, fill=0, stroke=1)
    c.roundRect(right_box_x, detail_box_y, detail_box_w, detail_box_h, 10, fill=0, stroke=1)

    c.setFillColor(colors.HexColor("#0f2940"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_box_x + 10, detail_box_y + detail_box_h - 16, "New Companies Added This Week")
    c.drawString(right_box_x + 10, detail_box_y + detail_box_h - 16, "Quotation Details by Company")

    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica", 8)
    left_y = detail_box_y + detail_box_h - 32
    if weekly_new_prospects:
        for prospect in weekly_new_prospects[:8]:
            line = (
                f"- {prospect.get('company_name', 'Unknown')} | "
                f"{prospect.get('status', 'New Lead')} | AED {float(prospect.get('estimated_value', 0) or 0):,.0f}"
            )
            c.drawString(left_box_x + 10, left_y, line[:62])
            left_y -= 12
    else:
        c.drawString(left_box_x + 10, left_y, "- No new companies added in this week")

    right_y = detail_box_y + detail_box_h - 32
    if weekly_quotes:
        for quote in weekly_quotes[:8]:
            line = (
                f"- {quote.get('customer_name', 'Unknown')} | {quote.get('product_name', '')} | "
                f"{quote.get('currency', 'AED')} {float(quote.get('quote_value', 0) or 0):,.0f}"
            )
            c.drawString(right_box_x + 10, right_y, line[:62])
            right_y -= 12
    else:
        c.drawString(right_box_x + 10, right_y, "- No quotation details in this week")

    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 8)
    c.drawString(34, 18, f"Generated on {now_stamp()} | Source: Sales CRM Dashboard")

    detail_rows = min(len(weekly_new_prospects), 14) + min(len(weekly_quotes), 14) + min(len(weekly_pos), 12)
    if detail_rows > 16:
        c.showPage()

        c.setFillColor(colors.HexColor("#082f49"))
        c.rect(0, page_h - 58, page_w, 58, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(34, page_h - 36, "Pipeline Detail Appendix")

        c.setFillColor(colors.HexColor("#0f2940"))
        c.setFont("Helvetica-Bold", 11)
        c.drawString(34, page_h - 82, "Top New Prospects")
        c.setFillColor(colors.HexColor("#1f2937"))
        c.setFont("Helvetica", 9)
        y = page_h - 98
        if weekly_new_prospects:
            for p in weekly_new_prospects[:14]:
                line = (
                    f"- {p.get('company_name', 'Unknown')} | {p.get('status', 'New Lead')} | "
                    f"Potential AED {float(p.get('estimated_value', 0) or 0):,.0f}"
                )
                c.drawString(36, y, line[:132])
                y -= 12
        else:
            c.drawString(36, y, "- No new prospects added in this week")
            y -= 12

        c.setFillColor(colors.HexColor("#0f2940"))
        c.setFont("Helvetica-Bold", 11)
        c.drawString(34, y - 8, "Latest Quotations")
        c.setFillColor(colors.HexColor("#1f2937"))
        c.setFont("Helvetica", 9)
        y -= 24
        if weekly_quotes:
            for q in weekly_quotes[:14]:
                line = (
                    f"- {q.get('customer_name', 'Unknown')} | {q.get('product_name', '')} | "
                    f"{q.get('currency', 'AED')} {float(q.get('quote_value', 0) or 0):,.0f} | {q.get('status', 'Draft')}"
                )
                c.drawString(36, y, line[:132])
                y -= 12
        else:
            c.drawString(36, y, "- No quotations issued in this week")
            y -= 12

        c.setFillColor(colors.HexColor("#0f2940"))
        c.setFont("Helvetica-Bold", 11)
        c.drawString(34, y - 8, "Latest Purchase Orders")
        c.setFillColor(colors.HexColor("#1f2937"))
        c.setFont("Helvetica", 9)
        y -= 24
        if weekly_pos:
            for po in weekly_pos[:12]:
                line = (
                    f"- {po.get('po_number', 'PO')} | {po.get('company_name', 'Unknown')} | "
                    f"AED {float(po.get('po_value', 0) or 0):,.0f} | {po.get('status', 'Issued')}"
                )
                c.drawString(36, y, line[:132])
                y -= 12
        else:
            c.drawString(36, y, "- No purchase orders captured in this week")

        c.setFillColor(colors.HexColor("#64748b"))
        c.setFont("Helvetica", 8)
        c.drawString(34, 18, f"Generated on {now_stamp()} | Page 2")

    c.save()
    return out_path


def save_monthly_executive_pdf_to_downloads(data: dict[str, Any], start: date, end: date) -> Path:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except Exception as exc:
        raise RuntimeError("reportlab is required. Install with: pip install reportlab") from exc

    prospects = data.get("prospects", [])
    quotations = data.get("quotations", [])
    purchase_orders = data.get("purchase_orders", [])
    activities = data.get("activity_log", [])

    monthly_new_prospects = [p for p in prospects if date_in_range(p.get("created_at", ""), start, end)]
    monthly_quotes = [q for q in quotations if date_in_range(q.get("created_date", ""), start, end)]
    monthly_pos = [po for po in purchase_orders if date_in_range(po.get("po_date", ""), start, end)]
    monthly_activities = [a for a in activities if date_in_range(a.get("activity_date", ""), start, end)]
    monthly_won = [p for p in prospects if p.get("status") == "Won" and date_in_range(p.get("updated_at", ""), start, end)]

    quote_total = sum(float(q.get("quote_value", 0) or 0) for q in monthly_quotes)
    po_total = sum(float(po.get("po_value", 0) or 0) for po in monthly_pos)
    pipeline_added = sum(float(p.get("estimated_value", 0) or 0) for p in monthly_new_prospects)
    won_total = sum(float(p.get("estimated_value", 0) or 0) for p in monthly_won)

    quote_status_counts: dict[str, int] = {}
    for q in monthly_quotes:
        status = q.get("status", "Draft")
        quote_status_counts[status] = quote_status_counts.get(status, 0) + 1
    top_quote_status = sorted(quote_status_counts.items(), key=lambda x: x[1], reverse=True)

    # Aggregate monthly trend by week bucket (Mon-Sun bucket labels).
    quote_week_totals: dict[date, float] = {}
    lead_week_counts: dict[date, float] = {}
    scan_day = start
    while scan_day <= end:
        week_start = scan_day - timedelta(days=scan_day.weekday())
        quote_week_totals.setdefault(week_start, 0.0)
        lead_week_counts.setdefault(week_start, 0.0)
        scan_day += timedelta(days=1)

    for q in monthly_quotes:
        qd = safe_parse_date(q.get("created_date", ""))
        if qd and start <= qd <= end:
            bucket = qd - timedelta(days=qd.weekday())
            quote_week_totals[bucket] = quote_week_totals.get(bucket, 0.0) + float(q.get("quote_value", 0) or 0)

    for p in monthly_new_prospects:
        pd_ = safe_parse_date(p.get("created_at", ""))
        if pd_ and start <= pd_ <= end:
            bucket = pd_ - timedelta(days=pd_.weekday())
            lead_week_counts[bucket] = lead_week_counts.get(bucket, 0.0) + 1.0

    ordered_buckets = sorted(quote_week_totals.keys())
    week_labels = [f"W{i+1}" for i in range(len(ordered_buckets))]
    quote_values = [quote_week_totals.get(k, 0.0) for k in ordered_buckets]
    lead_values = [lead_week_counts.get(k, 0.0) for k in ordered_buckets]

    report_dir = DOWNLOADS_DIR / "crm_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    period_label = f"{start.isoformat()}_to_{end.isoformat()}"
    out_path = report_dir / f"monthly_executive_report_{period_label}_{stamp}.pdf"

    c = canvas.Canvas(str(out_path), pagesize=A4)
    page_w, page_h = A4

    # Header aligned with weekly report visual language.
    c.setFillColor(colors.HexColor("#edf7fb"))
    c.rect(0, page_h - 136, page_w, 136, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#9bdaf0"))
    c.rect(0, page_h - 144, page_w, 8, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#fbbf24"))
    c.rect(0, page_h - 150, page_w, 6, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#c7e6f2"))
    c.line(0, page_h - 136, page_w, page_h - 136)

    c.setFillColor(colors.HexColor("#0f2940"))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(34, page_h - 56, "Metalys Enclosures Manufacturing")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(34, page_h - 78, "Monthly Executive CRM Intelligence Report")
    c.setFont("Helvetica", 11)
    c.drawString(34, page_h - 96, f"Date Frame: {start} to {end}")
    c.setFillColor(colors.HexColor("#1d4f68"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(34, page_h - 114, "PREMIUM MONTHLY ANALYTICS VIEW")

    logo_path = _resolve_logo_path()
    if logo_path:
        try:
            c.drawImage(
                str(logo_path),
                page_w - 170,
                page_h - 118,
                width=130,
                height=84,
                mask="auto",
                preserveAspectRatio=True,
            )
        except Exception:
            pass

    card_y = page_h - 244
    card_w = (page_w - 34 * 2 - 24) / 4
    card_h = 76
    cards = [
        ("New Prospects", str(len(monthly_new_prospects)), "Monthly lead creation", "#dbeafe"),
        ("Quote Value", f"AED {quote_total:,.0f}", f"{len(monthly_quotes)} quotations", "#cffafe"),
        ("PO Value", f"AED {po_total:,.0f}", f"{len(monthly_pos)} purchase orders", "#dcfce7"),
        ("Won Value", f"AED {won_total:,.0f}", f"{len(monthly_won)} won projects", "#ffedd5"),
    ]
    for i, (title, value, note, shade) in enumerate(cards):
        x = 34 + i * (card_w + 8)
        c.setFillColor(colors.HexColor(shade))
        c.roundRect(x, card_y, card_w, card_h, 10, fill=1, stroke=0)
        c.setStrokeColor(colors.HexColor("#d3e4f3"))
        c.roundRect(x, card_y, card_w, card_h, 10, fill=0, stroke=1)
        c.setFillColor(colors.HexColor("#334155"))
        c.setFont("Helvetica", 8)
        c.drawCentredString(x + card_w / 2, card_y + 58, title.upper())
        c.setFillColor(colors.HexColor("#0b2235"))
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(x + card_w / 2, card_y + 38, value)
        c.setFillColor(colors.HexColor("#475569"))
        c.setFont("Helvetica", 8)
        c.drawCentredString(x + card_w / 2, card_y + 18, note)

    insight_box_y = card_y - 66
    c.setFillColor(colors.HexColor("#f8fafc"))
    c.roundRect(34, insight_box_y, page_w - 68, 56, 10, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#dbe7f2"))
    c.roundRect(34, insight_box_y, page_w - 68, 56, 10, fill=0, stroke=1)
    c.setFillColor(colors.HexColor("#0f2940"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(44, insight_box_y + 42, "Monthly Narrative")
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica", 9)
    top_quote_text = ", ".join(f"{k}: {v}" for k, v in top_quote_status[:4]) if top_quote_status else "No quote status changes"
    insight = (
        f"Monthly summary: {len(monthly_new_prospects)} new prospects, AED {quote_total:,.0f} quotation value, "
        f"AED {po_total:,.0f} purchase orders, and AED {pipeline_added:,.0f} pipeline added. "
        f"Quote status mix: {top_quote_text}."
    )
    _pdf_text_block(c, insight, 44, insight_box_y + 26, page_w - 88, leading=11)

    chart_y = insight_box_y - 190
    chart_w = (page_w - 80) / 2
    _draw_pdf_bar_chart(
        c,
        title="Weekly Quotation Value Trend",
        labels=week_labels,
        values=quote_values,
        x=34,
        y=chart_y,
        width=chart_w,
        height=176,
        bar_color="#0ea5a4",
        value_prefix="",
    )
    _draw_pdf_bar_chart(
        c,
        title="Weekly New Companies Added",
        labels=week_labels,
        values=lead_values,
        x=44 + chart_w,
        y=chart_y,
        width=chart_w,
        height=176,
        bar_color="#f97316",
        value_prefix="",
    )

    c.setFillColor(colors.HexColor("#0f2940"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(34, chart_y - 12, "Strategic Highlights")
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica", 9)
    highlights = [
        f"Monthly quotation to PO ratio: {((po_total / quote_total) * 100):.1f}%" if quote_total > 0 else "Monthly quotation to PO ratio: not enough quote value data",
        f"Total activities completed: {len(monthly_activities)}",
        f"Average quotation value: AED {(quote_total / len(monthly_quotes)):,.0f}" if monthly_quotes else "Average quotation value: no monthly quotations",
    ]
    hy = chart_y - 24
    for item in highlights:
        c.drawString(36, hy, f"- {item}"[:132])
        hy -= 12

    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 8)
    c.drawString(34, 18, f"Generated on {now_stamp()} | Source: Sales CRM Dashboard")

    # Detail appendix page with richer monthly company and quotation detail.
    c.showPage()
    c.setFillColor(colors.HexColor("#082f49"))
    c.rect(0, page_h - 58, page_w, 58, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(34, page_h - 36, "Monthly Detail Appendix")

    c.setFillColor(colors.HexColor("#0f2940"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(34, page_h - 82, "New Companies Added")
    c.setFillColor(colors.HexColor("#1f2937"))
    c.setFont("Helvetica", 9)
    y = page_h - 98
    if monthly_new_prospects:
        for p in monthly_new_prospects[:20]:
            line = (
                f"- {p.get('company_name', 'Unknown')} | {p.get('status', 'New Lead')} | "
                f"Potential AED {float(p.get('estimated_value', 0) or 0):,.0f}"
            )
            c.drawString(36, y, line[:132])
            y -= 12
    else:
        c.drawString(36, y, "- No new companies added in this month")
        y -= 12

    c.setFillColor(colors.HexColor("#0f2940"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(34, y - 8, "Quotation Details (Company | Product | Value | Status)")
    c.setFillColor(colors.HexColor("#1f2937"))
    c.setFont("Helvetica", 9)
    y -= 24
    if monthly_quotes:
        for q in monthly_quotes[:24]:
            line = (
                f"- {q.get('customer_name', 'Unknown')} | {q.get('product_name', '')} | "
                f"{q.get('currency', 'AED')} {float(q.get('quote_value', 0) or 0):,.0f} | {q.get('status', 'Draft')}"
            )
            c.drawString(36, y, line[:132])
            y -= 12
            if y < 40:
                break
    else:
        c.drawString(36, y, "- No quotation details in this month")

    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 8)
    c.drawString(34, 18, f"Generated on {now_stamp()} | Page 2")

    c.save()
    return out_path
def period_frames(data: dict[str, Any], start: date, end: date) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prospects = data["prospects"]
    quotations = data["quotations"]
    activities = data.get("activity_log", [])

    connected = [p for p in prospects if date_in_range(p.get("connected_at", ""), start, end)]
    proposals = [q for q in quotations if date_in_range(q.get("created_date", ""), start, end)]
    activities_in_period = [a for a in activities if date_in_range(a.get("activity_date", ""), start, end)]
    won_projects = [p for p in prospects if p.get("status") == "Won" and date_in_range(p.get("updated_at", ""), start, end)]
    connected_df = pd.DataFrame(connected)
    proposals_df = pd.DataFrame(proposals)
    activities_df = pd.DataFrame(activities_in_period)

    prospect_map = {p["id"]: p for p in prospects}
    next_steps_rows = []
    for quote in proposals:
        linked = prospect_map.get(quote.get("prospect_id", ""), {})
        next_steps_rows.append(
            {
                "prospect_id": quote.get("prospect_id", ""),
                "company_name": quote.get("customer_name", ""),
                "product_name": quote.get("product_name", ""),
                "quote_value": quote.get("quote_value", 0),
                "quote_status": quote.get("status", ""),
                "next_step": linked.get("next_action", ""),
                "current_stage": linked.get("status", ""),
                "expected_close_date": linked.get("expected_close_date", ""),
            }
        )
    next_steps_df = pd.DataFrame(next_steps_rows)

    quote_map = latest_quote_map(quotations)
    won_rows = []
    for project in won_projects:
        q = quote_map.get(project["id"], {})
        won_rows.append(
            {
                "prospect_id": project.get("id", ""),
                "company_name": project.get("company_name", ""),
                "contact_name": project.get("contact_name", ""),
                "product_name": q.get("product_name", project.get("product_interest", "")),
                "quotation_value": float(q.get("quote_value", 0) or 0),
                "quote_status": q.get("status", ""),
                "won_date": project.get("updated_at", ""),
                "next_step": project.get("next_action", ""),
            }
        )
    won_df = pd.DataFrame(won_rows)

    if connected_df.empty:
        connected_view = pd.DataFrame(
            columns=["id", "company_name", "contact_name", "status", "connected_at", "next_action", "estimated_value"]
        )
    else:
        connected_view = connected_df[
            ["id", "company_name", "contact_name", "status", "connected_at", "next_action", "estimated_value"]
        ]

    if proposals_df.empty:
        proposal_view = pd.DataFrame(
            columns=["id", "prospect_id", "customer_name", "product_name", "quote_value", "status", "created_date"]
        )
    else:
        proposal_view = proposals_df[
            ["id", "prospect_id", "customer_name", "product_name", "quote_value", "status", "created_date"]
        ]

    if activities_df.empty:
        activities_view = pd.DataFrame(
            columns=["activity_id", "activity_type", "company_name", "details", "product_name", "amount", "activity_date", "status"]
        )
    else:
        activities_view = activities_df[
            ["activity_id", "activity_type", "company_name", "details", "product_name", "amount", "activity_date", "status"]
        ]

    if won_df.empty:
        won_view = pd.DataFrame(
            columns=["prospect_id", "company_name", "contact_name", "product_name", "quotation_value", "quote_status", "won_date", "next_step"]
        )
    else:
        won_view = won_df[
            ["prospect_id", "company_name", "contact_name", "product_name", "quotation_value", "quote_status", "won_date", "next_step"]
        ]

    return connected_view, proposal_view, next_steps_df, activities_view, won_view


def reports_view(data: dict[str, Any]) -> None:
    render_workspace_hero(
        "Workspace",
        "Weekly and Monthly Reports",
        "Clean executive reporting for weekly and monthly performance with one-click premium PDF generation.",
    )

    st.markdown(
        """
        <style>
            .report-action-panel {
                border: 1px solid rgba(16, 61, 85, 0.14);
                border-radius: 16px;
                padding: 14px;
                background: linear-gradient(145deg, rgba(255,255,255,0.94), rgba(239,248,255,0.95));
                box-shadow: 0 10px 22px rgba(10, 34, 50, 0.08);
                margin: 8px 0 14px;
            }
            .report-log-label {
                font-size: 0.82rem;
                text-transform: uppercase;
                letter-spacing: 0.09em;
                color: #2a5878;
                font-weight: 700;
            }
            .report-log-value {
                font-size: 1rem;
                color: #10283b;
                font-weight: 600;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    current_day = date.today()

    r1, r2 = st.columns(2)
    with r1:
        selected_week = st.date_input("Report week anchor date", value=current_day)
    with r2:
        selected_month = st.selectbox(
            "Report month",
            list(range(1, 13)),
            index=current_day.month - 1,
            format_func=lambda m: f"{calendar.month_name[m]} {current_day.year}",
        )

    active_week_start = selected_week - timedelta(days=selected_week.weekday())
    active_week_end = min(selected_week, active_week_start + timedelta(days=4))
    month_start = date(current_day.year, selected_month, 1)
    month_end = date(current_day.year, selected_month, calendar.monthrange(current_day.year, selected_month)[1])

    wtab, mtab = st.tabs(["Weekly", "Monthly"])

    with wtab:
        st.caption("Weekly reports use business week range: Monday to Friday.")
        st.write(f"Period: {active_week_start} to {active_week_end}")
        render_period_report(data, active_week_start, active_week_end, "weekly")

        weekly_generated = st.session_state.get("weekly_report_generated_date", "-")
        weekly_downloaded = st.session_state.get("weekly_report_downloaded_date", "-")
        st.markdown(
            f"""
            <div class='report-action-panel'>
                <div class='report-log-label'>Logs</div>
                <div class='report-log-value'>Generated: {html.escape(str(weekly_generated))}</div>
                <div class='report-log-value'>Downloaded: {html.escape(str(weekly_downloaded))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Generate Weekly Premium Report", width="stretch"):
            try:
                run_key = f"{active_week_start}_{active_week_end}"
                last_key = st.session_state.get("last_weekly_pdf_key", "")
                last_at = st.session_state.get("last_weekly_pdf_at")
                now_time = datetime.now()

                if last_key == run_key and isinstance(last_at, datetime) and (now_time - last_at).total_seconds() < 4:
                    st.warning("Weekly report already generated just now. Skipping duplicate run.")
                else:
                    out_path = save_weekly_executive_pdf_to_downloads(data, active_week_start, active_week_end)
                    st.session_state["last_weekly_pdf_key"] = run_key
                    st.session_state["last_weekly_pdf_at"] = now_time
                    st.session_state["weekly_report_path"] = str(out_path)
                    st.session_state["weekly_report_generated_date"] = today_iso()
                    st.success(f"Weekly executive PDF generated: {out_path}")
            except Exception as exc:
                st.error(f"Could not generate weekly executive PDF: {exc}")

        weekly_path = st.session_state.get("weekly_report_path", "")
        if weekly_path and Path(weekly_path).exists():
            weekly_bytes = Path(weekly_path).read_bytes()
            if st.download_button(
                "Download Weekly Premium Report",
                data=weekly_bytes,
                file_name=Path(weekly_path).name,
                mime="application/pdf",
                width="stretch",
            ):
                st.session_state["weekly_report_downloaded_date"] = today_iso()

    with mtab:
        st.write(f"Period: {month_start} to {month_end}")
        render_period_report(data, month_start, month_end, "monthly", combined_view=True)

        monthly_generated = st.session_state.get("monthly_report_generated_date", "-")
        monthly_downloaded = st.session_state.get("monthly_report_downloaded_date", "-")
        st.markdown(
            f"""
            <div class='report-action-panel'>
                <div class='report-log-label'>Logs</div>
                <div class='report-log-value'>Generated: {html.escape(str(monthly_generated))}</div>
                <div class='report-log-value'>Downloaded: {html.escape(str(monthly_downloaded))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Generate Monthly Premium Report", width="stretch"):
            try:
                run_key = f"{month_start}_{month_end}"
                last_key = st.session_state.get("last_monthly_pdf_key", "")
                last_at = st.session_state.get("last_monthly_pdf_at")
                now_time = datetime.now()

                if last_key == run_key and isinstance(last_at, datetime) and (now_time - last_at).total_seconds() < 4:
                    st.warning("Monthly report already generated just now. Skipping duplicate run.")
                else:
                    out_path = save_monthly_executive_pdf_to_downloads(data, month_start, month_end)
                    st.session_state["last_monthly_pdf_key"] = run_key
                    st.session_state["last_monthly_pdf_at"] = now_time
                    st.session_state["monthly_report_path"] = str(out_path)
                    st.session_state["monthly_report_generated_date"] = today_iso()
                    st.success(f"Monthly executive PDF generated: {out_path}")
            except Exception as exc:
                st.error(f"Could not generate monthly executive PDF: {exc}")

        monthly_path = st.session_state.get("monthly_report_path", "")
        if monthly_path and Path(monthly_path).exists():
            monthly_bytes = Path(monthly_path).read_bytes()
            if st.download_button(
                "Download Monthly Premium Report",
                data=monthly_bytes,
                file_name=Path(monthly_path).name,
                mime="application/pdf",
                width="stretch",
            ):
                st.session_state["monthly_report_downloaded_date"] = today_iso()


def main() -> None:
    style_app()
    data = load_data()
    if ensure_schema(data):
        save_data(data)

    components.html(
        "<script>setTimeout(() => window.location.reload(), 30000);</script>",
        height=0,
    )

    with st.sidebar:
        st.title("Sales Workspace")
        section = st.radio(
            "Go to",
            [
                "Dashboard",
                "Global Search",
                "Lead 360",
                "Follow-ups",
                "Customers",
                "Prospects",
                "Technical Drawings",
                "Pipeline",
                "Quotations",
                "Purchase Orders",
                "Insights",
                "Reports",
            ],
            label_visibility="collapsed",
        )
        st.markdown("---")
        if st.button("Reset to Sample Data", width="stretch"):
            save_data_and_refresh(SAMPLE_DATA)

    if section == "Dashboard":
        dashboard(data)
    elif section == "Global Search":
        global_search_view(data)
    elif section == "Lead 360":
        lead_360_view(data)
    elif section == "Follow-ups":
        followups_view(data)
    elif section == "Customers":
        customers_view(data)
    elif section == "Prospects":
        prospects_view(data)
    elif section == "Technical Drawings":
        technical_drawings_view(data)
    elif section == "Pipeline":
        pipeline_view(data)
    elif section == "Quotations":
        quotations_view(data)
    elif section == "Purchase Orders":
        purchase_orders_view(data)
    elif section == "Insights":
        insights_view(data)
    elif section == "Reports":
        reports_view(data)


if __name__ == "__main__":
    main()
