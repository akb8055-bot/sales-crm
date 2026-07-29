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

Data is stored locally in `crm_data.json` and auto-created on first launch.
