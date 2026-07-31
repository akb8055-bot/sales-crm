from datetime import date, timedelta

import pandas as pd
import streamlit as st

from app import (
    QUOTE_STATUSES,
    STATUSES,
    ensure_schema,
    load_data,
    render_dynamic_table,
    render_workspace_hero,
    save_data,
    style_app,
)


def _pipeline_summary_df(prospects: list[dict]) -> pd.DataFrame:
    counts = []
    for status in STATUSES:
        counts.append({"status": status, "lead_count": sum(1 for p in prospects if p.get("status") == status)})
    return pd.DataFrame(counts)


def _latest_updates_df(activities: list[dict]) -> pd.DataFrame:
    if not activities:
        return pd.DataFrame(columns=["activity_date", "company_name", "activity_type", "details", "status"])
    df = pd.DataFrame(activities)
    show_cols = [
        c
        for c in ["activity_date", "company_name", "activity_type", "details", "status"]
        if c in df.columns
    ]
    if not show_cols:
        return pd.DataFrame(columns=["activity_date", "company_name", "activity_type", "details", "status"])
    return df.sort_values("activity_date", ascending=False)[show_cols]


def main() -> None:
    style_app()
    data = load_data()
    if ensure_schema(data):
        save_data(data)

    prospects = data.get("prospects", [])
    quotes = data.get("quotations", [])
    activities = data.get("activity_log", [])

    render_workspace_hero(
        "Executive View",
        "CEO Command Deck",
        "Read-only strategic visibility on companies, quotations shared, latest updates, and pipeline movement.",
    )

    total_companies = len({p.get("company_name", "").strip() for p in prospects if p.get("company_name", "").strip()})
    total_quotes = len(quotes)
    total_quote_value = sum(float(q.get("quote_value", 0) or 0) for q in quotes)
    won_count = sum(1 for p in prospects if p.get("status") == "Won")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Companies", total_companies)
    m2.metric("Quotations Shared", total_quotes)
    m3.metric("Total Quote Value", f"AED {total_quote_value:,.0f}")
    m4.metric("Won Projects", won_count)

    st.markdown("### Companies and Latest Status")
    prospects_df = pd.DataFrame(prospects)
    if prospects_df.empty:
        st.info("No prospect/company records available yet.")
    else:
        company_cols = [
            c
            for c in ["id", "company_name", "contact_name", "status", "next_action", "updated_at"]
            if c in prospects_df.columns
        ]
        render_dynamic_table(
            prospects_df[company_cols],
            "Company Overview",
            key="ceo_company_overview",
            max_rows=max(1, len(prospects_df)),
            strict_columns=True,
        )

    st.markdown("### Quotations Shared")
    quotes_df = pd.DataFrame(quotes)
    if quotes_df.empty:
        st.info("No quotations available yet.")
    else:
        if "linked_drawing_ids" in quotes_df.columns:
            quotes_df["linked_drawing_ids"] = quotes_df["linked_drawing_ids"].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else str(x or "")
            )
        quote_cols = [
            c
            for c in [
                "id",
                "customer_name",
                "product_name",
                "quote_value",
                "status",
                "created_date",
                "linked_drawing_ids",
            ]
            if c in quotes_df.columns
        ]
        render_dynamic_table(
            quotes_df[quote_cols],
            "Quotations Shared",
            key="ceo_quotations",
            max_rows=max(1, len(quotes_df)),
            strict_columns=True,
        )

    st.markdown("### Pipeline Summary")
    pipeline_df = _pipeline_summary_df(prospects)
    render_dynamic_table(
        pipeline_df,
        "Pipeline by Stage",
        key="ceo_pipeline_summary",
        max_rows=max(1, len(pipeline_df)),
        strict_columns=True,
    )

    st.markdown("### Latest Updates")
    updates_df = _latest_updates_df(activities)
    render_dynamic_table(
        updates_df.head(80),
        "Recent Business Updates",
        key="ceo_latest_updates",
        max_rows=80,
        strict_columns=True,
    )


if __name__ == "__main__":
    main()
