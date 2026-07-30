# Custom Sales CRM

A dynamic Streamlit-based CRM tailored for tracking:

- Full customer details
- Potential prospects and stage status
- Quotation generation status
- Product name and quotation value per opportunity
- Pipeline and insights dashboards

## Run

```bash
cd /Users/aadi/sales-crm
/opt/homebrew/bin/python3 -m streamlit run app.py
```

## What Is Included

- `Dashboard`: KPIs, pipeline chart, and upcoming actions
- `Customers`: full account details with inline editing
- `Prospects`: lead/opportunity list including latest quotation context
- `Pipeline`: dynamic stage management in a board-style layout
- `Quotations`: create and maintain quotes by product and value
- `Insights`: revenue views by product and quote status

Data is stored in Supabase when credentials are configured, with local `crm_data.json` fallback for development.

## Permanent Cloud Data Setup (Supabase)

1. Create a Supabase project.
2. In Supabase SQL Editor, run the script in `supabase_schema.sql`.
3. In Streamlit Community Cloud app settings, add secrets:

```toml
SUPABASE_URL = "https://<project-ref>.supabase.co"
SUPABASE_KEY = "<service-role-key>"
SUPABASE_TABLE = "crm_state"
SUPABASE_ROW_ID = "default"
```

4. Redeploy the Streamlit app.

Behavior:

- On first cloud run, if the Supabase row is empty, the app seeds it from local data.
- All future writes go to Supabase, so restarts and redeploys do not lose CRM data.
- If Supabase secrets are missing, the app continues with local JSON storage.

Last deploy trigger update: 2026-07-29
