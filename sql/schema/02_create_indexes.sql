CREATE INDEX idx_facts_sales_date_id 
on fact_sales (date_id);

create index idx_facts_sales_customer_id
on fact_sales (customer_id);

create index idx_facts_sales_product_id
on fact_sales (product_id);

create index idx_facts_sales_store_id
on fact_sales (store_id);   

