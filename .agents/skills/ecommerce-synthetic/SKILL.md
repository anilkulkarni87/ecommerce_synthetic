---
name: ecommerce-synthetic
description: Generate, validate, inspect, profile, and stream realistic omnichannel synthetic ecommerce datasets (Small to XL) with referential integrity across 19 Parquet tables. Use when the user requests synthetic retail data, customer 360 test datasets, fraud anomaly datasets, clickstream streaming, or ETL pipeline test fixtures.
---

# Ecommerce Synthetic Data Generator — Agent Guide

## Overview

This skill guides agents in running, validating, profiling, and querying the omnichannel synthetic ecommerce data generator. It produces 19 interconnected Parquet tables across online e-commerce, physical POS retail, loyalty programs, clickstream, email, reviews, support, A/B experiments, and fraud detection.

The complete machine-readable data dictionary is available in [config/schema.json](file:///Users/harihiom/Anil/git/Ecommerce_synthetic/config/schema.json).

---

## When to Activate This Skill

Activate this skill when the user asks to:
1. Generate synthetic or mock data for ecommerce, retail, or omnichannel businesses.
2. Build or test a **Customer 360** data pipeline, data warehouse, or CDP.
3. Test **Identity Resolution** (cookie stitching, POS phone match, email resolution).
4. Train ML models for **Fraud Detection** with realistic ground-truth labels.
5. Simulate **real-time event streaming** (Kafka, HTTP webhooks, clickstream).
6. Create incremental daily batches for **ETL/ELT pipeline testing**.

---

## Command Reference & Presets

Run commands in the terminal using the local virtual environment (`source .venv/bin/activate`):

### 1. Fast Generation (Recommended for quick testing)
Generates Small tier (500 customers, 1.5K orders, 50K clickstream events) and pre-bundles into DuckDB:
```bash
source .venv/bin/activate
ecommerce-synth generate --tier small --duckdb --output ./output/test_run
```

### 2. Available Volume Tiers
- `--tier small` (~68K total rows, ~4.5 MB, ~5 seconds)
- `--tier medium` (~6M total rows, ~400 MB, ~45 seconds)
- `--tier large` (~60M total rows, ~4 GB)
- `--tier xl` (~600M total rows, ~40 GB)

### 3. Validate Referential Integrity
Checks all 29 foreign-key relationships across all 19 tables:
```bash
ecommerce-synth validate ./output/test_run
```

### 4. Preview / Inspect Table Data
Inspect row counts, column types, and sample records directly from the CLI:
```bash
ecommerce-synth preview ./output/test_run orders_online --limit 5
ecommerce-synth preview ./output/test_run customers --limit 5
```

### 5. Profile Business Metrics & Export Dashboard
Calculates GMV, AOV by channel, cart abandonment, customer LTV, and fraud metrics:
```bash
ecommerce-synth profile ./output/test_run --html ./output/test_run/report.html
```

### 6. Incremental Pipeline Generation ("Yesterday's Data")
Appends 1 or N days of new records to an existing dataset run:
```bash
# Append 1 day of delta data
ecommerce-synth generate --incremental ./output/test_run --days 1

# Simulate a week of daily batches (creates batches/day_1, batches/day_2, ...)
ecommerce-synth generate --incremental ./output/test_run --days 7 --daily-batches
```

### 7. Real-Time Event Streaming
Sequentially stream chronologically interleaved events to stdout, JSON Lines, or a Webhook:
```bash
# Stream to stdout at 100x speed
ecommerce-synth stream ./output/test_run --speed 100 --limit 50

# Output raw NDJSON / JSON Lines
ecommerce-synth stream ./output/test_run --json --speed 0 | jq .

# POST live events to an HTTP Webhook
ecommerce-synth stream ./output/test_run --webhook http://localhost:8080/api/events
```

---

## Key Table Relationships (The 19 Tables)

```
[customers] ────────┬───(1:N)───> [addresses] (shipping & billing)
                    ├───(1:N)───> [orders_online] ──(1:N)──> [order_items_online] ──> [products]
                    ├───(1:1)───> [instore_accounts] ──(1:N)──> [orders_instore] ──> [order_items_instore] ──> [products]
                    ├───(1:N)───> [clickstream] (session_id stitches to orders_online)
                    ├───(1:N)───> [email_events] ──> [email_campaigns]
                    ├───(1:1)───> [loyalty_members] ──(1:N)──> [loyalty_transactions]
                    ├───(1:N)───> [reviews] ──> [products]
                    ├───(1:N)───> [support_tickets]
                    ├───(1:N)───> [experiment_assignments] ──> [experiments]
                    └───(1:N)───> [fraud_flags]
```

Fixed Dimension Tables:
- `products.parquet`: 2,000 SKUs (Electronics, Apparel, Home & Kitchen, Sports, Beauty, Grocery).
- `stores.parquet`: 50 physical retail stores with geo coordinates and regions.

---

## SQL Query Recipes (DuckDB / Polars)

When querying the generated `ecommerce.duckdb` file:

### Recipe 1: Unified Customer 360 View
```sql
SELECT 
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    c.email,
    c.customer_segment,
    COUNT(DISTINCT o.order_id) AS online_orders_count,
    COALESCE(SUM(o.total_amount), 0) AS online_spend,
    COUNT(DISTINCT pos.transaction_id) AS instore_orders_count,
    COALESCE(SUM(pos.total_amount), 0) AS instore_spend,
    COALESCE(SUM(o.total_amount), 0) + COALESCE(SUM(pos.total_amount), 0) AS total_lifetime_spend,
    l.tier AS loyalty_tier,
    l.points_balance
FROM customers c
LEFT JOIN orders_online o ON c.customer_id = o.customer_id
LEFT JOIN orders_instore pos ON c.customer_id = pos.customer_id
LEFT JOIN loyalty_members l ON c.customer_id = l.customer_id
GROUP BY 1, 2, 3, 4, 10, 11
ORDER BY total_lifetime_spend DESC;
```

### Recipe 2: Identity Resolution (Cross-Channel Phone Stitching)
Stitch anonymous in-store POS shoppers to registered online customer profiles:
```sql
SELECT 
    pos.transaction_id,
    pos.transaction_date,
    pos.total_amount,
    acc.phone_number,
    c.customer_id AS resolved_customer_id,
    c.email AS resolved_email,
    CASE WHEN c.customer_id IS NOT NULL THEN 'RESOLVED' ELSE 'UNMATCHED_GUEST' END AS resolution_status
FROM orders_instore pos
JOIN instore_accounts acc ON pos.instore_account_id = acc.instore_account_id
LEFT JOIN customers c ON acc.phone_number = c.phone;
```

### Recipe 3: Clickstream Conversion Funnel
```sql
SELECT 
    event_type,
    COUNT(*) AS event_count,
    COUNT(DISTINCT session_id) AS unique_sessions
FROM clickstream
GROUP BY event_type
ORDER BY event_count DESC;
```

### Recipe 4: Fraud Detection Model Evaluation
```sql
SELECT 
    fraud_type,
    COUNT(*) AS flagged_incidents,
    AVG(risk_score) AS avg_model_risk,
    SUM(CASE WHEN is_confirmed_fraud THEN 1 ELSE 0 END) AS ground_truth_positives,
    ROUND(AVG(CASE WHEN is_confirmed_fraud THEN 1.0 ELSE 0.0 END) * 100, 1) AS precision_pct
FROM fraud_flags
GROUP BY fraud_type;
```
