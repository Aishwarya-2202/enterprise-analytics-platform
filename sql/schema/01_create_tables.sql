create table dim_date(
date_id SERIAL PRIMARY KEY,
full_date DATE NOT NULL UNIQUE,
day SMALLINT NOT NULL,
month SMALLINT NOT NULL,
month_name VARCHAR(20) NOT NULL,
quarter SMALLINT NOT NULL,
year SMALLINT NOT NULL,
is_weekend BOOLEAN NOT NULL DEFAULT FALSE);

create table dim_customer(
customer_id   SERIAL PRIMARY KEY,
customer_name VARCHAR(100) not null ,
email varchar(150) NOT NULL UNIQUE,
segment varchar(50),
signup_date DATE);

create table dim_product (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(150) NOT NULL,
    category varchar(80) not null,
    sub_category varchar(80),
    unit_cost numeric(10,2) not null check(unit_cost >= 0)
);


CREATE TABLE dim_store (
    store_id        SERIAL PRIMARY KEY,
    store_name      VARCHAR(100) NOT NULL,
    city            VARCHAR(80) NOT NULL,
    region          VARCHAR(80) NOT NULL,
    store_manager   VARCHAR(100)
);

CREATE TABLE fact_sales (
    sale_id         SERIAL PRIMARY KEY,
    date_id         INTEGER NOT NULL REFERENCES dim_date(date_id),
    customer_id     INTEGER NOT NULL REFERENCES dim_customer(customer_id),
    product_id      INTEGER NOT NULL REFERENCES dim_product(product_id),
    store_id        INTEGER NOT NULL REFERENCES dim_store(store_id),
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    unit_price      NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
    total_amount    NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0)
);