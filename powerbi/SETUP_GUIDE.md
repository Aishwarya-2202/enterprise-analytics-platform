# Power BI Setup Guide

## Connection

- Source: PostgreSQL, `localhost:5432`, database `enterprise_analytics`
- Mode: **Import** (not DirectQuery) -- appropriate at our current data volume
- Tables imported: `fact_sales`, `dim_date`, `dim_customer`, `dim_product`, `dim_store`
- Deliberately NOT imported: `vw_monthly_revenue`, `vw_category_performance`,
  `vw_store_performance` -- these pre-aggregate data, which would prevent
  flexible slicing in Power BI's own DAX/visual layer. The raw star schema
  is imported instead, so Power BI's relationship engine and DAX measures
  can do the joining and aggregating dynamically.

## Relationships (verify manually, don't trust auto-detect blindly)

| From (many side)     | To (one side)          | Cardinality | Filter direction |
|-----------------------|--------------------------|-------------|-------------------|
| fact_sales.date_id     | dim_date.date_id         | Many-to-one | Single            |
| fact_sales.customer_id | dim_customer.customer_id | Many-to-one | Single            |
| fact_sales.product_id  | dim_product.product_id   | Many-to-one | Single            |
| fact_sales.store_id    | dim_store.store_id       | Many-to-one | Single            |

## Refresh process

After running `python etl/pipeline.py` with new source data, refresh the
Power BI model: Home ribbon -> Refresh. This re-imports all five tables
from PostgreSQL. Import mode means the report shows stale data until this
refresh is run manually (or scheduled, once published -- see a later part
of this module).