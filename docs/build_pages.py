#!/usr/bin/env python3
"""Builds docs/index.html in the Swiss Cartographic Atlas design from config/schema.json."""

import json
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
schema_file = repo_root / "config" / "schema.json"

with open(schema_file) as f:
    schema = json.load(f)

DOMAINS = {
    "orders_online": "Omnichannel Sales & POS",
    "order_items_online": "Omnichannel Sales & POS",
    "orders_instore": "Omnichannel Sales & POS",
    "order_items_instore": "Omnichannel Sales & POS",
    "stores": "Omnichannel Sales & POS",
    "products": "Omnichannel Sales & POS",
    "shipments": "Omnichannel Sales & POS",
    "returns": "Omnichannel Sales & POS",
    "inventory_snapshots": "Omnichannel Sales & POS",
    "customers": "Customer 360 & Identity",
    "addresses": "Customer 360 & Identity",
    "instore_accounts": "Customer 360 & Identity",
    "loyalty_members": "Customer 360 & Identity",
    "clickstream": "Engagement & Retention",
    "email_campaigns": "Engagement & Retention",
    "email_events": "Engagement & Retention",
    "loyalty_transactions": "Engagement & Retention",
    "reviews": "Engagement & Retention",
    "support_tickets": "Engagement & Retention",
    "experiments": "Experimentation & Fraud",
    "experiment_assignments": "Experimentation & Fraud",
    "fraud_flags": "Experimentation & Fraud",
    "customer_consents": "Governance & Compliance",
    "identity_ground_truth": "Governance & Compliance",
}

all_tables = {}
for tname, tinfo in schema.get("tables", {}).items():
    tinfo["domain"] = DOMAINS.get(tname, "Core")
    tinfo["is_optional"] = False
    all_tables[tname] = tinfo

for tname, tinfo in schema.get("optional_tables", {}).items():
    tinfo["domain"] = DOMAINS.get(tname, "Governance & Compliance")
    tinfo["is_optional"] = True
    all_tables[tname] = tinfo

schema_payload = {
    "version": schema.get("version", "1.1.0"),
    "tables": all_tables,
}
schema_json_str = json.dumps(schema_payload, indent=2)

html_template = '''<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ecommerce-synth — Omnichannel Synthetic Data Atlas</title>
  <meta name="description" content="Referentially-intact omnichannel synthetic ecommerce data generator for Parquet, DuckDB, Databricks Unity Catalog, Snowflake, and BigQuery.">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Source+Sans+3:wght@400;500;600;700&display=swap" rel="stylesheet">

  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          fontFamily: {
            sans: ['"Source Sans 3"', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
          },
          colors: {
            paper: '#FAF8F4',
            plate: '#FFFFFF',
            vellum: '#F3EFE6',
            hairline: '#DFD9CE',
            ink: '#0F172A',
            muted: '#475569',
            cobalt: '#1D4ED8',
            amberroute: '#B45309',
            tealroute: '#0F766E',
            crimson: '#BE123C',
          }
        }
      }
    }
  </script>

  <style>
    :root { color-scheme: light; }
    ::selection { background: #1D4ED8; color: #FFFFFF; }
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: #FAF8F4; }
    ::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #94A3B8; }
    :focus-visible { outline: 2px solid #1D4ED8; outline-offset: 2px; }
    .tabular-nums { font-variant-numeric: tabular-nums; }
    h1 { font-size: 2.75rem; line-height: 1.08; letter-spacing: -0.025em; }
    h2 { font-size: 1.75rem; line-height: 1.2; letter-spacing: -0.02em; }
    h3 { font-size: 1.05rem; line-height: 1.35; }
    .atlas-grid {
      background-image:
        linear-gradient(to right, rgba(223, 217, 206, 0.45) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(223, 217, 206, 0.45) 1px, transparent 1px);
      background-size: 28px 28px;
    }
  </style>
</head>
<body class="bg-paper text-ink font-sans antialiased">

  <!-- Top Masthead -->
  <header class="sticky top-0 z-50 bg-paper/95 backdrop-blur border-b border-hairline">
    <div class="max-w-[1380px] mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <a href="#" class="flex items-center gap-2.5 text-ink hover:text-cobalt transition">
          <svg class="w-5 h-5 text-cobalt" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z"/>
          </svg>
          <span class="font-semibold text-sm font-mono tracking-tight">ecommerce-synth</span>
        </a>
        <span class="hidden sm:inline-block text-[11px] font-mono px-2 py-0.5 bg-vellum text-muted border border-hairline">v1.1.0 · 24 Tables</span>
      </div>

      <nav class="hidden md:flex lg:hidden items-center gap-5 text-xs font-medium text-muted">
        <a href="#features" class="hover:text-ink transition">Capabilities</a>
        <a href="#tiers" class="hover:text-ink transition">Scale &amp; CLI</a>
        <a href="#schema" class="hover:text-ink transition">Schema</a>
        <a href="#warehouses" class="hover:text-ink transition">Warehouses</a>
        <a href="#recipes" class="hover:text-ink transition">SQL</a>
      </nav>

      <div class="flex items-center gap-3">
        <a href="#schema" class="hidden sm:inline-flex items-center px-3 py-1.5 text-xs font-medium bg-cobalt text-white hover:bg-blue-800 transition">
          24-Table Dictionary
        </a>
        <a href="https://github.com/anilkulkarni87/ecommerce_synthetic" target="_blank" rel="noopener noreferrer"
           class="inline-flex items-center gap-2 px-3 py-1.5 bg-plate hover:bg-vellum border border-hairline text-xs font-medium text-ink transition">
          <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24">
            <path fill-rule="evenodd" clip-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
          </svg>
          <span>GitHub</span>
        </a>
      </div>
    </div>
  </header>

  <!-- Main Atlas Frame: Sticky Left Rail + Reading Column -->
  <div class="max-w-[1380px] mx-auto px-4 sm:px-6 lg:px-8 flex gap-10">

    <!-- Left Wayfinding Rail -->
    <aside class="hidden lg:block w-52 shrink-0 py-10">
      <div class="sticky top-24 space-y-6">
        <div>
          <div class="text-[11px] font-mono uppercase tracking-wider text-muted mb-3">Atlas Index</div>
          <nav class="space-y-1 text-sm border-l border-hairline">
            <a href="#overview" class="block pl-3.5 py-1 text-ink font-medium border-l-2 border-cobalt -ml-[1px] hover:text-cobalt transition">Overview &amp; Map</a>
            <a href="#features" class="block pl-3.5 py-1 text-muted hover:text-ink transition">Capabilities</a>
            <a href="#tiers" class="block pl-3.5 py-1 text-muted hover:text-ink transition">Scale &amp; CLI</a>
            <a href="#schema" class="block pl-3.5 py-1 text-muted hover:text-ink transition">Schema (24)</a>
            <a href="#warehouses" class="block pl-3.5 py-1 text-muted hover:text-ink transition">Warehouses</a>
            <a href="#recipes" class="block pl-3.5 py-1 text-muted hover:text-ink transition">SQL Recipes</a>
            <a href="#personas" class="block pl-3.5 py-1 text-muted hover:text-ink transition">Personas</a>
            <a href="#quickstart" class="block pl-3.5 py-1 text-muted hover:text-ink transition">Quickstart</a>
          </nav>
        </div>

        <div class="pt-5 border-t border-hairline space-y-2 text-xs">
          <div class="font-mono text-[11px] uppercase tracking-wider text-muted">Route Legend</div>
          <div class="flex items-center gap-2 text-ink"><span class="w-3 h-0.5 bg-cobalt inline-block"></span><span>Digital FK</span></div>
          <div class="flex items-center gap-2 text-ink"><span class="w-3 h-0.5 border-t-2 border-dashed border-amberroute inline-block"></span><span>POS Stitching</span></div>
          <div class="flex items-center gap-2 text-ink"><span class="w-3 h-0.5 bg-tealroute inline-block"></span><span>Fulfillment / Web</span></div>
        </div>
      </div>
    </aside>

    <!-- Primary Reading Column -->
    <main class="flex-1 min-w-0">

      <!-- Overview & First-Viewport Atlas Plate (#overview) -->
      <section id="overview" class="py-10 sm:py-14 border-b border-hairline">
        <div class="grid grid-cols-1 xl:grid-cols-12 gap-8 items-start">
          <div class="xl:col-span-6">
            <h1 class="font-bold text-ink mb-4">
              Omnichannel retail data, mapped to real-world identity.
            </h1>
            <p class="text-base text-muted leading-relaxed max-w-[62ch] mb-6">
              Deterministic synthetic datasets across 22 core tables and 2 optional governance/ER tables. Digital checkouts, decoupled retail POS (<code class="font-mono text-xs bg-vellum px-1.5 py-0.5 text-ink">customer_id = NULL</code>), BOPIS/BORIS fulfillment, and persistent clickstream <code class="font-mono text-xs bg-vellum px-1.5 py-0.5 text-ink">anonymous_id</code> cookies stream straight into DuckDB, Snowflake, Databricks UC, or BigQuery.
            </p>

            <div class="flex flex-wrap items-center gap-3 mb-8">
              <a href="#schema" class="px-5 py-2.5 bg-cobalt hover:bg-blue-800 text-white text-sm font-medium transition">
                Explore 24-Table Schema
              </a>
              <a href="#tiers" class="px-5 py-2.5 bg-plate hover:bg-vellum text-ink text-sm font-medium border border-hairline transition">
                Compose CLI Command
              </a>
            </div>

            <dl class="grid grid-cols-2 sm:grid-cols-4 gap-5 pt-5 border-t border-hairline">
              <div>
                <dt class="text-xs text-muted">Schema</dt>
                <dd class="text-base font-semibold text-ink tabular-nums mt-0.5">22 + 2 Tables</dd>
              </div>
              <div>
                <dt class="text-xs text-muted">Integrity</dt>
                <dd class="text-base font-semibold text-tealroute tabular-nums mt-0.5">29 FK Checks</dd>
              </div>
              <div>
                <dt class="text-xs text-muted">Destinations</dt>
                <dd class="text-base font-semibold text-ink tabular-nums mt-0.5">4 Warehouses</dd>
              </div>
              <div>
                <dt class="text-xs text-muted">Max Scale</dt>
                <dd class="text-base font-semibold text-cobalt tabular-nums mt-0.5">500M+ Rows</dd>
              </div>
            </dl>
          </div>

          <!-- CLI Preview Plate (Flat, No Nested Cards) -->
          <div class="xl:col-span-6 bg-plate border border-hairline">
            <div class="bg-vellum px-4 py-2.5 border-b border-hairline flex items-center justify-between gap-2">
              <span class="text-xs font-mono text-muted">cli-preview</span>
              <div class="flex items-center gap-1 text-xs font-mono">
                <button onclick="switchTerminalTab('stream')" id="term-tab-stream" class="px-2.5 py-1 bg-cobalt text-white font-medium transition">Stream</button>
                <button onclick="switchTerminalTab('generate')" id="term-tab-generate" class="px-2.5 py-1 text-muted hover:text-ink transition">Chunked</button>
                <button onclick="switchTerminalTab('compliance')" id="term-tab-compliance" class="px-2.5 py-1 text-muted hover:text-ink transition">Global</button>
                <button onclick="switchTerminalTab('validate')" id="term-tab-validate" class="px-2.5 py-1 text-muted hover:text-ink transition">Validate</button>
              </div>
            </div>

            <div class="p-5 font-mono text-xs text-ink leading-relaxed overflow-x-auto min-h-[270px]">
              <div id="term-content-stream">
                <div class="flex items-center justify-between gap-2 pb-3 mb-3 border-b border-hairline">
                  <span class="text-cobalt font-medium">$ ecommerce-synth generate --tier large --stream-to snowflake --database ECOM_DB --schema PROD</span>
                  <button onclick="copyCommand('ecommerce-synth generate --tier large --stream-to snowflake --database ECOM_DB --schema PROD')" class="text-muted hover:text-ink px-2 py-0.5 border border-hairline bg-paper shrink-0">Copy</button>
                </div>
                <p class="text-muted">Streaming directly to Snowflake: ECOM_DB.PROD (0 local Parquet files)</p>
                <p class="text-tealroute mt-2">  ✓ Streamed customers: 500,000 rows</p>
                <p class="text-tealroute">  ✓ Streamed instore_accounts: 210,000 rows (decoupled POS)</p>
                <p class="text-tealroute">  ✓ Streamed orders_online: 1,000,000 rows (18% BOPIS, 15% guest)</p>
                <p class="text-tealroute">  ✓ Streamed clickstream: 50,000,000 rows (100 chunks)</p>
                <p class="text-muted mt-2">Applying 31 PII/financial governance tags &amp; stitched v_customer_360...</p>
                <p class="text-ink font-semibold mt-2">Direct Snowflake stream complete: 22 tables, 60.4M rows.</p>
              </div>

              <div id="term-content-generate" class="hidden">
                <div class="flex items-center justify-between gap-2 pb-3 mb-3 border-b border-hairline">
                  <span class="text-cobalt font-medium">$ ecommerce-synth generate --tier large --chunk-size 500000 --output ./output/large/</span>
                  <button onclick="copyCommand('ecommerce-synth generate --tier large --chunk-size 500000 --output ./output/large/')" class="text-muted hover:text-ink px-2 py-0.5 border border-hairline bg-paper shrink-0">Copy</button>
                </div>
                <p class="text-muted">Generation Configuration [Tier: LARGE | Chunk Size: 500,000 rows]</p>
                <p class="text-tealroute mt-2">  ✓ customers.parquet: 500,000 rows, 41.2 MB</p>
                <p class="text-tealroute">  ✓ orders_online/ (2 chunks): 1,000,000 rows, 74.8 MB</p>
                <p class="text-tealroute">  ✓ clickstream/ (100 chunks): 50,000,000 rows, 1.48 GB</p>
                <p class="text-muted mt-2">Constant bounded RAM via ChunkedParquetWriter.</p>
              </div>

              <div id="term-content-compliance" class="hidden">
                <div class="flex items-center justify-between gap-2 pb-3 mb-3 border-b border-hairline">
                  <span class="text-cobalt font-medium">$ ecommerce-synth generate --tier medium --regions US,GB,DE,JP --compliance --identity-noise 0.15</span>
                  <button onclick="copyCommand('ecommerce-synth generate --tier medium --regions US,GB,DE,JP --compliance --identity-noise 0.15')" class="text-muted hover:text-ink px-2 py-0.5 border border-hairline bg-paper shrink-0">Copy</button>
                </div>
                <p class="text-muted">Regions: US, GB, DE, JP | Identity Noise: 15.0% | Compliance: GDPR/CCPA/APPI</p>
                <p class="text-tealroute mt-2">  ✓ customers.parquet: 50,000 rows (localized Faker + 2% DSAR tombstones)</p>
                <p class="text-tealroute">  ✓ customer_consents.parquet: 150,000 consent records</p>
                <p class="text-tealroute">  ✓ identity_ground_truth.parquet: digital + POS cross-channel mappings</p>
              </div>

              <div id="term-content-validate" class="hidden">
                <div class="flex items-center justify-between gap-2 pb-3 mb-3 border-b border-hairline">
                  <span class="text-cobalt font-medium">$ ecommerce-synth validate ./output/medium/</span>
                  <button onclick="copyCommand('ecommerce-synth validate ./output/medium/')" class="text-muted hover:text-ink px-2 py-0.5 border border-hairline bg-paper shrink-0">Copy</button>
                </div>
                <p class="text-muted">Validating referential integrity across single &amp; chunked Parquet tables...</p>
                <p class="text-tealroute mt-2">  ✓ addresses.customer_id -> customers.customer_id (0 orphans)</p>
                <p class="text-tealroute">  ✓ orders_online.session_id -> clickstream.session_id (100% linked)</p>
                <p class="text-tealroute">  ✓ orders_instore.instore_account_id -> instore_accounts (decoupled POS)</p>
                <p class="text-ink font-semibold mt-2">All 29 referential integrity checks passed.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Capabilities Grid (#features) -->
      <section id="features" class="py-14 border-b border-hairline">
        <div class="max-w-2xl mb-8">
          <h2 class="font-bold text-ink mb-2">Engineered for decoupled POS, global scale, and governance</h2>
          <p class="text-sm sm:text-base text-muted">Deterministic by seed, executed in Polars, and structured around real-world retail boundaries.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 border border-hairline bg-plate">
          <div class="p-6 border-b border-hairline md:border-r">
            <div class="flex items-center justify-between gap-3 mb-2">
              <h3 class="font-semibold text-ink">Decoupled Retail POS</h3>
              <code class="text-[11px] font-mono text-amberroute bg-vellum px-2 py-0.5">instore_accounts</code>
            </div>
            <p class="text-sm text-muted leading-relaxed">
              POS registers capture <code class="font-mono text-xs text-ink">phone_number</code>, <code class="font-mono text-xs text-ink">email</code>, or both with <code class="font-mono text-xs text-ink">customer_id = NULL</code>, alongside active POS-only shoppers, anonymous walk-ins, and <code class="font-mono text-xs text-ink">payment_token</code> card fingerprints.
            </p>
          </div>

          <div class="p-6 border-b border-hairline">
            <div class="flex items-center justify-between gap-3 mb-2">
              <h3 class="font-semibold text-ink">Omnichannel BOPIS &amp; BORIS</h3>
              <code class="text-[11px] font-mono text-tealroute bg-vellum px-2 py-0.5">fulfillment_type</code>
            </div>
            <p class="text-sm text-muted leading-relaxed">
              Models ~18% Buy Online, Pick Up In Store (<code class="font-mono text-xs text-ink">pickup_store_id</code>, free pickup, no carrier shipment) and ~35% Buy Online, Return In Store (<code class="font-mono text-xs text-ink">return_channel</code>, <code class="font-mono text-xs text-ink">return_store_id</code>).
            </p>
          </div>

          <div class="p-6 border-b border-hairline md:border-r">
            <div class="flex items-center justify-between gap-3 mb-2">
              <h3 class="font-semibold text-ink">Cross-Channel Entity Resolution</h3>
              <code class="text-[11px] font-mono text-amberroute bg-vellum px-2 py-0.5">--identity-noise</code>
            </div>
            <p class="text-sm text-muted leading-relaxed">
              Injects duplicate profiles, temporal PII drift, and 5% household sharing across <code class="font-mono text-xs text-ink">customers</code> and <code class="font-mono text-xs text-ink">instore_accounts</code>, emitting cross-channel <code class="font-mono text-xs text-ink">identity_ground_truth.parquet</code>.
            </p>
          </div>

          <div class="p-6 border-b border-hairline">
            <div class="flex items-center justify-between gap-3 mb-2">
              <h3 class="font-semibold text-ink">Clickstream &amp; Guest Checkout</h3>
              <code class="text-[11px] font-mono text-cobalt bg-vellum px-2 py-0.5">anonymous_id</code>
            </div>
            <p class="text-sm text-muted leading-relaxed">
              100% of <code class="font-mono text-xs text-ink">orders_online.session_id</code> values link to purchase funnels, ~15% are guest checkouts (<code class="font-mono text-xs text-ink">guest_email</code>), and persistent <code class="font-mono text-xs text-ink">anonymous_id</code> cookies model pre-login browsing.
            </p>
          </div>

          <div class="p-6 border-b border-hairline md:border-r">
            <div class="flex items-center justify-between gap-3 mb-2">
              <h3 class="font-semibold text-ink">Global Multi-Region Localization</h3>
              <code class="text-[11px] font-mono text-cobalt bg-vellum px-2 py-0.5">--regions global</code>
            </div>
            <p class="text-sm text-muted leading-relaxed">
              Country packs (<code class="font-mono text-xs text-ink">US, GB, DE, FR, CA, JP, AU, BR</code>) localize customers, physical <code class="font-mono text-xs text-ink">stores.country</code>, currencies, FX rates, and VAT vs. sales-tax calculation.
            </p>
          </div>

          <div class="p-6 border-b border-hairline">
            <div class="flex items-center justify-between gap-3 mb-2">
              <h3 class="font-semibold text-ink">GDPR / CCPA Consent &amp; PII Tags</h3>
              <code class="text-[11px] font-mono text-crimson bg-vellum px-2 py-0.5">--compliance</code>
            </div>
            <p class="text-sm text-muted leading-relaxed">
              Emits <code class="font-mono text-xs text-ink">customer_consents.parquet</code> plus 2% DSAR erasure tombstones and compiles 31 <code class="font-mono text-xs text-ink">DIRECT_PII</code>, <code class="font-mono text-xs text-ink">INDIRECT_PII</code>, and <code class="font-mono text-xs text-ink">FINANCIAL</code> column tags into Snowflake &amp; Databricks DDL.
            </p>
          </div>

          <div class="p-6 border-b md:border-b-0 border-hairline md:border-r">
            <div class="flex items-center justify-between gap-3 mb-2">
              <h3 class="font-semibold text-ink">Direct-to-Database Streaming</h3>
              <code class="text-[11px] font-mono text-tealroute bg-vellum px-2 py-0.5">--stream-to</code>
            </div>
            <p class="text-sm text-muted leading-relaxed">
              Stream Polars chunks directly into DuckDB, Snowflake (<code class="font-mono text-xs text-ink">write_pandas</code>), Databricks UC Volumes, or BigQuery (<code class="font-mono text-xs text-ink">LoadJob</code>) with zero local Parquet files.
            </p>
          </div>

          <div class="p-6">
            <div class="flex items-center justify-between gap-3 mb-2">
              <h3 class="font-semibold text-ink">50M+ Chunked Parquet Persistence</h3>
              <code class="text-[11px] font-mono text-cobalt bg-vellum px-2 py-0.5">--chunk-size</code>
            </div>
            <p class="text-sm text-muted leading-relaxed">
              Streaming <code class="font-mono text-xs text-ink">ChunkedParquetWriter</code> flushes <code class="font-mono text-xs text-ink">table/part-00000.parquet</code> partitions every N rows (default 500K) to keep memory bounded on Large and XL runs.
            </p>
          </div>
        </div>
      </section>

      <!-- Volume Tiers & CLI Builder (#tiers) -->
      <section id="tiers" class="py-14 border-b border-hairline">
        <div class="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
          <div>
            <h2 class="font-bold text-ink mb-2">Volume Tiers &amp; CLI Builder</h2>
            <p class="text-sm text-muted">Inspect row counts per tier and compose a ready-to-run generation command.</p>
          </div>

          <div class="inline-flex border border-hairline bg-plate">
            <button onclick="selectTier('small')" id="tier-btn-small" class="px-4 py-1.5 text-xs font-medium text-muted hover:text-ink transition">Small</button>
            <button onclick="selectTier('medium')" id="tier-btn-medium" class="px-4 py-1.5 text-xs font-medium bg-cobalt text-white transition">Medium</button>
            <button onclick="selectTier('large')" id="tier-btn-large" class="px-4 py-1.5 text-xs font-medium text-muted hover:text-ink transition">Large</button>
            <button onclick="selectTier('xl')" id="tier-btn-xl" class="px-4 py-1.5 text-xs font-medium text-muted hover:text-ink transition">XL</button>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div class="lg:col-span-7 bg-plate border border-hairline overflow-hidden">
            <table class="w-full text-left border-collapse text-sm">
              <thead>
                <tr class="border-b border-hairline bg-vellum text-xs font-medium text-muted">
                  <th class="py-3 px-4">Domain Entity</th>
                  <th class="py-3 px-4 text-right">Target Volume</th>
                  <th class="py-3 px-4 text-right hidden sm:table-cell">Notes</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-hairline tabular-nums">
                <tr><td class="py-2.5 px-4 text-ink">Customers</td><td id="stat-customers" class="py-2.5 px-4 text-right font-mono text-ink">50,000</td><td class="py-2.5 px-4 text-right text-xs text-muted hidden sm:table-cell">7 behavioral personas</td></tr>
                <tr><td class="py-2.5 px-4 text-ink">Online Orders</td><td id="stat-online-orders" class="py-2.5 px-4 text-right font-mono text-ink">100,000</td><td class="py-2.5 px-4 text-right text-xs text-muted hidden sm:table-cell">18% BOPIS, 15% guest</td></tr>
                <tr><td class="py-2.5 px-4 text-ink">In-Store POS Txns</td><td id="stat-store-txns" class="py-2.5 px-4 text-right font-mono text-ink">40,000</td><td class="py-2.5 px-4 text-right text-xs text-muted hidden sm:table-cell">50 store locations</td></tr>
                <tr><td class="py-2.5 px-4 text-ink">Clickstream Events</td><td id="stat-clickstream" class="py-2.5 px-4 text-right font-mono text-cobalt font-medium">5,000,000</td><td class="py-2.5 px-4 text-right text-xs text-muted hidden sm:table-cell">Auto-chunked above 500K</td></tr>
                <tr><td class="py-2.5 px-4 text-ink">Emails Delivered</td><td id="stat-emails" class="py-2.5 px-4 text-right font-mono text-ink">500,000</td><td class="py-2.5 px-4 text-right text-xs text-muted hidden sm:table-cell">Open, click, bounce events</td></tr>
                <tr><td class="py-2.5 px-4 text-ink">Loyalty Members</td><td id="stat-loyalty" class="py-2.5 px-4 text-right font-mono text-ink">30,000</td><td class="py-2.5 px-4 text-right text-xs text-muted hidden sm:table-cell">Bronze to Platinum</td></tr>
                <tr><td class="py-2.5 px-4 text-ink">Support Tickets</td><td id="stat-support" class="py-2.5 px-4 text-right font-mono text-ink">12,000</td><td class="py-2.5 px-4 text-right text-xs text-muted hidden sm:table-cell">CSAT &amp; SLA timestamps</td></tr>
                <tr class="bg-vellum/60"><td class="py-2.5 px-4 font-semibold text-ink">Estimated Parquet Size</td><td id="stat-size" class="py-2.5 px-4 text-right font-mono text-tealroute font-semibold">~350 MB</td><td class="py-2.5 px-4 text-right text-xs text-muted hidden sm:table-cell">Snappy compressed</td></tr>
              </tbody>
            </table>
          </div>

          <div class="lg:col-span-5 bg-plate border border-hairline p-6 flex flex-col justify-between">
            <div class="space-y-4">
              <h3 class="font-semibold text-ink">Compose Generation Command</h3>

              <div class="relative">
                <label class="block text-xs text-muted mb-1.5">Persistence / Delivery Mode</label>
                <button type="button" id="cmd-mode-btn" onclick="toggleModeMenu()"
                        class="w-full flex items-center justify-between text-xs bg-paper border border-hairline hover:border-slate-400 px-3 py-2 text-ink transition">
                  <span id="cmd-mode-label">Local Parquet (Chunked if &gt; 500K rows)</span>
                  <svg class="w-4 h-4 text-muted shrink-0" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5"/></svg>
                </button>
                <div id="cmd-mode-menu" class="hidden absolute z-30 mt-1 w-full bg-plate border border-hairline shadow-lg py-1 text-xs">
                  <button type="button" onclick="selectCmdMode('parquet', 'Local Parquet (Chunked if > 500K rows)')" class="w-full text-left px-3 py-2 text-ink hover:bg-cobalt hover:text-white transition">Local Parquet (Chunked if &gt; 500K rows)</button>
                  <button type="button" onclick="selectCmdMode('stream-duckdb', 'Direct Stream -> DuckDB (0 local files)')" class="w-full text-left px-3 py-2 text-ink hover:bg-cobalt hover:text-white transition">Direct Stream -&gt; DuckDB (0 local files)</button>
                  <button type="button" onclick="selectCmdMode('stream-snowflake', 'Direct Stream -> Snowflake (0 local files)')" class="w-full text-left px-3 py-2 text-ink hover:bg-cobalt hover:text-white transition">Direct Stream -&gt; Snowflake (0 local files)</button>
                  <button type="button" onclick="selectCmdMode('stream-databricks', 'Direct Stream -> Databricks UC (0 local files)')" class="w-full text-left px-3 py-2 text-ink hover:bg-cobalt hover:text-white transition">Direct Stream -&gt; Databricks UC (0 local files)</button>
                  <button type="button" onclick="selectCmdMode('stream-bigquery', 'Direct Stream -> BigQuery (0 local files)')" class="w-full text-left px-3 py-2 text-ink hover:bg-cobalt hover:text-white transition">Direct Stream -&gt; BigQuery (0 local files)</button>
                </div>
              </div>

              <div class="space-y-2.5 pt-1">
                <label class="flex items-center gap-2.5 text-xs text-ink cursor-pointer">
                  <input type="checkbox" id="opt-global" onchange="updateGeneratedCommand()" class="border-hairline text-cobalt">
                  <span>Enable global regions (<code class="font-mono text-muted">--regions global</code>)</span>
                </label>
                <label class="flex items-center gap-2.5 text-xs text-ink cursor-pointer">
                  <input type="checkbox" id="opt-compliance" onchange="updateGeneratedCommand()" class="border-hairline text-cobalt">
                  <span>Enable GDPR/CCPA consent ledger (<code class="font-mono text-muted">--compliance</code>)</span>
                </label>
                <label class="flex items-center gap-2.5 text-xs text-ink cursor-pointer">
                  <input type="checkbox" id="opt-identity" onchange="updateGeneratedCommand()" class="border-hairline text-cobalt">
                  <span>Inject 15% entity-resolution noise (<code class="font-mono text-muted">--identity-noise 0.15</code>)</span>
                </label>
              </div>
            </div>

            <div class="mt-6 pt-5 border-t border-hairline">
              <div class="bg-vellum/70 p-3 font-mono text-xs text-cobalt overflow-x-auto whitespace-nowrap mb-3" id="generated-command-display">ecommerce-synth generate --tier medium --chunk-size 500000</div>
              <button onclick="copyGeneratedCommand()" class="w-full py-2 bg-cobalt hover:bg-blue-800 text-white text-xs font-medium transition">
                Copy Command
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- Interactive 24-Table Schema, Topology Map & Data Dictionary (#schema) -->
      <section id="schema" class="py-14 border-b border-hairline">
        <div class="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-6">
          <div>
            <h2 class="font-bold text-ink mb-2">Schema Topology &amp; Data Dictionary (24 Tables)</h2>
            <p class="text-sm text-muted max-w-2xl">
              22 core omnichannel tables plus 2 optional governance/ER tables (<code class="font-mono text-xs text-ink">customer_consents</code>, <code class="font-mono text-xs text-ink">identity_ground_truth</code>).
            </p>
          </div>

          <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <div class="inline-flex border border-hairline bg-plate text-xs font-mono">
              <button onclick="selectDdlDialect('snowflake')" id="ddl-btn-snowflake" class="px-2.5 py-1.5 bg-cobalt text-white transition">Snowflake</button>
              <button onclick="selectDdlDialect('databricks')" id="ddl-btn-databricks" class="px-2.5 py-1.5 text-muted hover:text-ink transition">Databricks</button>
              <button onclick="selectDdlDialect('bigquery')" id="ddl-btn-bigquery" class="px-2.5 py-1.5 text-muted hover:text-ink transition">BigQuery</button>
            </div>

            <div class="relative w-full sm:w-56">
              <input type="text" id="schema-search" onkeyup="filterSchema()" placeholder="Filter tables or columns..."
                     class="w-full bg-plate border border-hairline px-3 py-1.5 text-xs text-ink placeholder-muted focus:outline-none focus:border-cobalt transition">
            </div>
          </div>
        </div>

        <!-- Cartographic Relationship Map with Layer Switcher -->
        <div class="bg-plate border border-hairline p-4 mb-6 overflow-x-auto atlas-grid">
          <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
            <div class="flex flex-wrap items-center gap-1.5 text-xs">
              <span class="font-mono text-[11px] text-muted mr-1">Layers:</span>
              <button onclick="setMapLayer('all')" id="layer-btn-all" class="px-2.5 py-1 bg-ink text-white font-medium transition">All Routes</button>
              <button onclick="setMapLayer('digital')" id="layer-btn-digital" class="px-2.5 py-1 bg-vellum text-ink hover:bg-hairline transition">Digital</button>
              <button onclick="setMapLayer('pos')" id="layer-btn-pos" class="px-2.5 py-1 bg-vellum text-ink hover:bg-hairline transition">Decoupled POS</button>
              <button onclick="setMapLayer('fulfillment')" id="layer-btn-fulfillment" class="px-2.5 py-1 bg-vellum text-ink hover:bg-hairline transition">BOPIS &amp; Web</button>
            </div>
            <button onclick="filterByTable('')" class="text-[11px] font-mono text-cobalt hover:underline">Reset table filter</button>
          </div>

          <svg id="atlas-erd" viewBox="0 0 1040 245" class="w-full min-w-[780px] h-auto text-[11px] font-mono">
            <!-- Digital FK lines (cobalt) -->
            <g id="layer-lines-digital" stroke="#1D4ED8" stroke-opacity="0.45" stroke-width="1.35" fill="none">
              <path d="M165 92 L245 43"/>
              <path d="M165 92 L245 147"/>
              <path d="M165 92 L245 199"/>
              <path d="M420 43 L505 147"/>
              <path d="M665 147 L755 147"/>
            </g>
            <!-- POS stitching & POS FK lines (amber) -->
            <g id="layer-lines-pos" fill="none">
              <path d="M165 92 L245 95" stroke="#B45309" stroke-width="1.5" stroke-dasharray="4 3"/>
              <path d="M420 95 L505 199" stroke="#B45309" stroke-opacity="0.6" stroke-width="1.35"/>
              <path d="M665 199 L755 95" stroke="#B45309" stroke-opacity="0.5" stroke-width="1.35"/>
            </g>
            <!-- Fulfillment / BOPIS / Inventory lines (teal) -->
            <g id="layer-lines-fulfillment" stroke="#0F766E" stroke-opacity="0.55" stroke-width="1.35" fill="none">
              <path d="M420 43 L505 43"/>
              <path d="M420 43 L505 95"/>
              <path d="M665 43 L755 43"/>
              <path d="M665 95 L755 95"/>
              <path d="M665 199 L755 199"/>
            </g>

            <!-- Hub: customers -->
            <g onclick="filterByTable('customers')" class="cursor-pointer map-node" data-layer="digital pos">
              <rect x="20" y="72" width="145" height="40" rx="4" fill="#FFFFFF" stroke="#1D4ED8" stroke-width="1.75"/>
              <text x="92" y="96" text-anchor="middle" fill="#0F172A" font-weight="600">customers</text>
            </g>
            <!-- Column 2 -->
            <g onclick="filterByTable('orders_online')" class="cursor-pointer map-node" data-layer="digital fulfillment">
              <rect x="245" y="25" width="175" height="36" rx="4" fill="#FFFFFF" stroke="#1D4ED8" stroke-opacity="0.6"/>
              <text x="332" y="47" text-anchor="middle" fill="#0F172A">orders_online</text>
            </g>
            <g onclick="filterByTable('instore_accounts')" class="cursor-pointer map-node" data-layer="pos">
              <rect x="245" y="77" width="175" height="36" rx="4" fill="#FAF8F4" stroke="#B45309" stroke-width="1.5"/>
              <text x="332" y="99" text-anchor="middle" fill="#B45309" font-weight="600">instore_accounts</text>
            </g>
            <g onclick="filterByTable('customer_consents')" class="cursor-pointer map-node" data-layer="digital">
              <rect x="245" y="129" width="175" height="36" rx="4" fill="#FFFFFF" stroke="#94A3B8" stroke-dasharray="3 2"/>
              <text x="332" y="151" text-anchor="middle" fill="#BE123C">customer_consents</text>
            </g>
            <g onclick="filterByTable('identity_ground_truth')" class="cursor-pointer map-node" data-layer="digital pos">
              <rect x="245" y="181" width="175" height="36" rx="4" fill="#FFFFFF" stroke="#94A3B8" stroke-dasharray="3 2"/>
              <text x="332" y="203" text-anchor="middle" fill="#1D4ED8">identity_ground_truth</text>
            </g>
            <!-- Column 3 -->
            <g onclick="filterByTable('shipments')" class="cursor-pointer map-node" data-layer="fulfillment">
              <rect x="505" y="25" width="160" height="36" rx="4" fill="#FFFFFF" stroke="#0F766E" stroke-opacity="0.6"/>
              <text x="585" y="47" text-anchor="middle" fill="#0F172A">shipments</text>
            </g>
            <g onclick="filterByTable('returns')" class="cursor-pointer map-node" data-layer="fulfillment">
              <rect x="505" y="77" width="160" height="36" rx="4" fill="#FFFFFF" stroke="#0F766E" stroke-opacity="0.6"/>
              <text x="585" y="99" text-anchor="middle" fill="#0F172A">returns</text>
            </g>
            <g onclick="filterByTable('clickstream')" class="cursor-pointer map-node" data-layer="digital fulfillment">
              <rect x="505" y="129" width="160" height="36" rx="4" fill="#FFFFFF" stroke="#1D4ED8" stroke-opacity="0.6"/>
              <text x="585" y="151" text-anchor="middle" fill="#0F766E">clickstream</text>
            </g>
            <g onclick="filterByTable('orders_instore')" class="cursor-pointer map-node" data-layer="pos">
              <rect x="505" y="181" width="160" height="36" rx="4" fill="#FFFFFF" stroke="#B45309" stroke-opacity="0.7"/>
              <text x="585" y="203" text-anchor="middle" fill="#0F172A">orders_instore</text>
            </g>
            <!-- Column 4 -->
            <g onclick="filterByTable('products')" class="cursor-pointer map-node" data-layer="digital fulfillment">
              <rect x="755" y="25" width="175" height="36" rx="4" fill="#FFFFFF" stroke="#DFD9CE"/>
              <text x="842" y="47" text-anchor="middle" fill="#0F172A">products</text>
            </g>
            <g onclick="filterByTable('stores')" class="cursor-pointer map-node" data-layer="pos fulfillment">
              <rect x="755" y="77" width="175" height="36" rx="4" fill="#FFFFFF" stroke="#0F766E" stroke-opacity="0.6"/>
              <text x="842" y="99" text-anchor="middle" fill="#0F172A">stores</text>
            </g>
            <g onclick="filterByTable('loyalty_members')" class="cursor-pointer map-node" data-layer="digital">
              <rect x="755" y="129" width="175" height="36" rx="4" fill="#FFFFFF" stroke="#DFD9CE"/>
              <text x="842" y="151" text-anchor="middle" fill="#0F172A">loyalty_members</text>
            </g>
            <g onclick="filterByTable('inventory_snapshots')" class="cursor-pointer map-node" data-layer="fulfillment pos">
              <rect x="755" y="181" width="175" height="36" rx="4" fill="#FFFFFF" stroke="#DFD9CE"/>
              <text x="842" y="203" text-anchor="middle" fill="#0F172A">inventory_snapshots</text>
            </g>
          </svg>
        </div>

        <!-- Domain Filter Pills -->
        <div class="flex flex-wrap gap-2 mb-6">
          <button onclick="filterDomain('all')" id="domain-pill-all" class="px-3.5 py-1.5 text-xs font-medium bg-cobalt text-white transition">All (24)</button>
          <button onclick="filterDomain('Omnichannel Sales & POS')" id="domain-pill-sales" class="px-3.5 py-1.5 text-xs font-medium bg-plate text-muted hover:text-ink border border-hairline transition">Sales, Fulfillment &amp; POS (9)</button>
          <button onclick="filterDomain('Customer 360 & Identity')" id="domain-pill-cust" class="px-3.5 py-1.5 text-xs font-medium bg-plate text-muted hover:text-ink border border-hairline transition">Customer 360 (4)</button>
          <button onclick="filterDomain('Engagement & Retention')" id="domain-pill-eng" class="px-3.5 py-1.5 text-xs font-medium bg-plate text-muted hover:text-ink border border-hairline transition">Engagement (6)</button>
          <button onclick="filterDomain('Experimentation & Fraud')" id="domain-pill-fraud" class="px-3.5 py-1.5 text-xs font-medium bg-plate text-muted hover:text-ink border border-hairline transition">Experiments &amp; Fraud (3)</button>
          <button onclick="filterDomain('Governance & Compliance')" id="domain-pill-gov" class="px-3.5 py-1.5 text-xs font-medium bg-plate text-muted hover:text-ink border border-hairline transition">Governance &amp; ER (2)</button>
        </div>

        <div id="schema-grid" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5"></div>
      </section>

      <!-- Multi-Warehouse Exporters (#warehouses) -->
      <section id="warehouses" class="py-14 border-b border-hairline">
        <div class="max-w-2xl mb-8">
          <h2 class="font-bold text-ink mb-2">Multi-Warehouse Exporters &amp; Direct Streaming</h2>
          <p class="text-sm text-muted">Load staged Parquet chunks via <code class="font-mono text-xs text-ink">export</code> or stream directly from memory via <code class="font-mono text-xs text-ink">--stream-to</code> with PK/FK constraints, PII tags, and analytical views.</p>
        </div>

        <div class="bg-plate border border-hairline">
          <div class="grid grid-cols-2 sm:grid-cols-4 border-b border-hairline bg-vellum text-xs font-medium">
            <button onclick="switchWhTab('databricks')" id="wh-tab-databricks" class="py-3 px-4 border-b-2 border-cobalt text-ink bg-plate transition">Databricks Unity Catalog</button>
            <button onclick="switchWhTab('snowflake')" id="wh-tab-snowflake" class="py-3 px-4 border-b-2 border-transparent text-muted hover:text-ink transition">Snowflake</button>
            <button onclick="switchWhTab('bigquery')" id="wh-tab-bigquery" class="py-3 px-4 border-b-2 border-transparent text-muted hover:text-ink transition">Google BigQuery</button>
            <button onclick="switchWhTab('duckdb')" id="wh-tab-duckdb" class="py-3 px-4 border-b-2 border-transparent text-muted hover:text-ink transition">DuckDB</button>
          </div>

          <div class="p-6">
            <div id="wh-content-databricks" class="grid grid-cols-1 lg:grid-cols-12 gap-6">
              <div class="lg:col-span-4 space-y-2 text-xs text-muted">
                <h3 class="font-semibold text-ink">Databricks Unity Catalog</h3>
                <p>Stages single or chunked Parquet directories to UC Volumes (or streams in-memory Parquet buffers), executes <code class="font-mono text-ink">read_files()</code> Delta CTAS, and applies UC column governance tags.</p>
              </div>
              <div class="lg:col-span-8 bg-vellum/60 p-4 font-mono text-xs text-ink overflow-x-auto">
                <div class="text-muted mb-1"># Direct stream or export</div>
                <div class="text-cobalt mb-3">$ ecommerce-synth generate --tier large --stream-to databricks --catalog dev --schema ecom</div>
                <div class="text-muted mb-1">-- Governance tags applied automatically</div>
                <div class="text-tealroute">ALTER TABLE dev.ecom.customers ALTER COLUMN email SET TAGS ('pii_classification' = 'DIRECT_PII', 'sensitivity' = 'HIGH');</div>
              </div>
            </div>

            <div id="wh-content-snowflake" class="hidden grid grid-cols-1 lg:grid-cols-12 gap-6">
              <div class="lg:col-span-4 space-y-2 text-xs text-muted">
                <h3 class="font-semibold text-ink">Snowflake</h3>
                <p>Supports internal stage <code class="font-mono text-ink">PUT</code> + <code class="font-mono text-ink">COPY INTO</code> and zero-file <code class="font-mono text-ink">write_pandas</code> streaming, with auto-discovered <code class="font-mono text-ink">connections.toml</code> profiles and 4h MFA caching.</p>
              </div>
              <div class="lg:col-span-8 bg-vellum/60 p-4 font-mono text-xs text-ink overflow-x-auto">
                <div class="text-muted mb-1"># Direct stream without local Parquet</div>
                <div class="text-cobalt mb-3">$ ecommerce-synth generate --tier large --stream-to snowflake --database ECOM_DB --schema PROD</div>
                <div class="text-muted mb-1">-- Governance tags applied automatically</div>
                <div class="text-tealroute">ALTER TABLE ECOM_DB.PROD.customers MODIFY COLUMN email SET TAG pii_classification = 'DIRECT_PII', sensitivity = 'HIGH';</div>
              </div>
            </div>

            <div id="wh-content-bigquery" class="hidden grid grid-cols-1 lg:grid-cols-12 gap-6">
              <div class="lg:col-span-4 space-y-2 text-xs text-muted">
                <h3 class="font-semibold text-ink">Google Cloud BigQuery</h3>
                <p>Streams DataFrames directly via <code class="font-mono text-ink">load_table_from_dataframe</code> or stages chunked Parquet files to GCS with native <code class="font-mono text-ink">LoadJob</code> ingestion.</p>
              </div>
              <div class="lg:col-span-8 bg-vellum/60 p-4 font-mono text-xs text-ink overflow-x-auto">
                <div class="text-muted mb-1"># Direct stream to BigQuery</div>
                <div class="text-cobalt mb-3">$ ecommerce-synth generate --tier medium --stream-to bigquery --project my-gcp-project --dataset ecom</div>
                <div class="text-muted mb-1">-- Analytical view deployed</div>
                <div class="text-tealroute">CREATE OR REPLACE VIEW `my-gcp-project.ecom.v_customer_360` AS ...</div>
              </div>
            </div>

            <div id="wh-content-duckdb" class="hidden grid grid-cols-1 lg:grid-cols-12 gap-6">
              <div class="lg:col-span-4 space-y-2 text-xs text-muted">
                <h3 class="font-semibold text-ink">DuckDB</h3>
                <p>Zero-copy Polars registration via <code class="font-mono text-ink">--stream-to duckdb</code> or multi-part <code class="font-mono text-ink">read_parquet([...])</code> export with custom <code class="font-mono text-ink">--schema</code> support.</p>
              </div>
              <div class="lg:col-span-8 bg-vellum/60 p-4 font-mono text-xs text-ink overflow-x-auto">
                <div class="text-muted mb-1"># Stream directly into a custom schema</div>
                <div class="text-cobalt mb-3">$ ecommerce-synth generate --tier medium --stream-to duckdb --database ./live.duckdb --schema retail</div>
                <div class="text-muted mb-1">-- Query immediately</div>
                <div class="text-tealroute">SELECT * FROM retail.v_customer_360 ORDER BY lifetime_spend DESC LIMIT 10;</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- SQL Recipes (#recipes) -->
      <section id="recipes" class="py-14 border-b border-hairline">
        <div class="max-w-2xl mb-8">
          <h2 class="font-bold text-ink mb-2">SQL Recipes &amp; Benchmark Queries</h2>
          <p class="text-sm text-muted">Ready-to-run analytical queries for cross-channel identity resolution, decoupled POS stitching, GDPR auditing, funnel attribution, and multi-currency GMV.</p>
        </div>

        <div class="bg-plate border border-hairline">
          <div class="grid grid-cols-2 sm:grid-cols-5 border-b border-hairline bg-vellum text-xs font-medium">
            <button onclick="switchRecipeTab('er')" id="rec-tab-er" class="py-3 px-4 border-b-2 border-cobalt text-ink bg-plate transition">Entity Resolution</button>
            <button onclick="switchRecipeTab('pos')" id="rec-tab-pos" class="py-3 px-4 border-b-2 border-transparent text-muted hover:text-ink transition">POS Stitching</button>
            <button onclick="switchRecipeTab('gdpr')" id="rec-tab-gdpr" class="py-3 px-4 border-b-2 border-transparent text-muted hover:text-ink transition">GDPR Consent</button>
            <button onclick="switchRecipeTab('funnel')" id="rec-tab-funnel" class="py-3 px-4 border-b-2 border-transparent text-muted hover:text-ink transition">Funnel &amp; Cookie</button>
            <button onclick="switchRecipeTab('fx')" id="rec-tab-fx" class="py-3 px-4 border-b-2 border-transparent text-muted hover:text-ink transition">Multi-Currency</button>
          </div>
          <div class="p-6 bg-paper font-mono text-xs text-ink overflow-x-auto">
            <pre id="rec-content-er" class="leading-relaxed">SELECT
  gt.record_type,
  gt.noise_type,
  COUNT(*) AS total_records,
  COUNT(DISTINCT gt.true_entity_id) AS canonical_entities
FROM identity_ground_truth gt
GROUP BY gt.record_type, gt.noise_type
ORDER BY total_records DESC;</pre>

            <pre id="rec-content-pos" class="hidden leading-relaxed">SELECT
  ia.instore_account_id,
  c.customer_id AS matched_digital_id,
  COUNT(oi.transaction_id) AS pos_txns,
  ROUND(SUM(oi.total_amount_usd), 2) AS pos_spend_usd
FROM instore_accounts ia
LEFT JOIN customers c
  ON (ia.email IS NOT NULL AND LOWER(TRIM(ia.email)) = LOWER(TRIM(c.email)))
  OR (ia.phone_number IS NOT NULL AND RIGHT(REGEXP_REPLACE(ia.phone_number, '[^0-9]', '', 'g'), 10) = RIGHT(REGEXP_REPLACE(c.phone, '[^0-9]', '', 'g'), 10))
LEFT JOIN orders_instore oi ON ia.instore_account_id = oi.instore_account_id
GROUP BY 1, 2
ORDER BY pos_spend_usd DESC NULLS LAST;</pre>

            <pre id="rec-content-gdpr" class="hidden leading-relaxed">SELECT
  cc.jurisdiction,
  cc.purpose,
  cc.status,
  COUNT(*) AS customer_count
FROM customer_consents cc
JOIN customers c ON cc.customer_id = c.customer_id
GROUP BY 1, 2, 3
ORDER BY 1, 2, 4 DESC;</pre>

            <pre id="rec-content-funnel" class="hidden leading-relaxed">SELECT
  o.device_type,
  o.fulfillment_type,
  COUNT(DISTINCT o.order_id) AS linked_orders,
  COUNT(DISTINCT cs.anonymous_id) AS stitched_cookies
FROM orders_online o
JOIN clickstream cs ON o.session_id = cs.session_id
GROUP BY 1, 2;</pre>

            <pre id="rec-content-fx" class="hidden leading-relaxed">SELECT
  currency_code,
  tax_regime,
  COUNT(*) AS order_count,
  ROUND(SUM(total_amount), 2) AS local_gmv,
  ROUND(SUM(total_amount_usd), 2) AS usd_consolidated_gmv
FROM orders_online
GROUP BY 1, 2
ORDER BY usd_consolidated_gmv DESC;</pre>
          </div>
        </div>
      </section>

      <!-- Behavioral Personas Matrix (#personas) -->
      <section id="personas" class="py-14 border-b border-hairline">
        <div class="max-w-2xl mb-8">
          <h2 class="font-bold text-ink mb-2">Behavioral Customer Personas &amp; Fraud Vectors</h2>
          <p class="text-sm text-muted">Activity across orders, clickstream, email engagement, loyalty, and fraud anomalies is driven by 7 empirical personas in <code class="font-mono text-xs text-ink">persona.py</code>.</p>
        </div>

        <div class="bg-plate border border-hairline overflow-x-auto">
          <table class="w-full text-left border-collapse text-xs sm:text-sm">
            <thead>
              <tr class="border-b border-hairline bg-vellum text-xs font-medium text-muted">
                <th class="py-3 px-4">Persona</th>
                <th class="py-3 px-4 text-right">Share</th>
                <th class="py-3 px-4 text-right">Orders / Yr</th>
                <th class="py-3 px-4 text-right">Email Open</th>
                <th class="py-3 px-4 text-right">Return Rate</th>
                <th class="py-3 px-4">Behavioral Signature</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-hairline tabular-nums">
              <tr><td class="py-3 px-4 font-semibold text-cobalt">Power Shopper</td><td class="py-3 px-4 text-right font-mono">8%</td><td class="py-3 px-4 text-right font-mono">12 - 30</td><td class="py-3 px-4 text-right font-mono">65%</td><td class="py-3 px-4 text-right font-mono">8%</td><td class="py-3 px-4 text-muted text-xs">VIP Gold/Platinum loyalty, high AOV, frequent omnichannel</td></tr>
              <tr><td class="py-3 px-4 font-semibold text-ink">Regular</td><td class="py-3 px-4 text-right font-mono">27%</td><td class="py-3 px-4 text-right font-mono">4 - 10</td><td class="py-3 px-4 text-right font-mono">35%</td><td class="py-3 px-4 text-right font-mono">10%</td><td class="py-3 px-4 text-muted text-xs">Consistent repeat purchases, Bronze/Silver loyalty</td></tr>
              <tr><td class="py-3 px-4 font-semibold text-ink">Occasional</td><td class="py-3 px-4 text-right font-mono">30%</td><td class="py-3 px-4 text-right font-mono">1 - 3</td><td class="py-3 px-4 text-right font-mono">20%</td><td class="py-3 px-4 text-right font-mono">12%</td><td class="py-3 px-4 text-muted text-xs">Seasonal holiday peaks, mixed online and POS</td></tr>
              <tr><td class="py-3 px-4 font-semibold text-amberroute">Bargain Hunter</td><td class="py-3 px-4 text-right font-mono">15%</td><td class="py-3 px-4 text-right font-mono">2 - 6</td><td class="py-3 px-4 text-right font-mono">50%</td><td class="py-3 px-4 text-right font-mono">15%</td><td class="py-3 px-4 text-muted text-xs">Promo-driven, always applies coupon codes</td></tr>
              <tr><td class="py-3 px-4 font-semibold text-muted">One-and-Done</td><td class="py-3 px-4 text-right font-mono">10%</td><td class="py-3 px-4 text-right font-mono">1</td><td class="py-3 px-4 text-right font-mono">8%</td><td class="py-3 px-4 text-right font-mono">5%</td><td class="py-3 px-4 text-muted text-xs">Single order churned cohort</td></tr>
              <tr><td class="py-3 px-4 font-semibold text-tealroute">Window Shopper</td><td class="py-3 px-4 text-right font-mono">8%</td><td class="py-3 px-4 text-right font-mono">0</td><td class="py-3 px-4 text-right font-mono">12%</td><td class="py-3 px-4 text-right font-mono">0%</td><td class="py-3 px-4 text-muted text-xs">Heavy browse &amp; cart abandon telemetry</td></tr>
              <tr class="bg-rose-50/60"><td class="py-3 px-4 font-semibold text-crimson">Fraudster</td><td class="py-3 px-4 text-right font-mono text-crimson">2%</td><td class="py-3 px-4 text-right font-mono">15 - 40</td><td class="py-3 px-4 text-right font-mono">5%</td><td class="py-3 px-4 text-right font-mono text-crimson">60%+</td><td class="py-3 px-4 text-crimson text-xs">Card testing, account takeover, promo/refund abuse, synthetic ID</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Quickstart (#quickstart) -->
      <section id="quickstart" class="py-14">
        <div class="max-w-2xl mb-8">
          <h2 class="font-bold text-ink mb-2">Quickstart &amp; CLI Reference</h2>
          <p class="text-sm text-muted">Install with optional warehouse connectors and run locally in Python 3.11+.</p>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div class="bg-plate border border-hairline p-6 space-y-3 font-mono text-xs text-ink">
            <div class="text-xs font-sans font-semibold text-ink mb-2">Installation</div>
            <div class="bg-vellum/70 p-3 flex items-center justify-between gap-2">
              <span>pip install -e ".[dev]"</span>
              <button onclick="copyCommand('pip install -e &quot;.[dev]&quot;')" class="text-muted hover:text-ink shrink-0">Copy</button>
            </div>
            <div class="bg-vellum/70 p-3 flex items-center justify-between gap-2">
              <span>pip install -e ".[all-targets]"</span>
              <button onclick="copyCommand('pip install -e &quot;.[all-targets]&quot;')" class="text-muted hover:text-ink shrink-0">Copy</button>
            </div>
          </div>

          <div class="bg-plate border border-hairline p-6 space-y-3 font-mono text-xs text-ink">
            <div class="text-xs font-sans font-semibold text-ink mb-2">Common Workflows</div>
            <div class="bg-vellum/70 p-3">
              <span class="text-muted block mb-0.5"># Stream 50M+ scale directly to Snowflake (no local Parquet)</span>
              <span class="text-cobalt">ecommerce-synth generate --tier large --stream-to snowflake --database ECOM_DB --schema PROD</span>
            </div>
            <div class="bg-vellum/70 p-3">
              <span class="text-muted block mb-0.5"># Global regions + GDPR consent + cross-channel entity noise</span>
              <span class="text-tealroute">ecommerce-synth generate --tier medium --regions US,GB,DE,JP --compliance --identity-noise 0.15</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Footer -->
      <footer class="py-8 border-t border-hairline text-muted text-xs flex flex-col sm:flex-row items-center justify-between gap-4">
        <div class="font-mono">ecommerce-synth · Apache-2.0</div>
        <div class="flex items-center gap-6">
          <a href="https://github.com/anilkulkarni87/ecommerce_synthetic" target="_blank" rel="noopener noreferrer" class="hover:text-ink transition">Repository</a>
          <a href="#schema" class="hover:text-ink transition">Schema Dictionary</a>
        </div>
      </footer>
    </main>
  </div>

  <!-- Toast -->
  <div id="copy-toast" class="fixed bottom-5 right-5 z-50 px-3.5 py-2 bg-ink text-white text-xs font-medium shadow-lg transform translate-y-16 opacity-0 transition-all duration-200 pointer-events-none">
    <span id="toast-message">Copied to clipboard</span>
  </div>

  <script>
    const SCHEMA = __SCHEMA_JSON__;

    const TIERS = {
      small: { customers: "500", onlineOrders: "1,000", storeTxns: "500", clickstream: "50,000", emails: "5,000", loyalty: "300", support: "150", size: "< 5 MB" },
      medium: { customers: "50,000", onlineOrders: "100,000", storeTxns: "40,000", clickstream: "5,000,000", emails: "500,000", loyalty: "30,000", support: "12,000", size: "~350 MB" },
      large: { customers: "500,000", onlineOrders: "1,000,000", storeTxns: "400,000", clickstream: "50,000,000", emails: "5,000,000", loyalty: "300,000", support: "120,000", size: "~3.5 GB" },
      xl: { customers: "5,000,000", onlineOrders: "10,000,000", storeTxns: "4,000,000", clickstream: "500,000,000", emails: "50,000,000", loyalty: "3,000,000", support: "1,200,000", size: "~35 GB" }
    };

    let currentTier = "medium";
    let currentDomain = "all";
    let currentCmdMode = "parquet";
    let currentDdlDialect = "snowflake";

    function setMapLayer(layer) {
      ['all', 'digital', 'pos', 'fulfillment'].forEach(l => {
        const btn = document.getElementById('layer-btn-' + l);
        btn.className = l === layer
          ? "px-2.5 py-1 bg-ink text-white font-medium transition"
          : "px-2.5 py-1 bg-vellum text-ink hover:bg-hairline transition";
      });
      const lineGroups = {
        digital: document.getElementById('layer-lines-digital'),
        pos: document.getElementById('layer-lines-pos'),
        fulfillment: document.getElementById('layer-lines-fulfillment'),
      };
      Object.entries(lineGroups).forEach(([k, g]) => {
        if (g) g.style.opacity = (layer === 'all' || layer === k) ? '1' : '0.12';
      });
      document.querySelectorAll('.map-node').forEach(node => {
        const layers = (node.getAttribute('data-layer') || '').split(' ');
        node.style.opacity = (layer === 'all' || layers.includes(layer)) ? '1' : '0.28';
      });
    }

    function toggleModeMenu() {
      document.getElementById('cmd-mode-menu').classList.toggle('hidden');
    }

    function selectCmdMode(mode, label) {
      currentCmdMode = mode;
      document.getElementById('cmd-mode-label').textContent = label;
      document.getElementById('cmd-mode-menu').classList.add('hidden');
      updateGeneratedCommand();
    }

    function selectDdlDialect(dialect) {
      currentDdlDialect = dialect;
      ['snowflake', 'databricks', 'bigquery'].forEach(d => {
        document.getElementById('ddl-btn-' + d).className = d === dialect
          ? "px-2.5 py-1.5 bg-cobalt text-white transition"
          : "px-2.5 py-1.5 text-muted hover:text-ink transition";
      });
    }

    document.addEventListener('click', (e) => {
      const btn = document.getElementById('cmd-mode-btn');
      const menu = document.getElementById('cmd-mode-menu');
      if (btn && menu && !btn.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.add('hidden');
      }
    });

    function selectTier(tierKey) {
      currentTier = tierKey;
      ['small', 'medium', 'large', 'xl'].forEach(k => {
        const btn = document.getElementById('tier-btn-' + k);
        btn.className = k === tierKey
          ? "px-4 py-1.5 text-xs font-medium bg-cobalt text-white transition"
          : "px-4 py-1.5 text-xs font-medium text-muted hover:text-ink transition";
      });
      const t = TIERS[tierKey];
      document.getElementById('stat-customers').textContent = t.customers;
      document.getElementById('stat-online-orders').textContent = t.onlineOrders;
      document.getElementById('stat-store-txns').textContent = t.storeTxns;
      document.getElementById('stat-clickstream').textContent = t.clickstream;
      document.getElementById('stat-emails').textContent = t.emails;
      document.getElementById('stat-loyalty').textContent = t.loyalty;
      document.getElementById('stat-support').textContent = t.support;
      document.getElementById('stat-size').textContent = t.size;
      updateGeneratedCommand();
    }

    function updateGeneratedCommand() {
      const mode = currentCmdMode;
      const useGlobal = document.getElementById('opt-global').checked;
      const useCompliance = document.getElementById('opt-compliance').checked;
      const useIdentity = document.getElementById('opt-identity').checked;

      let cmd = `ecommerce-synth generate --tier ${currentTier} --chunk-size 500000`;
      if (useGlobal) cmd += ` --regions global`;
      if (useCompliance) cmd += ` --compliance`;
      if (useIdentity) cmd += ` --identity-noise 0.15`;

      if (mode === 'stream-duckdb') cmd += ` --stream-to duckdb --database ./live.duckdb`;
      else if (mode === 'stream-snowflake') cmd += ` --stream-to snowflake --database ECOM_DB --schema PROD`;
      else if (mode === 'stream-databricks') cmd += ` --stream-to databricks --catalog dev --schema ecom`;
      else if (mode === 'stream-bigquery') cmd += ` --stream-to bigquery --project my-gcp-project --dataset ecom`;

      document.getElementById('generated-command-display').textContent = cmd;
    }

    function copyGeneratedCommand() {
      copyCommand(document.getElementById('generated-command-display').textContent);
    }

    function copyCommand(text) {
      navigator.clipboard.writeText(text);
      const toast = document.getElementById('copy-toast');
      document.getElementById('toast-message').textContent = `Copied: ${text.length > 42 ? text.substring(0, 42) + '...' : text}`;
      toast.classList.remove('translate-y-16', 'opacity-0');
      toast.classList.add('translate-y-0', 'opacity-100');
      setTimeout(() => {
        toast.classList.add('translate-y-16', 'opacity-0');
        toast.classList.remove('translate-y-0', 'opacity-100');
      }, 2200);
    }

    function switchTerminalTab(tabId) {
      ['stream', 'generate', 'compliance', 'validate'].forEach(t => {
        const btn = document.getElementById('term-tab-' + t);
        const content = document.getElementById('term-content-' + t);
        if (t === tabId) {
          btn.className = "px-2.5 py-1 bg-cobalt text-white font-medium transition";
          content.classList.remove('hidden');
        } else {
          btn.className = "px-2.5 py-1 text-muted hover:text-ink transition";
          content.classList.add('hidden');
        }
      });
    }

    function switchWhTab(targetId) {
      ['databricks', 'snowflake', 'bigquery', 'duckdb'].forEach(t => {
        const btn = document.getElementById('wh-tab-' + t);
        const content = document.getElementById('wh-content-' + t);
        if (t === targetId) {
          btn.className = "py-3 px-4 border-b-2 border-cobalt text-ink bg-plate transition";
          content.classList.remove('hidden');
        } else {
          btn.className = "py-3 px-4 border-b-2 border-transparent text-muted hover:text-ink transition";
          content.classList.add('hidden');
        }
      });
    }

    function getTypeColorClass(typeStr) {
      const t = typeStr.toLowerCase();
      if (t.includes('uuid')) return 'text-cobalt';
      if (t.includes('timestamp') || t.includes('date')) return 'text-tealroute';
      if (t.includes('int') || t.includes('float')) return 'text-amberroute';
      if (t.includes('bool')) return 'text-emerald-700';
      return 'text-muted';
    }

    const SAMPLE_ROWS = {
      customers: [
        { customer_id: "c8a1f2...", first_name: "Elena", last_name: "Vance", email: "elena.vance42@gmail.com", customer_segment: "vip" },
        { customer_id: "9b120e...", first_name: "REDACTED", last_name: "REDACTED", email: "erased_9b12@anonymized.local", customer_segment: "returning" }
      ],
      instore_accounts: [
        { instore_account_id: "ia_441...", customer_id: null, store_id: "STORE-012", phone_number: "(415) 555-0192", email: null },
        { instore_account_id: "ia_442...", customer_id: null, store_id: "STORE-004", phone_number: null, email: "pos.shopper@example.com" }
      ],
      orders_online: [
        { order_id: "ord_771a...", customer_id: "c8a1f2...", fulfillment_type: "bopis", pickup_store_id: "STORE-012", currency_code: "EUR", payment_token: "tok_9f2a1c" },
        { order_id: "ord_882b...", customer_id: null, guest_email: "guest@example.com", fulfillment_type: "ship_to_home", currency_code: "USD", payment_token: "tok_3d8b10" }
      ],
      shipments: [
        { shipment_id: "shp_01a...", order_id: "ord_882b...", carrier: "DHL", tracking_number: "DH4829103841", shipping_tier: "express", status: "delivered" }
      ],
      returns: [
        { return_id: "ret_19c...", order_id: "ord_882b...", return_channel: "instore", return_store_id: "STORE-008", return_reason: "wrong_size", refund_amount: 84.50 }
      ],
      customer_consents: [
        { consent_id: "cns_11a...", jurisdiction: "GDPR", purpose: "analytics_cookies", status: "withdrawn" },
        { consent_id: "cns_11b...", jurisdiction: "CCPA", purpose: "marketing_email", status: "granted" }
      ],
      identity_ground_truth: [
        { record_type: "customer", customer_id: "c8a1f2...", instore_account_id: null, true_entity_id: "c8a1f2...", is_duplicate: false, noise_type: "none" },
        { record_type: "instore_account", customer_id: null, instore_account_id: "ia_441...", true_entity_id: "c8a1f2...", is_duplicate: true, noise_type: "pos_cross_channel" }
      ],
      fraud_flags: [
        { flag_id: "flg_001...", entity_type: "order", fraud_type: "card_testing", risk_score: 0.94, is_confirmed_fraud: true }
      ]
    };

    function switchRecipeTab(tabId) {
      ['er', 'pos', 'gdpr', 'funnel', 'fx'].forEach(t => {
        const btn = document.getElementById('rec-tab-' + t);
        const pre = document.getElementById('rec-content-' + t);
        if (t === tabId) {
          btn.className = "py-3 px-4 border-b-2 border-cobalt text-ink bg-plate transition";
          pre.classList.remove('hidden');
        } else {
          btn.className = "py-3 px-4 border-b-2 border-transparent text-muted hover:text-ink transition";
          pre.classList.add('hidden');
        }
      });
    }

    function filterByTable(tableName) {
      document.getElementById('schema-search').value = tableName;
      if (tableName) {
        currentDomain = 'all';
        filterDomain('all');
      } else {
        renderSchemaCards();
      }
    }

    function mapSqlType(rawType, dialect) {
      const t = rawType.toLowerCase();
      if (t.includes('string') || t.includes('uuid')) return dialect === 'snowflake' ? 'VARCHAR' : 'STRING';
      if (t.includes('integer')) return dialect === 'bigquery' ? 'INT64' : 'INT';
      if (t.includes('float')) return dialect === 'bigquery' ? 'FLOAT64' : (dialect === 'databricks' ? 'DOUBLE' : 'FLOAT');
      if (t.includes('bool')) return dialect === 'bigquery' ? 'BOOL' : 'BOOLEAN';
      if (t.includes('timestamp')) return dialect === 'snowflake' ? 'TIMESTAMP_NTZ' : 'TIMESTAMP';
      if (t.includes('date')) return 'DATE';
      return 'STRING';
    }

    function copyTableDDL(tableName) {
      const tinfo = SCHEMA.tables[tableName];
      const dialect = currentDdlDialect;
      const cols = [];
      const tagStmts = [];
      for (const [cname, cinfo] of Object.entries(tinfo.columns)) {
        const sqlType = mapSqlType(cinfo.type, dialect);
        const nn = cinfo.nullable ? '' : ' NOT NULL';
        cols.push(`  ${cname} ${sqlType}${nn}`);
        if (cinfo.pii_classification) {
          if (dialect === 'databricks') {
            tagStmts.push(`ALTER TABLE catalog.schema.${tableName} ALTER COLUMN ${cname} SET TAGS ('pii_classification' = '${cinfo.pii_classification}', 'sensitivity' = '${cinfo.sensitivity}');`);
          } else if (dialect === 'snowflake') {
            tagStmts.push(`ALTER TABLE db.schema.${tableName} MODIFY COLUMN ${cname} SET TAG pii_classification = '${cinfo.pii_classification}', sensitivity = '${cinfo.sensitivity}';`);
          }
        }
      }
      if (tinfo.primary_key && dialect !== 'bigquery') {
        cols.push(`  CONSTRAINT ${tableName}_pk PRIMARY KEY (${tinfo.primary_key})`);
      }
      let ddl = `CREATE OR REPLACE TABLE ${tableName} (\\n${cols.join(',\\n')}\\n);`;
      if (tagStmts.length > 0) ddl += `\\n\\n${tagStmts.join('\\n')}`;
      copyCommand(ddl);
    }

    function toggleSampleData(tableName) {
      const el = document.getElementById('sample-container-' + tableName);
      if (el) el.classList.toggle('hidden');
    }

    function renderSchemaCards() {
      const container = document.getElementById('schema-grid');
      container.innerHTML = '';
      const query = document.getElementById('schema-search').value.toLowerCase().trim();

      for (const [tname, tinfo] of Object.entries(SCHEMA.tables)) {
        if (currentDomain !== 'all' && tinfo.domain !== currentDomain) continue;
        const colNames = Object.keys(tinfo.columns).join(' ').toLowerCase();
        if (query && !tname.toLowerCase().includes(query) && !tinfo.description.toLowerCase().includes(query) && !colNames.includes(query)) continue;

        const colCount = Object.keys(tinfo.columns).length;
        const pk = tinfo.primary_key || 'None';
        const fkCount = tinfo.foreign_keys ? Object.keys(tinfo.foreign_keys).length : 0;

        let columnsHtml = '';
        let piiCount = 0;
        for (const [cname, cinfo] of Object.entries(tinfo.columns)) {
          const isPK = cname === pk;
          const isFK = tinfo.foreign_keys && tinfo.foreign_keys[cname];
          const pii = cinfo.pii_classification;
          if (pii) piiCount++;
          let piiBadge = '';
          if (pii === 'DIRECT_PII') piiBadge = '<span class="ml-1 text-[9px] px-1 bg-rose-100 text-crimson font-semibold">PII:HIGH</span>';
          else if (pii === 'INDIRECT_PII') piiBadge = '<span class="ml-1 text-[9px] px-1 bg-amber-100 text-amberroute font-semibold">PII:MED</span>';
          else if (pii === 'FINANCIAL') piiBadge = '<span class="ml-1 text-[9px] px-1 bg-teal-100 text-tealroute font-semibold">FIN</span>';

          columnsHtml += `
            <tr class="border-b border-hairline/70 last:border-0 text-[11px]">
              <td class="py-2 pr-2 font-mono text-ink">
                ${cname}
                ${isPK ? '<span class="ml-1 text-[9px] px-1 bg-amber-100 text-amberroute font-semibold">PK</span>' : ''}
                ${isFK ? '<span class="ml-1 text-[9px] px-1 bg-blue-100 text-cobalt font-semibold">FK</span>' : ''}
                ${piiBadge}
              </td>
              <td class="py-2 px-2 font-mono ${getTypeColorClass(cinfo.type)}">${cinfo.type}</td>
              <td class="py-2 px-2 text-muted">${cinfo.nullable ? 'NULL' : 'NOT NULL'}</td>
              <td class="py-2 pl-2 text-muted max-w-[140px] truncate" title="${cinfo.description}">${cinfo.description}</td>
            </tr>
          `;
        }

        const card = document.createElement('div');
        card.className = "bg-plate border border-hairline p-5 flex flex-col justify-between";
        card.innerHTML = `
          <div>
            <div class="flex items-start justify-between gap-2 mb-2">
              <div>
                <h3 class="text-sm font-semibold text-ink font-mono flex items-center gap-2">
                  <span>${tname}</span>
                  ${tinfo.is_optional ? `<span class="text-[10px] font-mono px-1.5 py-0.5 bg-blue-50 text-cobalt">${tinfo.optional_flag}</span>` : ''}
                </h3>
                <span class="text-[11px] text-muted">${tinfo.domain}</span>
              </div>
              <span class="text-[10px] font-mono px-2 py-0.5 bg-vellum text-muted">${tinfo.file}</span>
            </div>
            <p class="text-xs text-muted mb-3 leading-relaxed">${tinfo.description}</p>
            <div class="flex flex-wrap gap-1.5 text-[11px] font-mono mb-3">
              <span class="px-2 py-0.5 bg-vellum text-ink">Cols: ${colCount}</span>
              <span class="px-2 py-0.5 bg-vellum text-amberroute">PK: ${pk}</span>
              ${fkCount > 0 ? `<span class="px-2 py-0.5 bg-vellum text-cobalt">FKs: ${fkCount}</span>` : ''}
              ${piiCount > 0 ? `<span class="px-2 py-0.5 bg-vellum text-crimson">Tags: ${piiCount}</span>` : ''}
            </div>
          </div>

          <div>
            <div id="cols-container-${tname}" class="hidden mt-3 pt-3 border-t border-hairline overflow-x-auto max-h-64">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="text-[10px] uppercase font-semibold text-muted border-b border-hairline">
                    <th class="pb-1.5 pr-2">Column</th>
                    <th class="pb-1.5 px-2">Type</th>
                    <th class="pb-1.5 px-2">Null</th>
                    <th class="pb-1.5 pl-2">Description</th>
                  </tr>
                </thead>
                <tbody>${columnsHtml}</tbody>
              </table>
            </div>
            <div id="sample-container-${tname}" class="hidden mt-3 pt-3 border-t border-hairline overflow-x-auto">
              <pre class="text-[10px] font-mono text-ink bg-vellum/70 p-2.5 leading-relaxed">${SAMPLE_ROWS[tname] ? JSON.stringify(SAMPLE_ROWS[tname], null, 2) : ''}</pre>
            </div>

            <div class="flex items-center gap-2 mt-2">
              <button onclick="toggleTableDetails('${tname}')" id="toggle-btn-${tname}"
                      class="flex-1 py-1.5 bg-vellum hover:bg-hairline text-ink text-xs font-medium transition">
                View ${colCount} Columns
              </button>
              <button onclick="copyTableDDL('${tname}')"
                      class="px-2.5 py-1.5 bg-plate hover:bg-vellum text-cobalt text-xs font-mono border border-hairline transition" title="Copy CREATE TABLE DDL + Governance Tags">
                DDL
              </button>
              ${SAMPLE_ROWS[tname] ? `<button onclick="toggleSampleData('${tname}')" class="px-2.5 py-1.5 bg-plate hover:bg-vellum text-tealroute text-xs font-mono border border-hairline transition">Sample</button>` : ''}
            </div>
          </div>
        `;
        container.appendChild(card);
      }

      if (container.children.length === 0) {
        container.innerHTML = `<div class="col-span-full py-12 text-center text-sm text-muted">No matching tables found.</div>`;
      }
    }

    function toggleTableDetails(tableName) {
      const container = document.getElementById('cols-container-' + tableName);
      const btn = document.getElementById('toggle-btn-' + tableName);
      if (container.classList.contains('hidden')) {
        container.classList.remove('hidden');
        btn.textContent = 'Hide Columns';
      } else {
        container.classList.add('hidden');
        btn.textContent = `View ${Object.keys(SCHEMA.tables[tableName].columns).length} Columns`;
      }
    }

    function filterDomain(domainName) {
      currentDomain = domainName;
      const map = {
        'all': 'domain-pill-all',
        'Omnichannel Sales & POS': 'domain-pill-sales',
        'Customer 360 & Identity': 'domain-pill-cust',
        'Engagement & Retention': 'domain-pill-eng',
        'Experimentation & Fraud': 'domain-pill-fraud',
        'Governance & Compliance': 'domain-pill-gov',
      };
      Object.values(map).forEach(id => {
        document.getElementById(id).className = "px-3.5 py-1.5 text-xs font-medium bg-plate text-muted hover:text-ink border border-hairline transition";
      });
      document.getElementById(map[domainName]).className = "px-3.5 py-1.5 text-xs font-medium bg-cobalt text-white transition";
      renderSchemaCards();
    }

    function filterSchema() {
      renderSchemaCards();
    }

    document.addEventListener('DOMContentLoaded', () => {
      renderSchemaCards();
    });
  </script>
</body>
</html>
'''

html_content = html_template.replace("__SCHEMA_JSON__", schema_json_str)
output_path = repo_root / "docs" / "index.html"
with open(output_path, "w") as f:
    f.write(html_content)

print(f"Generated {output_path} successfully ({len(html_content):,} bytes, {len(all_tables)} tables).")
