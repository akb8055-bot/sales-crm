import json
import base64
import calendar
from datetime import date, datetime
from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Custom Sales CRM", page_icon="📈", layout="wide")

APP_RELEASE = "2026-07-29-r2"
DOWNLOADS_DIR = Path.home() / "Downloads"

DATA_FILE = Path(__file__).parent / "crm_data.json"
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
    "customers": [
        {
            "id": "CUST-1001",
            "company_name": "Aurora Hospitality Group",
            "contact_name": "Nadia Rahman",
            "email": "nadia@aurorahg.com",
            "phone": "+971-50-123-1111",
            "industry": "Hospitality",
            "city": "Abu Dhabi",
            "country": "UAE",
            "account_owner": "Adithya",
            "lifecycle_stage": "Active",
            "annual_revenue": 2500000,
            "last_contact": "2026-07-24",
            "notes": "Prefers quarterly pricing reviews",
        }
    ],
    "prospects": [
        {
            "id": "LEAD-2001",
            "customer_id": "",
            "company_name": "Seabreeze Resorts",
            "contact_name": "Liam Farooq",
            "email": "liam@seabreezeresorts.com",
            "phone": "+971-50-555-2020",
            "source": "Referral",
            "industry": "Hospitality",
            "product_interest": "Operations Automation Suite",
            "estimated_value": 120000,
            "status": "Qualified",
            "expected_close_date": "2026-08-30",
            "next_action": "Product demo on Tuesday",
            "notes": "High urgency due to current vendor issues",
            "created_at": "2026-07-20 10:00",
            "updated_at": "2026-07-24 16:15",
        },
        {
            "id": "LEAD-2002",
            "customer_id": "",
            "company_name": "BlueHarbor Stays",
            "contact_name": "Eva Thomas",
            "email": "eva@blueharborstays.com",
            "phone": "+971-50-777-9090",
            "source": "Inbound",
            "industry": "Real Estate",
            "product_interest": "Sales Intelligence Module",
            "estimated_value": 65000,
            "status": "Proposal Sent",
            "expected_close_date": "2026-08-12",
            "next_action": "Follow up on legal redlines",
            "notes": "Procurement lead requested revised payment terms",
            "created_at": "2026-07-18 13:20",
            "updated_at": "2026-07-25 09:10",
        },
    ],
    "quotations": [
        {
            "id": "Q-3001",
            "prospect_id": "LEAD-2002",
            "customer_name": "BlueHarbor Stays",
            "product_name": "Sales Intelligence Module",
            "quote_value": 62000,
            "currency": "AED",
            "status": "Sent",
            "created_date": "2026-07-25",
            "valid_until": "2026-08-10",
            "notes": "Includes onboarding and 6 months support",
        }
    ],
    "prospect_attachments": {
        "LEAD-2002": [
            {
                "file_id": "ATT-4001",
                "file_name": "BlueHarbor_Quote_July.pdf",
                "mime_type": "application/pdf",
                "uploaded_at": "2026-07-25 10:40",
                "content_b64": "U2FtcGxlIFF1b3RhdGlvbiBGaWxl",
            }
        ]
    },
}


def style_app() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;600&display=swap');

            :root {
                --ink: #13202a;
                --muted: #5c6f7d;
                --paper: #f6f8f7;
                --glass: rgba(255, 255, 255, 0.82);
                --accent: #0ea5a4;
                --accent-2: #f97316;
                --ok: #16a34a;
                --warn: #d97706;
            }

            .stApp {
                font-family: 'Space Grotesk', sans-serif;
                color: var(--ink);
                background:
                    radial-gradient(circle at 10% 5%, rgba(14, 165, 164, 0.22), transparent 32%),
                    radial-gradient(circle at 86% 12%, rgba(249, 115, 22, 0.20), transparent 34%),
                    linear-gradient(170deg, #f9fbff 0%, #edf6f3 48%, #f8f4ee 100%);
            }

            h1, h2, h3 {
                letter-spacing: -0.02em;
            }

            .hero {
                background: linear-gradient(135deg, rgba(10, 18, 28, 0.94), rgba(17, 94, 89, 0.92));
                border-radius: 20px;
                padding: 20px 24px;
                color: #eef9f8;
                margin-bottom: 14px;
                border: 1px solid rgba(255, 255, 255, 0.16);
                box-shadow: 0 14px 30px rgba(12, 22, 34, 0.2);
            }

            .hero p {
                margin: 4px 0 0;
                color: #ccf0ed;
            }

            .metric-card {
                background: var(--glass);
                border: 1px solid rgba(16, 30, 42, 0.08);
                border-radius: 16px;
                padding: 14px;
                backdrop-filter: blur(6px);
            }

            .pipeline-card {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(12, 32, 46, 0.1);
                border-radius: 12px;
                padding: 10px;
                margin-bottom: 10px;
                box-shadow: 0 8px 20px rgba(17, 38, 54, 0.08);
            }

            .pipeline-title {
                font-weight: 700;
                margin-bottom: 6px;
            }

            .mono {
                font-family: 'IBM Plex Mono', monospace;
                color: var(--muted);
                font-size: 0.83rem;
            }

            .stSidebar {
                background: linear-gradient(180deg, #0f2f31 0%, #103343 55%, #172430 100%);
            }

            .stSidebar * {
                color: #e9fffb !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def today_iso() -> str:
    return str(date.today())


def load_data() -> dict[str, list[dict[str, Any]]]:
    if not DATA_FILE.exists():
        save_data(SAMPLE_DATA)
        return SAMPLE_DATA

    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


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
    if "prospect_attachments" not in data or not isinstance(data.get("prospect_attachments"), dict):
        data["prospect_attachments"] = {}
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

    return changed


def save_data(data: dict[str, list[dict[str, Any]]]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


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


def render_attachment_manager(data: dict[str, Any], prospects: list[dict[str, Any]], key_prefix: str) -> None:
    attachments = data["prospect_attachments"]
    if not prospects:
        st.info("Create a prospect first to upload quotation PDFs.")
        return

    upload_options = {f"{p['id']} | {p['company_name']}": p["id"] for p in prospects}
    upload_label = st.selectbox(
        "Select prospect",
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

    if st.button("Save Uploaded PDF Files", width="stretch", key=f"{key_prefix}_save_upload_btn"):
        if not uploaded_files:
            st.warning("Please choose one or more PDF files first.")
        else:
            files_for_prospect = attachments.setdefault(upload_prospect_id, [])
            current_ids = [f.get("file_id", "") for f in files_for_prospect]
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
            save_data(data)
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
                    save_data(data)
                    st.success("File deleted.")
                    st.rerun()
    else:
        st.caption("No quotation PDFs uploaded for this prospect yet.")


def dashboard(data: dict[str, list[dict[str, Any]]]) -> None:
    customers = data["customers"]
    prospects = data["prospects"]
    quotations = data["quotations"]

    total_pipeline = sum(float(p.get("estimated_value", 0) or 0) for p in prospects if p.get("status") != "Lost")
    won_value = sum(float(p.get("estimated_value", 0) or 0) for p in prospects if p.get("status") == "Won")
    open_leads = sum(1 for p in prospects if p.get("status") not in {"Won", "Lost"})
    conversion = (sum(1 for p in prospects if p.get("status") == "Won") / len(prospects) * 100) if prospects else 0

    st.markdown(
        """
        <div class='hero'>
            <h2 style='margin:0;'>Custom Sales CRM</h2>
            <p>Track customers, prospects, quotation values, and product opportunities in one place.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"Release: {APP_RELEASE}")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Customers", len(customers))
    col2.metric("Prospects", len(prospects))
    col3.metric("Open Pipeline", f"AED {total_pipeline:,.0f}")
    col4.metric("Won Value", f"AED {won_value:,.0f}")
    col5.metric("Win Rate", f"{conversion:.1f}%")

    left, right = st.columns([1.25, 1])

    with left:
        st.subheader("Pipeline by Status")
        status_counts = (
            pd.DataFrame(prospects)["status"].value_counts().reindex(STATUSES, fill_value=0)
            if prospects
            else pd.Series([0] * len(STATUSES), index=STATUSES)
        )
        st.bar_chart(status_counts)

    with right:
        st.subheader("Recent Quotations")
        if quotations:
            recent = pd.DataFrame(quotations).sort_values("created_date", ascending=False).head(8)
            st.dataframe(
                recent[["id", "customer_name", "product_name", "quote_value", "status", "valid_until"]],
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No quotations yet.")

    st.subheader("Upcoming Actions")
    action_df = pd.DataFrame(prospects)
    if not action_df.empty:
        action_df = action_df[action_df["status"].isin(["Contacted", "Qualified", "Proposal Sent", "Negotiation"])]
        action_df = action_df[["company_name", "contact_name", "status", "next_action", "expected_close_date"]]
        st.dataframe(action_df, width="stretch", hide_index=True)
    else:
        st.info("Add prospects to see your task queue.")


def customers_view(data: dict[str, list[dict[str, Any]]]) -> None:
    st.subheader("Customer Directory")
    customers = data["customers"]

    if customers:
        customer_df = pd.DataFrame(customers)
        edited = st.data_editor(customer_df, width="stretch", hide_index=True, num_rows="dynamic")
        if st.button("Save Customer Edits", width="stretch"):
            data["customers"] = edited.fillna("").to_dict("records")
            save_data(data)
            st.success("Customer records updated.")
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
                    save_data(data)
                    st.success(f"Customer {company} added.")


def prospects_view(data: dict[str, list[dict[str, Any]]]) -> None:
    st.subheader("Prospect Tracker")
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
        st.dataframe(p_df, width="stretch", hide_index=True)
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
                        save_data(data)
                        st.success("Prospect updated.")
        else:
            st.info("Select a prospect from the dropdown to open the edit form.")

    st.markdown("### Upload Quotation PDF Files")
    render_attachment_manager(data, prospects, key_prefix="prospects")

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
                    save_data(data)
                    st.success(f"Prospect {company} added.")


def quotations_view(data: dict[str, list[dict[str, Any]]]) -> None:
    st.subheader("Quotations")
    quotes = data["quotations"]
    prospects = data["prospects"]

    if quotes:
        q_df = pd.DataFrame(quotes)
        if "quote_value" in q_df.columns:
            q_df["quote_value"] = pd.to_numeric(q_df["quote_value"], errors="coerce").fillna(0.0)
        edited_quotes = st.data_editor(q_df, width="stretch", hide_index=True, num_rows="dynamic")
        if st.button("Save Quotation Edits", width="stretch"):
            if "quote_value" in edited_quotes.columns:
                edited_quotes["quote_value"] = pd.to_numeric(edited_quotes["quote_value"], errors="coerce").fillna(0.0)
            data["quotations"] = edited_quotes.fillna("").to_dict("records")
            save_data(data)
            st.success("Quotation records updated.")
    else:
        st.info("No quotations created yet.")

    with st.expander("Generate New Quotation", expanded=False):
        with st.form("new_quote_form", clear_on_submit=True):
            lead_options = {f"{p['id']} | {p['company_name']} ({p['status']})": p for p in prospects}
            selected_label = st.selectbox("Prospect", list(lead_options.keys()) if lead_options else ["No prospects available"])
            selected_lead = lead_options.get(selected_label)

            c1, c2, c3 = st.columns(3)
            product = c1.text_input("Product Name*")
            value = c2.number_input("Quotation Value", min_value=0.0, step=1000.0)
            currency = c3.selectbox("Currency", ["AED", "USD", "EUR", "GBP"])

            d1, d2 = st.columns(2)
            quote_status = d1.selectbox("Quote Status", QUOTE_STATUSES)
            valid_until = d2.date_input("Valid Until", value=date.today())

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
                    }
                    data["quotations"].append(new_quote)

                    for p in data["prospects"]:
                        if p["id"] == selected_lead["id"] and p["status"] in {"New Lead", "Contacted", "Qualified"}:
                            p["status"] = "Proposal Sent"
                            p["updated_at"] = now_stamp()
                            if not p.get("connected_at"):
                                p["connected_at"] = today_iso()

                    save_data(data)
                    st.success(f"Quotation created for {selected_lead['company_name']}.")

    st.markdown("### Upload Existing Quotation PDFs")
    st.caption("Use this when you already generated quotation PDFs and want to attach them to a lead.")
    render_attachment_manager(data, prospects, key_prefix="quotations")


def pipeline_view(data: dict[str, list[dict[str, Any]]]) -> None:
    st.subheader("Dynamic Sales Pipeline")
    st.caption("Move opportunities between stages and track quote/product/value context.")

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
                break
        save_data(data)
        st.success(f"{selected_lead['company_name']} moved to {new_stage}.")

    cols = st.columns(len(STATUSES))
    for idx, status in enumerate(STATUSES):
        with cols[idx]:
            st.markdown(f"### {status}")
            status_items = [p for p in prospects if p["status"] == status]
            if not status_items:
                st.caption("No records")

            for lead in status_items:
                quote = quotes_map.get(lead["id"])
                quote_line = (
                    f"Quote: {quote.get('currency', 'AED')} {float(quote.get('quote_value', 0)):,.0f} | {quote.get('product_name', '')}"
                    if quote
                    else "Quote: Not generated"
                )

                st.markdown(
                    f"""
                    <div class='pipeline-card'>
                        <div class='pipeline-title'>{lead['company_name']}</div>
                        <div>{lead['contact_name']}</div>
                        <div class='mono'>{lead['id']} | Est. AED {float(lead.get('estimated_value', 0)):,.0f}</div>
                        <div class='mono'>{quote_line}</div>
                        <div class='mono'>Product: {lead.get('product_interest', '')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def insights_view(data: dict[str, list[dict[str, Any]]]) -> None:
    st.subheader("Revenue and Product Insights")
    prospects = pd.DataFrame(data["prospects"])
    quotes = pd.DataFrame(data["quotations"])

    if not prospects.empty:
        st.write("Pipeline value by product interest")
        product_value = prospects.groupby("product_interest", dropna=False)["estimated_value"].sum().sort_values(ascending=False)
        st.bar_chart(product_value)
    else:
        st.info("Prospects required for insights.")

    if not quotes.empty:
        st.write("Quotation value by quote status")
        quote_status = quotes.groupby("status", dropna=False)["quote_value"].sum().sort_values(ascending=False)
        st.bar_chart(quote_status)
    else:
        st.info("Quotations required for quote insights.")


def render_period_report(data: dict[str, Any], start: date, end: date, label: str) -> None:
    prospects = data["prospects"]
    quotations = data["quotations"]

    connected = [p for p in prospects if date_in_range(p.get("connected_at", ""), start, end)]
    proposals = [q for q in quotations if date_in_range(q.get("created_date", ""), start, end)]
    connected_df = pd.DataFrame(connected)
    proposals_df = pd.DataFrame(proposals)

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

    m1, m2, m3 = st.columns(3)
    m1.metric(f"Leads Connected ({label})", len(connected))
    m2.metric(f"Proposals Shared ({label})", len(proposals))
    m3.metric(
        f"Proposal Value ({label})",
        f"AED {sum(float(x.get('quote_value', 0) or 0) for x in proposals):,.0f}",
    )

    st.markdown("#### Leads Connected")
    if connected_df.empty:
        st.info("No connected leads in this period.")
    else:
        connected_view = connected_df[
            ["id", "company_name", "contact_name", "status", "connected_at", "next_action", "estimated_value"]
        ]
        st.dataframe(connected_view, width="stretch", hide_index=True)
        st.download_button(
            "Download Connected Leads CSV",
            data=csv_bytes(connected_view),
            file_name=f"connected_leads_{label.lower()}.csv",
            mime="text/csv",
        )

    st.markdown("#### Proposals Shared")
    if proposals_df.empty:
        st.info("No proposals shared in this period.")
    else:
        proposal_view = proposals_df[
            ["id", "prospect_id", "customer_name", "product_name", "quote_value", "status", "created_date"]
        ]
        st.dataframe(proposal_view, width="stretch", hide_index=True)
        st.download_button(
            "Download Proposals CSV",
            data=csv_bytes(proposal_view),
            file_name=f"proposals_{label.lower()}.csv",
            mime="text/csv",
        )

    st.markdown("#### Next Steps for Proposal Leads")
    if next_steps_df.empty:
        st.info("No next-step records available for proposals in this period.")
    else:
        st.dataframe(next_steps_df, width="stretch", hide_index=True)
        st.download_button(
            "Download Next Steps CSV",
            data=csv_bytes(next_steps_df),
            file_name=f"proposal_next_steps_{label.lower()}.csv",
            mime="text/csv",
        )


def save_report_bundle_to_downloads(label: str, connected_df: pd.DataFrame, proposals_df: pd.DataFrame, next_steps_df: pd.DataFrame) -> list[Path]:
    report_dir = DOWNLOADS_DIR / "crm_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    connected_path = report_dir / f"{label}_connected_leads_{stamp}.csv"
    proposals_path = report_dir / f"{label}_proposals_shared_{stamp}.csv"
    next_steps_path = report_dir / f"{label}_next_steps_{stamp}.csv"

    connected_df.to_csv(connected_path, index=False)
    proposals_df.to_csv(proposals_path, index=False)
    next_steps_df.to_csv(next_steps_path, index=False)

    return [connected_path, proposals_path, next_steps_path]


def period_frames(data: dict[str, Any], start: date, end: date) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prospects = data["prospects"]
    quotations = data["quotations"]

    connected = [p for p in prospects if date_in_range(p.get("connected_at", ""), start, end)]
    proposals = [q for q in quotations if date_in_range(q.get("created_date", ""), start, end)]
    connected_df = pd.DataFrame(connected)
    proposals_df = pd.DataFrame(proposals)

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

    return connected_view, proposal_view, next_steps_df


def reports_view(data: dict[str, Any]) -> None:
    st.subheader("Weekly and Monthly Reports")
    st.caption("Dynamic reports for connected leads, proposals shared, and next actions.")

    current_day = date.today()
    week_start = current_day - timedelta(days=current_day.weekday())
    week_end = week_start + timedelta(days=6)

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
    active_week_end = active_week_start + timedelta(days=6)
    month_start = date(current_day.year, selected_month, 1)
    month_end = date(current_day.year, selected_month, calendar.monthrange(current_day.year, selected_month)[1])

    wtab, mtab = st.tabs(["Weekly", "Monthly"])

    with wtab:
        st.write(f"Period: {active_week_start} to {active_week_end}")
        render_period_report(data, active_week_start, active_week_end, "weekly")
        weekly_connected, weekly_proposals, weekly_next_steps = period_frames(data, active_week_start, active_week_end)
        st.caption("Click to save weekly report files directly to your local Downloads/crm_reports folder (local run only).")
        if st.button("Save Weekly Report Files to Downloads", width="stretch"):
            try:
                files = save_report_bundle_to_downloads("weekly", weekly_connected, weekly_proposals, weekly_next_steps)
                st.success("Saved weekly report files:")
                for path in files:
                    st.write(str(path))
            except Exception as exc:
                st.error(f"Could not save report files: {exc}")

    with mtab:
        st.write(f"Period: {month_start} to {month_end}")
        render_period_report(data, month_start, month_end, "monthly")
        monthly_connected, monthly_proposals, monthly_next_steps = period_frames(data, month_start, month_end)
        st.caption("Click to save monthly report files directly to your local Downloads/crm_reports folder (local run only).")
        if st.button("Save Monthly Report Files to Downloads", width="stretch"):
            try:
                files = save_report_bundle_to_downloads("monthly", monthly_connected, monthly_proposals, monthly_next_steps)
                st.success("Saved monthly report files:")
                for path in files:
                    st.write(str(path))
            except Exception as exc:
                st.error(f"Could not save report files: {exc}")


def main() -> None:
    style_app()
    data = load_data()
    if ensure_schema(data):
        save_data(data)

    with st.sidebar:
        st.title("Sales Workspace")
        section = st.radio(
            "Go to",
            ["Dashboard", "Customers", "Prospects", "Pipeline", "Quotations", "Insights", "Reports"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        if st.button("Reset to Sample Data", width="stretch"):
            save_data(SAMPLE_DATA)
            st.success("Sample CRM data restored.")

    if section == "Dashboard":
        dashboard(data)
    elif section == "Customers":
        customers_view(data)
    elif section == "Prospects":
        prospects_view(data)
    elif section == "Pipeline":
        pipeline_view(data)
    elif section == "Quotations":
        quotations_view(data)
    elif section == "Insights":
        insights_view(data)
    elif section == "Reports":
        reports_view(data)


if __name__ == "__main__":
    main()
