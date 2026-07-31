from datetime import date, datetime

import altair as alt
import pandas as pd
import streamlit as st

from app import STATUSES, ensure_schema, load_data, render_dynamic_table, save_data


def _apply_ceo_style() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Source+Sans+3:wght@400;500;600;700&display=swap');

            :root {
                --ink: #0f1c2e;
                --muted: #41556f;
                --card: rgba(255,255,255,0.92);
                --line: rgba(15, 37, 59, 0.14);
                --accent: #0d698b;
                --accent-2: #b7791f;
            }

            .stApp {
                font-family: 'Source Sans 3', sans-serif;
                color: var(--ink);
                background:
                    radial-gradient(circle at 12% 8%, rgba(14, 106, 140, 0.14), transparent 33%),
                    radial-gradient(circle at 92% 4%, rgba(183, 121, 31, 0.16), transparent 30%),
                    linear-gradient(160deg, #f8fbff 0%, #eef3f8 48%, #f9f5ee 100%);
            }

            .block-container {
                max-width: 1380px;
                padding-top: 1.4rem !important;
                padding-bottom: 2.4rem !important;
            }

            .ceo-hero {
                border-radius: 26px;
                padding: 28px 30px;
                border: 1px solid rgba(255,255,255,0.42);
                background: linear-gradient(135deg, #0f2f49 0%, #146a88 56%, #b7791f 100%);
                box-shadow: 0 22px 48px rgba(10, 28, 44, 0.28);
                color: #f5fbff;
                margin-bottom: 18px;
            }

            .ceo-eyebrow {
                text-transform: uppercase;
                letter-spacing: 0.14em;
                font-size: 0.9rem;
                opacity: 0.92;
                font-weight: 700;
            }

            .ceo-title {
                font-family: 'Fraunces', serif;
                font-size: 3rem;
                line-height: 1.08;
                margin: 8px 0 8px;
                letter-spacing: -0.01em;
            }

            .ceo-subtitle {
                font-size: 1.16rem;
                line-height: 1.6;
                max-width: 84ch;
                color: #dbf3ff;
            }

            div[data-testid="metric-container"] {
                background: var(--card);
                border: 1px solid var(--line);
                border-radius: 18px;
                padding: 15px 16px;
                box-shadow: 0 10px 22px rgba(11, 28, 45, 0.08);
            }

            div[data-testid="metric-container"] label {
                font-size: 1.02rem !important;
                font-weight: 700 !important;
            }

            div[data-testid="metric-container"] [data-testid="stMetricValue"] {
                font-size: 2rem !important;
                font-weight: 700 !important;
                letter-spacing: -0.01em;
            }

            h2, h3 {
                font-family: 'Fraunces', serif;
                color: var(--ink);
                letter-spacing: -0.01em;
            }

            h2 {
                font-size: 2.05rem;
            }

            h3 {
                font-size: 1.7rem;
            }

            .ceo-note {
                background: rgba(255, 255, 255, 0.74);
                border: 1px solid var(--line);
                border-left: 5px solid var(--accent);
                border-radius: 14px;
                padding: 12px 14px;
                color: var(--muted);
                font-size: 1.08rem;
                margin-bottom: 12px;
            }

            .stMarkdown p, .stCaption {
                font-size: 1.06rem;
                line-height: 1.55;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _safe_date(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _pipeline_summary_df(prospects: list[dict]) -> pd.DataFrame:
    rows = []
    for status in STATUSES:
        rows.append({"status": status, "lead_count": sum(1 for p in prospects if p.get("status") == status)})
    return pd.DataFrame(rows)


def _is_ceo_level_activity(activity: dict) -> bool:
    activity_type = str(activity.get("activity_type", "")).strip().lower()
    details = str(activity.get("details", "")).strip().lower()

    if activity_type == "proposal shared":
        return True
    if activity_type == "prospect updated" and any(
        keyword in details
        for keyword in ["discussion", "discuss", "meeting", "call", "follow-up", "follow up", "next action"]
    ):
        return True
    return False


def _ceo_updates_df(activities: list[dict]) -> pd.DataFrame:
    filtered = [a for a in activities if _is_ceo_level_activity(a)]
    if not filtered:
        return pd.DataFrame(columns=["activity_date", "company_name", "activity_type", "details", "status", "amount"])

    df = pd.DataFrame(filtered)
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    else:
        df["amount"] = 0.0

    df["_date_sort"] = df["activity_date"].apply(lambda x: _safe_date(str(x)) or date.min)
    df = df.sort_values("_date_sort", ascending=False).drop(columns=["_date_sort"])
    cols = ["activity_date", "company_name", "activity_type", "details", "status", "amount"]
    return df[cols]


def _stage_aging_df(prospects: list[dict]) -> pd.DataFrame:
    rows: list[dict] = []
    today = date.today()
    for p in prospects:
        status = str(p.get("status", ""))
        if status in {"Won", "Lost"}:
            continue
        start_date = _safe_date(str(p.get("updated_at", ""))) or _safe_date(str(p.get("created_at", "")))
        if not start_date:
            continue
        age_days = (today - start_date).days
        rows.append(
            {
                "company_name": str(p.get("company_name", "")),
                "status": status,
                "age_days": max(age_days, 0),
                "next_action": str(p.get("next_action", "")),
            }
        )
    return pd.DataFrame(rows)


def _render_hero() -> None:
    st.markdown(
        """
        <div class='ceo-hero'>
            <div class='ceo-eyebrow'>Sales CRM</div>
            <div class='ceo-title'>Metalys Enclosures Manufacturing</div>
            <div class='ceo-subtitle'>Executive dashboard for strategic decision-making: pipeline health, commercial velocity, top opportunities, and business-critical updates only.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    _apply_ceo_style()
    data = load_data()
    if ensure_schema(data):
        save_data(data)

    prospects = data.get("prospects", [])
    quotes = data.get("quotations", [])
    purchase_orders = data.get("purchase_orders", [])
    activities = data.get("activity_log", [])

    _render_hero()

    total_companies = len({str(p.get("company_name", "")).strip() for p in prospects if str(p.get("company_name", "")).strip()})
    total_quotes = len(quotes)
    total_quote_value = sum(float(q.get("quote_value", 0) or 0) for q in quotes)
    won_count = sum(1 for p in prospects if p.get("status") == "Won")
    open_pipeline_value = sum(float(p.get("estimated_value", 0) or 0) for p in prospects if p.get("status") not in {"Won", "Lost"})
    po_total = sum(float(po.get("po_value", 0) or 0) for po in purchase_orders)

    conversion = (won_count / len(prospects) * 100.0) if prospects else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Companies", total_companies)
    m2.metric("Open Pipeline", f"AED {open_pipeline_value:,.0f}")
    m3.metric("Quotations Shared", total_quotes)
    m4.metric("Win Ratio", f"{conversion:.1f}%")

    m5, m6, m7 = st.columns(3)
    m5.metric("Total Quoted Value", f"AED {total_quote_value:,.0f}")
    m6.metric("Won Projects", won_count)
    m7.metric("PO Confirmed Value", f"AED {po_total:,.0f}")

    st.markdown("### Strategic Insights")
    insight_col1, insight_col2 = st.columns([1.15, 1])

    with insight_col1:
        pipeline_df = _pipeline_summary_df(prospects)
        chart = (
            alt.Chart(pipeline_df)
            .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, size=42)
            .encode(
                x=alt.X("status:N", sort=STATUSES, title=None, axis=alt.Axis(labelAngle=0, labelFontSize=13)),
                y=alt.Y("lead_count:Q", title="Lead Count"),
                color=alt.Color("status:N", sort=STATUSES, legend=None, scale=alt.Scale(range=["#315f87", "#2a7ea0", "#1b9aaa", "#ca8a04", "#db6c38", "#1d7f5f", "#607084"])),
                tooltip=["status", "lead_count"],
            )
            .properties(height=300)
        )
        st.altair_chart(chart, use_container_width=True)

    with insight_col2:
        quotes_df = pd.DataFrame(quotes)
        if not quotes_df.empty and "status" in quotes_df.columns:
            q_status = quotes_df["status"].fillna("Draft").value_counts().reset_index()
            q_status.columns = ["quote_status", "count"]
            pie = (
                alt.Chart(q_status)
                .mark_arc(innerRadius=66)
                .encode(
                    theta=alt.Theta("count:Q"),
                    color=alt.Color("quote_status:N", legend=alt.Legend(title="Quote Status"), scale=alt.Scale(range=["#1f77b4", "#0ea5a4", "#22c55e", "#ef4444"])),
                    tooltip=["quote_status", "count"],
                )
                .properties(height=300)
            )
            st.altair_chart(pie, use_container_width=True)
        else:
            st.info("No quotations available for status insight yet.")

    stage_age_df = _stage_aging_df(prospects)
    if not stage_age_df.empty:
        st.markdown("### Stage Aging Watchlist")
        watchlist = stage_age_df.sort_values("age_days", ascending=False).head(12)
        watchlist = watchlist.drop(columns=["age_days"], errors="ignore")
        render_dynamic_table(
            watchlist,
            "Longest Open Opportunities",
            key="ceo_stage_aging",
            max_rows=max(1, len(watchlist)),
            strict_columns=True,
        )
    else:
        st.markdown("<div class='ceo-note'>No aging risk identified yet on open opportunities.</div>", unsafe_allow_html=True)

    st.markdown("### CEO Updates (Business-Critical Only)")
    st.markdown(
        "<div class='ceo-note'>Includes only proposal shared events and recent discussion-level updates with companies. Routine uploads and low-level edits are excluded.</div>",
        unsafe_allow_html=True,
    )
    updates_df = _ceo_updates_df(activities)
    render_dynamic_table(
        updates_df.head(80),
        "Executive Activity Feed",
        key="ceo_updates",
        max_rows=80,
        strict_columns=True,
    )

    st.markdown("### Company Dashboard")
    prospects_df = pd.DataFrame(prospects)
    if prospects_df.empty:
        st.info("No prospect/company records available yet.")
    else:
        company_cols = [
            c
            for c in ["id", "company_name", "contact_name", "status", "estimated_value", "next_action"]
            if c in prospects_df.columns
        ]
        render_dynamic_table(
            prospects_df[company_cols],
            "Company Opportunity Register",
            key="ceo_company_overview",
            max_rows=max(1, len(prospects_df)),
            strict_columns=True,
        )


if __name__ == "__main__":
    main()
