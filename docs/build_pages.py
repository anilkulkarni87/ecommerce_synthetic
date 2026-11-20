#!/usr/bin/env python3
"""Builds docs/index.html with embedded schema (19 core + 2 optional tables) and clean editorial UI."""

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
  <title>ecommerce-synth — Omnichannel Synthetic Data Generator</title>
  <meta name="description" content="Referentially-intact omnichannel synthetic ecommerce data generator for Parquet, DuckDB, Databricks Unity Catalog, Snowflake, and BigQuery.">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">

  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          fontFamily: {
            sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
            mono: ['Fira Code', 'ui-monospace', 'SFMono-Regular', 'monospace'],
          },
          colors: {
            canvas: '#0A0D14',
            surface: '#111622',
            elevated: '#171E2E',
            borderline: '#1F293D',
            accent: '#6366F1',
          }
        }
      }
    }
  </script>

  <style>
    ::selection {
      background: #6366F1;
      color: #FFFFFF;
    }
    ::-webkit-scrollbar {
      width: 8px;
      height: 8px;
    }
    ::-webkit-scrollbar-track {
      background: #0A0D14;
    }
    ::-webkit-scrollbar-thumb {
      background: #1F293D;
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #334155;
    }
    :focus-visible {
      outline: 2px solid #6366F1;
      outline-offset: 2px;
    }
    .tabular-nums {
      font-variant-numeric: tabular-nums;
    }
  </style>
</head>
<body class="bg-canvas text-slate-100 font-sans antialiased">

  <!-- Top Navigation -->
  <header class="sticky top-0 z-50 bg-canvas/90 backdrop-blur-md border-b border-borderline">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
      <a href="#" class="flex items-center gap-2.5 text-slate-100 hover:text-white transition">
        <svg class="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
        </svg>
        <span class="font-semibold text-sm tracking-tight font-mono">ecommerce-synth</span>
        <span class="text-[11px] font-mono px-1.5 py-0.5 rounded bg-elevated text-slate-400 border border-borderline">v1.1.0</span>
      </a>

      <nav class="hidden md:flex items-center gap-6 text-xs font-medium text-slate-400">
        <a href="#features" class="hover:text-slate-100 transition">Capabilities</a>
        <a href="#tiers" class="hover:text-slate-100 transition">Scale &amp; CLI</a>
        <a href="#schema" class="hover:text-slate-100 transition">Schema (21)</a>
        <a href="#warehouses" class="hover:text-slate-100 transition">Warehouses</a>
        <a href="#personas" class="hover:text-slate-100 transition">Personas</a>
        <a href="#quickstart" class="hover:text-slate-100 transition">Quickstart</a>
      </nav>

      <a href="https://github.com/anilkulkarni87/ecommerce_synthetic" target="_blank" rel="noopener noreferrer"
         class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface hover:bg-elevated border border-borderline text-xs font-medium text-slate-200 transition">
        <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24">
          <path fill-rule="evenodd" clip-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
        </svg>
        <span>GitHub</span>
      </a>
    </div>
  </header>

  <!-- Hero Section (Asymmetric 2-Column) -->
  <section class="py-16 sm:py-24 border-b border-borderline">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
        <div class="lg:col-span-6 pt-2">
          <h1 class="text-3xl sm:text-5xl font-bold tracking-tight text-slate-50 leading-[1.12] mb-5">
            Referentially-intact omnichannel retail datasets at warehouse scale.
          </h1>
          <p class="text-base text-slate-400 leading-relaxed max-w-[65ch] mb-8">
            Generate deterministic synthetic ecommerce data across 19 core tables and optional GDPR consent and entity-resolution ground-truth tables. Stream directly into DuckDB, Snowflake, Databricks Unity Catalog, or BigQuery without writing local Parquet files.
          </p>

          <div class="flex flex-wrap items-center gap-3 mb-10">
            <a href="#schema" class="px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition">
              Browse 21-Table Dictionary
            </a>
            <a href="#tiers" class="px-5 py-2.5 rounded-lg bg-surface hover:bg-elevated text-slate-200 text-sm font-medium border border-borderline transition">
              Configure CLI &amp; Scale
            </a>
          </div>

          <dl class="grid grid-cols-2 sm:grid-cols-4 gap-6 pt-6 border-t border-borderline">
            <div>
              <dt class="text-xs text-slate-400">Schema</dt>
              <dd class="text-lg font-semibold text-slate-100 tabular-nums mt-0.5">19 + 2 Tables</dd>
            </div>
            <div>
              <dt class="text-xs text-slate-400">Integrity</dt>
              <dd class="text-lg font-semibold text-emerald-400 tabular-nums mt-0.5">29 FK Checks</dd>
            </div>
            <div>
              <dt class="text-xs text-slate-400">Destinations</dt>
              <dd class="text-lg font-semibold text-slate-100 tabular-nums mt-0.5">4 Warehouses</dd>
            </div>
            <div>
              <dt class="text-xs text-slate-400">Max Scale</dt>
              <dd class="text-lg font-semibold text-slate-100 tabular-nums mt-0.5">500M+ Rows</dd>
            </div>
          </dl>
        </div>

        <!-- Tabbed Terminal -->
        <div class="lg:col-span-6 bg-surface rounded-xl border border-borderline overflow-hidden shadow-lg shadow-black/40">
          <div class="bg-elevated px-4 py-2.5 border-b border-borderline flex items-center justify-between gap-2">
            <span class="text-xs font-mono text-slate-400">cli-preview</span>
            <div class="flex items-center gap-1 text-xs font-mono">
              <button onclick="switchTerminalTab('stream')" id="term-tab-stream" class="px-2.5 py-1 rounded bg-indigo-600 text-white font-medium transition">Stream to DB</button>
              <button onclick="switchTerminalTab('generate')" id="term-tab-generate" class="px-2.5 py-1 rounded text-slate-400 hover:text-slate-100 transition">Chunked</button>
              <button onclick="switchTerminalTab('compliance')" id="term-tab-compliance" class="px-2.5 py-1 rounded text-slate-400 hover:text-slate-100 transition">Global</button>
              <button onclick="switchTerminalTab('validate')" id="term-tab-validate" class="px-2.5 py-1 rounded text-slate-400 hover:text-slate-100 transition">Validate</button>
            </div>
          </div>

          <div class="p-5 font-mono text-xs bg-canvas/80 text-slate-300 leading-relaxed overflow-x-auto min-h-[290px]">
            <div id="term-content-stream">
              <div class="flex items-center justify-between gap-2 mb-3">
                <span class="text-indigo-300">$ ecommerce-synth generate --tier large --stream-to snowflake --database ECOM_DB --schema PROD</span>
                <button onclick="copyCommand('ecommerce-synth generate --tier large --stream-to snowflake --database ECOM_DB --schema PROD')" class="text-slate-400 hover:text-white px-2 py-0.5 rounded border border-borderline bg-surface shrink-0">Copy</button>
              </div>
              <p class="text-slate-400">Streaming directly to Snowflake: ECOM_DB.PROD (0 local Parquet files)</p>
              <p class="text-emerald-400 mt-2">  ✓ Streamed customers — 500,000 rows</p>
              <p class="text-emerald-400">  ✓ Streamed orders_online — 1,000,000 rows (2 chunks)</p>
              <p class="text-emerald-400">  ✓ Streamed clickstream — 50,000,000 rows (100 chunks)</p>
              <p class="text-slate-400 mt-1">Applying 31 PII/financial column governance tags...</p>
              <p class="text-slate-400">Deploying views: v_omnichannel_sales, v_customer_360</p>
              <p class="text-slate-100 font-semibold mt-2">Direct Snowflake stream complete: 19 tables, 60.4M rows.</p>
            </div>

            <div id="term-content-generate" class="hidden">
              <div class="flex items-center justify-between gap-2 mb-3">
                <span class="text-indigo-300">$ ecommerce-synth generate --tier large --chunk-size 500000 --output ./output/large/</span>
                <button onclick="copyCommand('ecommerce-synth generate --tier large --chunk-size 500000 --output ./output/large/')" class="text-slate-400 hover:text-white px-2 py-0.5 rounded border border-borderline bg-surface shrink-0">Copy</button>
              </div>
              <p class="text-slate-400">Generation Configuration [Tier: LARGE | Chunk Size: 500,000 rows]</p>
              <p class="text-emerald-400 mt-2">  ✓ customers.parquet — 500,000 rows, 41.2 MB</p>
              <p class="text-emerald-400">  ✓ orders_online/ (2 chunks) — 1,000,000 rows, 74.8 MB</p>
              <p class="text-emerald-400">  ✓ clickstream/ (100 chunks) — 50,000,000 rows, 1.48 GB</p>
              <p class="text-slate-400 mt-2">Constant bounded RAM via ChunkedParquetWriter.</p>
            </div>

            <div id="term-content-compliance" class="hidden">
              <div class="flex items-center justify-between gap-2 mb-3">
                <span class="text-indigo-300">$ ecommerce-synth generate --tier medium --regions US,GB,DE,JP --compliance --identity-noise 0.15</span>
                <button onclick="copyCommand('ecommerce-synth generate --tier medium --regions US,GB,DE,JP --compliance --identity-noise 0.15')" class="text-slate-400 hover:text-white px-2 py-0.5 rounded border border-borderline bg-surface shrink-0">Copy</button>
              </div>
              <p class="text-slate-400">Regions: US, GB, DE, JP | Identity Noise: 15.0% | Compliance: GDPR/CCPA/APPI</p>
              <p class="text-emerald-400 mt-2">  ✓ customers.parquet — 50,000 rows (localized Faker + 2% DSAR tombstones)</p>
              <p class="text-emerald-400">  ✓ customer_consents.parquet — 150,000 consent records</p>
              <p class="text-emerald-400">  ✓ identity_ground_truth.parquet — 50,000 entity mappings</p>
            </div>

            <div id="term-content-validate" class="hidden">
              <div class="flex items-center justify-between gap-2 mb-3">
                <span class="text-indigo-300">$ ecommerce-synth validate ./output/medium/</span>
                <button onclick="copyCommand('ecommerce-synth validate ./output/medium/')" class="text-slate-400 hover:text-white px-2 py-0.5 rounded border border-borderline bg-surface shrink-0">Copy</button>
              </div>
              <p class="text-slate-400">Validating referential integrity across single &amp; chunked Parquet tables...</p>
              <p class="text-emerald-400 mt-2">  ✓ addresses.customer_id -> customers.customer_id (0 orphans)</p>
              <p class="text-emerald-400">  ✓ orders_online.session_id -> clickstream.session_id (100% linked)</p>
              <p class="text-emerald-400">  ✓ loyalty_transactions.source_order_id -> orders (100% linked)</p>
              <p class="text-slate-100 font-semibold mt-2">All referential integrity checks passed.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Core Capabilities (#features) -->
  <section id="features" class="py-20 border-b border-borderline bg-surface/40">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="max-w-2xl mb-12">
        <h2 class="text-2xl sm:text-3xl font-bold tracking-tight text-slate-50 mb-3">
          Engineered for global scale, streaming, and governance
        </h2>
        <p class="text-sm sm:text-base text-slate-400">
          Every generator is deterministic by seed, backed by Polars columnar execution, and aligned with warehouse governance requirements.
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-px bg-borderline border border-borderline rounded-xl overflow-hidden">
        <div class="bg-canvas p-7">
          <div class="flex items-center justify-between gap-3 mb-2.5">
            <div class="flex items-center gap-2.5">
              <svg class="w-4 h-4 text-indigo-400 shrink-0" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418"/></svg>
              <h3 class="text-base font-semibold text-slate-100">Global Multi-Region Localization</h3>
            </div>
            <code class="text-[11px] font-mono text-indigo-300 bg-elevated px-2 py-0.5 rounded border border-borderline">--regions global</code>
          </div>
          <p class="text-sm text-slate-400 leading-relaxed">
            Configurable country packs in <code class="font-mono text-slate-300">config/regions.yaml</code> (<code class="font-mono text-slate-300">US, GB, DE, FR, CA, JP, AU, BR</code>) with localized Faker names and addresses, ISO country codes, currencies, FX rates, and VAT vs. sales-tax rules.
          </p>
        </div>

        <div class="bg-canvas p-7">
          <div class="flex items-center justify-between gap-3 mb-2.5">
            <div class="flex items-center gap-2.5">
              <svg class="w-4 h-4 text-rose-400 shrink-0" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"/></svg>
              <h3 class="text-base font-semibold text-slate-100">GDPR / CCPA Consent &amp; PII Tags</h3>
            </div>
            <code class="text-[11px] font-mono text-rose-300 bg-elevated px-2 py-0.5 rounded border border-borderline">--compliance</code>
          </div>
          <p class="text-sm text-slate-400 leading-relaxed">
            Emits <code class="font-mono text-slate-300">customer_consents.parquet</code> across marketing, analytics, and personalization purposes plus 2% DSAR erasure tombstones. Compiles 31 <code class="font-mono text-slate-300">DIRECT_PII</code>, <code class="font-mono text-slate-300">INDIRECT_PII</code>, and <code class="font-mono text-slate-300">FINANCIAL</code> column tags into Snowflake &amp; Databricks DDL.
          </p>
        </div>

        <div class="bg-canvas p-7">
          <div class="flex items-center justify-between gap-3 mb-2.5">
            <div class="flex items-center gap-2.5">
              <svg class="w-4 h-4 text-emerald-400 shrink-0" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"/></svg>
              <h3 class="text-base font-semibold text-slate-100">Direct-to-Database Streaming</h3>
            </div>
            <code class="text-[11px] font-mono text-emerald-300 bg-elevated px-2 py-0.5 rounded border border-borderline">--stream-to</code>
          </div>
          <p class="text-sm text-slate-400 leading-relaxed">
            Stream generated DataFrame chunks straight into DuckDB, Snowflake (<code class="font-mono text-slate-300">write_pandas</code>), Databricks UC Volumes (in-memory buffers), or BigQuery (<code class="font-mono text-slate-300">LoadJob</code>) without saving local Parquet files.
          </p>
        </div>

        <div class="bg-canvas p-7">
          <div class="flex items-center justify-between gap-3 mb-2.5">
            <div class="flex items-center gap-2.5">
              <svg class="w-4 h-4 text-indigo-400 shrink-0" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6.429 9.75L2.25 12l4.179 2.25m0-4.5l5.571 3 5.571-3m-11.142 0L2.25 7.5 12 2.25l9.75 5.25-4.179 2.25m0 0L21.75 12l-4.179 2.25m0 0l4.179 2.25L12 21.75 2.25 16.5l4.179-2.25m11.142 0l-5.571 3-5.571-3"/></svg>
              <h3 class="text-base font-semibold text-slate-100">50M+ Chunked Parquet Persistence</h3>
            </div>
            <code class="text-[11px] font-mono text-indigo-300 bg-elevated px-2 py-0.5 rounded border border-borderline">--chunk-size</code>
          </div>
          <p class="text-sm text-slate-400 leading-relaxed">
            Streaming <code class="font-mono text-slate-300">ChunkedParquetWriter</code> flushes <code class="font-mono text-slate-300">table/part-00000.parquet</code> partitions every N rows (default 500K) to keep memory bounded during Large (50M) and XL (500M) runs.
          </p>
        </div>

        <div class="bg-canvas p-7">
          <div class="flex items-center justify-between gap-3 mb-2.5">
            <div class="flex items-center gap-2.5">
              <svg class="w-4 h-4 text-amber-400 shrink-0" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"/></svg>
              <h3 class="text-base font-semibold text-slate-100">Entity Resolution Messy-Data Mode</h3>
            </div>
            <code class="text-[11px] font-mono text-amber-300 bg-elevated px-2 py-0.5 rounded border border-borderline">--identity-noise</code>
          </div>
          <p class="text-sm text-slate-400 leading-relaxed">
            Injects realistic duplicate customer records (email aliases, phone reformatting, nicknames, typos, household splits) and outputs <code class="font-mono text-slate-300">identity_ground_truth.parquet</code> to benchmark Precision/Recall/F1.
          </p>
        </div>

        <div class="bg-canvas p-7">
          <div class="flex items-center justify-between gap-3 mb-2.5">
            <div class="flex items-center gap-2.5">
              <svg class="w-4 h-4 text-slate-300 shrink-0" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244"/></svg>
              <h3 class="text-base font-semibold text-slate-100">True Clickstream-to-Order Attribution</h3>
            </div>
            <code class="text-[11px] font-mono text-slate-300 bg-elevated px-2 py-0.5 rounded border border-borderline">session_id</code>
          </div>
          <p class="text-sm text-slate-400 leading-relaxed">
            100% of <code class="font-mono text-slate-300">orders_online.session_id</code> values link to complete clickstream purchase funnels ending at <code class="font-mono text-slate-300">order_date</code>, alongside <code class="font-mono text-slate-300">loyalty_transactions.source_order_id</code> linkage.
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- Volume Tiers & Interactive CLI Builder (#tiers) -->
  <section id="tiers" class="py-20 border-b border-borderline">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
        <div>
          <h2 class="text-2xl sm:text-3xl font-bold tracking-tight text-slate-50 mb-2">Volume Tiers &amp; CLI Builder</h2>
          <p class="text-sm text-slate-400">Inspect row counts per tier and compose a ready-to-run generation command.</p>
        </div>

        <div class="inline-flex p-1 rounded-lg bg-surface border border-borderline">
          <button onclick="selectTier('small')" id="tier-btn-small" class="px-4 py-1.5 rounded-md text-xs font-medium text-slate-400 hover:text-white transition">Small</button>
          <button onclick="selectTier('medium')" id="tier-btn-medium" class="px-4 py-1.5 rounded-md text-xs font-medium bg-indigo-600 text-white transition">Medium</button>
          <button onclick="selectTier('large')" id="tier-btn-large" class="px-4 py-1.5 rounded-md text-xs font-medium text-slate-400 hover:text-white transition">Large</button>
          <button onclick="selectTier('xl')" id="tier-btn-xl" class="px-4 py-1.5 rounded-md text-xs font-medium text-slate-400 hover:text-white transition">XL</button>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <!-- Tier Table -->
        <div class="lg:col-span-7 bg-surface border border-borderline rounded-xl overflow-hidden">
          <table class="w-full text-left border-collapse text-sm">
            <thead>
              <tr class="border-b border-borderline bg-elevated/60 text-xs font-medium text-slate-400">
                <th class="py-3 px-4">Domain Entity</th>
                <th class="py-3 px-4 text-right">Target Volume</th>
                <th class="py-3 px-4 text-right hidden sm:table-cell">Notes</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-borderline/70 tabular-nums">
              <tr><td class="py-2.5 px-4 text-slate-200">Customers</td><td id="stat-customers" class="py-2.5 px-4 text-right font-mono text-slate-100">50,000</td><td class="py-2.5 px-4 text-right text-xs text-slate-400 hidden sm:table-cell">7 behavioral personas</td></tr>
              <tr><td class="py-2.5 px-4 text-slate-200">Online Orders</td><td id="stat-online-orders" class="py-2.5 px-4 text-right font-mono text-slate-100">100,000</td><td class="py-2.5 px-4 text-right text-xs text-slate-400 hidden sm:table-cell">Linked to clickstream sessions</td></tr>
              <tr><td class="py-2.5 px-4 text-slate-200">In-Store POS Txns</td><td id="stat-store-txns" class="py-2.5 px-4 text-right font-mono text-slate-100">40,000</td><td class="py-2.5 px-4 text-right text-xs text-slate-400 hidden sm:table-cell">50 store locations</td></tr>
              <tr><td class="py-2.5 px-4 text-slate-200">Clickstream Events</td><td id="stat-clickstream" class="py-2.5 px-4 text-right font-mono text-indigo-300 font-medium">5,000,000</td><td class="py-2.5 px-4 text-right text-xs text-slate-400 hidden sm:table-cell">Auto-chunked above 500K</td></tr>
              <tr><td class="py-2.5 px-4 text-slate-200">Emails Delivered</td><td id="stat-emails" class="py-2.5 px-4 text-right font-mono text-slate-100">500,000</td><td class="py-2.5 px-4 text-right text-xs text-slate-400 hidden sm:table-cell">Open, click, bounce events</td></tr>
              <tr><td class="py-2.5 px-4 text-slate-200">Loyalty Members</td><td id="stat-loyalty" class="py-2.5 px-4 text-right font-mono text-slate-100">30,000</td><td class="py-2.5 px-4 text-right text-xs text-slate-400 hidden sm:table-cell">Bronze to Platinum</td></tr>
              <tr><td class="py-2.5 px-4 text-slate-200">Support Tickets</td><td id="stat-support" class="py-2.5 px-4 text-right font-mono text-slate-100">12,000</td><td class="py-2.5 px-4 text-right text-xs text-slate-400 hidden sm:table-cell">CSAT &amp; SLA timestamps</td></tr>
              <tr class="bg-elevated/30"><td class="py-2.5 px-4 font-medium text-slate-100">Estimated Parquet Size</td><td id="stat-size" class="py-2.5 px-4 text-right font-mono text-emerald-400 font-semibold">~350 MB</td><td class="py-2.5 px-4 text-right text-xs text-slate-400 hidden sm:table-cell">Snappy compressed</td></tr>
            </tbody>
          </table>
        </div>

        <!-- Interactive Command Builder -->
        <div class="lg:col-span-5 bg-surface border border-borderline rounded-xl p-6 flex flex-col justify-between">
          <div class="space-y-4">
            <h3 class="text-sm font-semibold text-slate-100">Compose Generation Command</h3>

            <div>
              <label for="cmd-mode-select" class="block text-xs text-slate-400 mb-1.5">Persistence / Delivery Mode</label>
              <select id="cmd-mode-select" onchange="updateGeneratedCommand()" class="w-full text-xs bg-canvas border border-borderline rounded-lg px-3 py-2 text-slate-200">
                <option value="parquet">Local Parquet (Chunked if &gt; 500K rows)</option>
                <option value="stream-duckdb">Direct Stream → DuckDB (0 local files)</option>
                <option value="stream-snowflake">Direct Stream → Snowflake (0 local files)</option>
                <option value="stream-databricks">Direct Stream → Databricks UC (0 local files)</option>
                <option value="stream-bigquery">Direct Stream → BigQuery (0 local files)</option>
              </select>
            </div>

            <div class="space-y-2.5 pt-1">
              <label class="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer">
                <input type="checkbox" id="opt-global" onchange="updateGeneratedCommand()" class="rounded border-borderline bg-canvas text-indigo-600">
                <span>Enable global regions (<code class="font-mono text-slate-400">--regions global</code>)</span>
              </label>
              <label class="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer">
                <input type="checkbox" id="opt-compliance" onchange="updateGeneratedCommand()" class="rounded border-borderline bg-canvas text-indigo-600">
                <span>Enable GDPR/CCPA consent ledger (<code class="font-mono text-slate-400">--compliance</code>)</span>
              </label>
              <label class="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer">
                <input type="checkbox" id="opt-identity" onchange="updateGeneratedCommand()" class="rounded border-borderline bg-canvas text-indigo-600">
                <span>Inject 15% entity-resolution noise (<code class="font-mono text-slate-400">--identity-noise 0.15</code>)</span>
              </label>
            </div>
          </div>

          <div class="mt-6">
            <div class="bg-canvas border border-borderline rounded-lg p-3 font-mono text-xs text-indigo-300 break-all mb-3" id="generated-command-display">
              ecommerce-synth generate --tier medium --chunk-size 500000
            </div>
            <button onclick="copyGeneratedCommand()" class="w-full py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition">
              Copy Command
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Interactive 21-Table Schema & Data Dictionary (#schema) -->
  <section id="schema" class="py-20 border-b border-borderline bg-surface/40">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
        <div>
          <h2 class="text-2xl sm:text-3xl font-bold tracking-tight text-slate-50 mb-2">Schema &amp; Data Dictionary (21 Tables)</h2>
          <p class="text-sm text-slate-400 max-w-2xl">
            19 core omnichannel tables plus 2 optional governance and entity-resolution tables (<code class="font-mono text-slate-300">customer_consents</code>, <code class="font-mono text-slate-300">identity_ground_truth</code>) defined in <code class="font-mono text-slate-300">config/schema.json</code>.
          </p>
        </div>

        <div class="w-full md:w-72">
          <input type="text" id="schema-search" oninput="filterSchema()" placeholder="Filter tables or columns..."
                 class="w-full bg-canvas border border-borderline rounded-lg px-3.5 py-2 text-xs text-slate-200 placeholder-slate-500">
        </div>
      </div>

      <!-- Domain Filter Pills -->
      <div class="flex flex-wrap gap-2 mb-8">
        <button onclick="filterDomain('all')" id="domain-pill-all" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-indigo-600 text-white transition">All (21)</button>
        <button onclick="filterDomain('Omnichannel Sales & POS')" id="domain-pill-sales" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-surface text-slate-300 hover:text-white border border-borderline transition">Sales &amp; POS (6)</button>
        <button onclick="filterDomain('Customer 360 & Identity')" id="domain-pill-cust" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-surface text-slate-300 hover:text-white border border-borderline transition">Customer 360 (4)</button>
        <button onclick="filterDomain('Engagement & Retention')" id="domain-pill-eng" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-surface text-slate-300 hover:text-white border border-borderline transition">Engagement (6)</button>
        <button onclick="filterDomain('Experimentation & Fraud')" id="domain-pill-fraud" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-surface text-slate-300 hover:text-white border border-borderline transition">Experiments &amp; Fraud (3)</button>
        <button onclick="filterDomain('Governance & Compliance')" id="domain-pill-gov" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-surface text-slate-300 hover:text-white border border-borderline transition">Governance &amp; ER (2)</button>
      </div>

      <div id="schema-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        <!-- Rendered via JS -->
      </div>
    </div>
  </section>

  <!-- Multi-Warehouse Exporters (#warehouses) -->
  <section id="warehouses" class="py-20 border-b border-borderline">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="max-w-2xl mb-10">
        <h2 class="text-2xl sm:text-3xl font-bold tracking-tight text-slate-50 mb-2">Multi-Warehouse Exporters &amp; Direct Streaming</h2>
        <p class="text-sm text-slate-400">Load staged Parquet chunks via <code class="font-mono text-slate-300">export</code> or stream directly from memory via <code class="font-mono text-slate-300">--stream-to</code>, complete with PK/FK constraints, PII governance tags, and analytical views.</p>
      </div>

      <div class="bg-surface border border-borderline rounded-xl overflow-hidden">
        <div class="grid grid-cols-2 sm:grid-cols-4 border-b border-borderline bg-elevated/60 text-xs font-medium">
          <button onclick="switchWhTab('databricks')" id="wh-tab-databricks" class="py-3 px-4 border-b-2 border-indigo-500 text-white bg-surface transition">Databricks Unity Catalog</button>
          <button onclick="switchWhTab('snowflake')" id="wh-tab-snowflake" class="py-3 px-4 border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition">Snowflake</button>
          <button onclick="switchWhTab('bigquery')" id="wh-tab-bigquery" class="py-3 px-4 border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition">Google BigQuery</button>
          <button onclick="switchWhTab('duckdb')" id="wh-tab-duckdb" class="py-3 px-4 border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition">DuckDB</button>
        </div>

        <div class="p-6 sm:p-8">
          <div id="wh-content-databricks" class="grid grid-cols-1 lg:grid-cols-12 gap-8">
            <div class="lg:col-span-4 space-y-3 text-xs text-slate-400">
              <h3 class="text-base font-semibold text-slate-100">Databricks Unity Catalog</h3>
              <p>Stages single or chunked Parquet directories to UC Volumes (or streams in-memory Parquet buffers), executes <code class="font-mono text-slate-300">read_files()</code> Delta CTAS, and applies UC column governance tags.</p>
            </div>
            <div class="lg:col-span-8 bg-canvas border border-borderline rounded-lg p-4 font-mono text-xs text-slate-300 overflow-x-auto">
              <div class="text-slate-500 mb-1"># Direct stream or export</div>
              <div class="text-indigo-300 mb-3">$ ecommerce-synth generate --tier large --stream-to databricks --catalog dev --schema ecom</div>
              <div class="text-slate-500 mb-1">-- Governance tags applied automatically</div>
              <div class="text-emerald-300">ALTER TABLE dev.ecom.customers ALTER COLUMN email SET TAGS ('pii_classification' = 'DIRECT_PII', 'sensitivity' = 'HIGH');</div>
            </div>
          </div>

          <div id="wh-content-snowflake" class="hidden grid grid-cols-1 lg:grid-cols-12 gap-8">
            <div class="lg:col-span-4 space-y-3 text-xs text-slate-400">
              <h3 class="text-base font-semibold text-slate-100">Snowflake</h3>
              <p>Supports both internal stage <code class="font-mono text-slate-300">PUT</code> + <code class="font-mono text-slate-300">COPY INTO</code> and zero-file <code class="font-mono text-slate-300">write_pandas</code> streaming, with auto-discovered <code class="font-mono text-slate-300">connections.toml</code> profiles, 4h MFA token caching, and <code class="font-mono text-slate-300">MODIFY COLUMN ... SET TAG</code>.</p>
            </div>
            <div class="lg:col-span-8 bg-canvas border border-borderline rounded-lg p-4 font-mono text-xs text-slate-300 overflow-x-auto">
              <div class="text-slate-500 mb-1"># Direct stream without local Parquet</div>
              <div class="text-indigo-300 mb-3">$ ecommerce-synth generate --tier large --stream-to snowflake --database ECOM_DB --schema PROD</div>
              <div class="text-slate-500 mb-1">-- Governance tags applied automatically</div>
              <div class="text-emerald-300">ALTER TABLE ECOM_DB.PROD.customers MODIFY COLUMN email SET TAG pii_classification = 'DIRECT_PII', sensitivity = 'HIGH';</div>
            </div>
          </div>

          <div id="wh-content-bigquery" class="hidden grid grid-cols-1 lg:grid-cols-12 gap-8">
            <div class="lg:col-span-4 space-y-3 text-xs text-slate-400">
              <h3 class="text-base font-semibold text-slate-100">Google Cloud BigQuery</h3>
              <p>Streams DataFrames directly via <code class="font-mono text-slate-300">load_table_from_dataframe</code> or stages chunked Parquet files to GCS with native <code class="font-mono text-slate-300">LoadJob</code> ingestion and un-enforced PK/FK constraints.</p>
            </div>
            <div class="lg:col-span-8 bg-canvas border border-borderline rounded-lg p-4 font-mono text-xs text-slate-300 overflow-x-auto">
              <div class="text-slate-500 mb-1"># Direct stream to BigQuery</div>
              <div class="text-indigo-300 mb-3">$ ecommerce-synth generate --tier medium --stream-to bigquery --project my-gcp-project --dataset ecom</div>
              <div class="text-slate-500 mb-1">-- Analytical view deployed</div>
              <div class="text-emerald-300">CREATE OR REPLACE VIEW `my-gcp-project.ecom.v_customer_360` AS ...</div>
            </div>
          </div>

          <div id="wh-content-duckdb" class="hidden grid grid-cols-1 lg:grid-cols-12 gap-8">
            <div class="lg:col-span-4 space-y-3 text-xs text-slate-400">
              <h3 class="text-base font-semibold text-slate-100">DuckDB</h3>
              <p>Zero-copy Polars registration via <code class="font-mono text-slate-300">--stream-to duckdb</code> or multi-part <code class="font-mono text-slate-300">read_parquet([...])</code> export with custom <code class="font-mono text-slate-300">--schema</code> support.</p>
            </div>
            <div class="lg:col-span-8 bg-canvas border border-borderline rounded-lg p-4 font-mono text-xs text-slate-300 overflow-x-auto">
              <div class="text-slate-500 mb-1"># Stream directly into a custom schema</div>
              <div class="text-indigo-300 mb-3">$ ecommerce-synth generate --tier medium --stream-to duckdb --database ./live.duckdb --schema retail</div>
              <div class="text-slate-500 mb-1">-- Query immediately</div>
              <div class="text-emerald-300">SELECT channel, COUNT(*) AS txns, SUM(total_amount) AS gmv FROM retail.v_omnichannel_sales GROUP BY 1;</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Behavioral Personas Matrix (#personas) -->
  <section id="personas" class="py-20 border-b border-borderline bg-surface/40">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="max-w-2xl mb-10">
        <h2 class="text-2xl sm:text-3xl font-bold tracking-tight text-slate-50 mb-2">Behavioral Customer Personas &amp; Fraud Vectors</h2>
        <p class="text-sm text-slate-400">Activity across orders, clickstream, email engagement, loyalty, and fraud anomalies is driven by 7 empirical personas in <code class="font-mono text-slate-300">persona.py</code>.</p>
      </div>

      <div class="bg-surface border border-borderline rounded-xl overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs sm:text-sm">
          <thead>
            <tr class="border-b border-borderline bg-elevated/60 text-xs font-medium text-slate-400">
              <th class="py-3 px-4">Persona</th>
              <th class="py-3 px-4 text-right">Share</th>
              <th class="py-3 px-4">Orders / Yr</th>
              <th class="py-3 px-4">Browse-to-Buy</th>
              <th class="py-3 px-4">Behavioral Profile</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-borderline/70 tabular-nums">
            <tr><td class="py-3 px-4 font-medium text-slate-100">Power Shopper</td><td class="py-3 px-4 text-right font-mono text-slate-300">5%</td><td class="py-3 px-4 font-mono text-slate-300">15–25</td><td class="py-3 px-4 font-mono text-emerald-400">10.0%</td><td class="py-3 px-4 text-slate-400">High AOV, omnichannel buyer, Gold/Platinum loyalty, 45% email open rate.</td></tr>
            <tr><td class="py-3 px-4 font-medium text-slate-100">Regular</td><td class="py-3 px-4 text-right font-mono text-slate-300">25%</td><td class="py-3 px-4 font-mono text-slate-300">4–8</td><td class="py-3 px-4 font-mono text-slate-300">4.0%</td><td class="py-3 px-4 text-slate-400">Consistent bi-weekly/monthly orders across 2 preferred categories.</td></tr>
            <tr><td class="py-3 px-4 font-medium text-slate-100">Occasional</td><td class="py-3 px-4 text-right font-mono text-slate-300">40%</td><td class="py-3 px-4 font-mono text-slate-300">1–3</td><td class="py-3 px-4 font-mono text-slate-300">2.0%</td><td class="py-3 px-4 text-slate-400">Seasonal peak shopper (Q4 holidays, back-to-school), Bronze/Silver tier.</td></tr>
            <tr><td class="py-3 px-4 font-medium text-slate-100">Bargain Hunter</td><td class="py-3 px-4 text-right font-mono text-slate-300">15%</td><td class="py-3 px-4 font-mono text-slate-300">3–6</td><td class="py-3 px-4 font-mono text-slate-300">4.0%</td><td class="py-3 px-4 text-slate-400">Always applies coupon codes, higher return rate (12%), shops across categories.</td></tr>
            <tr><td class="py-3 px-4 font-medium text-slate-100">One-and-Done</td><td class="py-3 px-4 text-right font-mono text-slate-300">10%</td><td class="py-3 px-4 font-mono text-slate-300">1</td><td class="py-3 px-4 font-mono text-slate-300">0.5%</td><td class="py-3 px-4 text-slate-400">Single impulse checkout, no loyalty enrollment, 50% churned status.</td></tr>
            <tr><td class="py-3 px-4 font-medium text-slate-100">Window Shopper</td><td class="py-3 px-4 text-right font-mono text-slate-300">5%</td><td class="py-3 px-4 font-mono text-slate-300">0</td><td class="py-3 px-4 font-mono text-slate-500">0.0%</td><td class="py-3 px-4 text-slate-400">High clickstream browsing &amp; cart abandonment, zero completed orders.</td></tr>
            <tr><td class="py-3 px-4 font-medium text-rose-300">Fraudster</td><td class="py-3 px-4 text-right font-mono text-rose-300">~2%</td><td class="py-3 px-4 font-mono text-rose-300">Spike</td><td class="py-3 px-4 font-mono text-rose-300">70.0%</td><td class="py-3 px-4 text-slate-400">Card testing, account takeover, promo/refund abuse, synthetic identity labeled in <code class="font-mono text-slate-300">fraud_flags</code>.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>

  <!-- Quickstart (#quickstart) -->
  <section id="quickstart" class="py-20">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="max-w-2xl mb-10">
        <h2 class="text-2xl sm:text-3xl font-bold tracking-tight text-slate-50 mb-2">Quickstart &amp; CLI Reference</h2>
        <p class="text-sm text-slate-400">Install with optional warehouse connectors and run locally in Python 3.11+.</p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="bg-surface border border-borderline rounded-xl p-6 space-y-3 font-mono text-xs text-slate-300">
          <div class="text-xs font-sans font-semibold text-slate-100 mb-2">Installation</div>
          <div class="bg-canvas p-3 rounded-lg border border-borderline flex items-center justify-between gap-2">
            <span>pip install -e ".[dev]"</span>
            <button onclick="copyCommand('pip install -e &quot;.[dev]&quot;')" class="text-slate-400 hover:text-white shrink-0">Copy</button>
          </div>
          <div class="bg-canvas p-3 rounded-lg border border-borderline flex items-center justify-between gap-2">
            <span>pip install -e ".[all-targets]"</span>
            <button onclick="copyCommand('pip install -e &quot;.[all-targets]&quot;')" class="text-slate-400 hover:text-white shrink-0">Copy</button>
          </div>
        </div>

        <div class="bg-surface border border-borderline rounded-xl p-6 space-y-3 font-mono text-xs text-slate-300">
          <div class="text-xs font-sans font-semibold text-slate-100 mb-2">Common Workflows</div>
          <div class="bg-canvas p-3 rounded-lg border border-borderline">
            <span class="text-slate-500 block mb-0.5"># Stream 50M+ scale directly to Snowflake (no local Parquet)</span>
            <span class="text-indigo-300">ecommerce-synth generate --tier large --stream-to snowflake --database ECOM_DB --schema PROD</span>
          </div>
          <div class="bg-canvas p-3 rounded-lg border border-borderline">
            <span class="text-slate-500 block mb-0.5"># Global regions + GDPR consent + 15% entity-resolution noise</span>
            <span class="text-emerald-300">ecommerce-synth generate --tier medium --regions US,GB,DE,JP --compliance --identity-noise 0.15</span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Footer -->
  <footer class="py-10 border-t border-borderline text-slate-400 text-xs">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
      <div class="font-mono text-slate-400">ecommerce-synth · Apache-2.0</div>
      <div class="flex items-center gap-6">
        <a href="https://github.com/anilkulkarni87/ecommerce_synthetic" target="_blank" rel="noopener noreferrer" class="hover:text-slate-100 transition">Repository</a>
        <a href="#schema" class="hover:text-slate-100 transition">Schema Dictionary</a>
      </div>
    </div>
  </footer>

  <!-- Toast -->
  <div id="copy-toast" class="fixed bottom-5 right-5 z-50 px-3.5 py-2 rounded-lg bg-elevated border border-borderline text-slate-100 text-xs font-medium shadow-xl transform translate-y-16 opacity-0 transition-all duration-200 pointer-events-none">
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

    function selectTier(tierKey) {
      currentTier = tierKey;
      ['small', 'medium', 'large', 'xl'].forEach(k => {
        const btn = document.getElementById('tier-btn-' + k);
        btn.className = k === tierKey
          ? "px-4 py-1.5 rounded-md text-xs font-medium bg-indigo-600 text-white transition"
          : "px-4 py-1.5 rounded-md text-xs font-medium text-slate-400 hover:text-white transition";
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
      const mode = document.getElementById('cmd-mode-select').value;
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
          btn.className = "px-2.5 py-1 rounded bg-indigo-600 text-white font-medium transition";
          content.classList.remove('hidden');
        } else {
          btn.className = "px-2.5 py-1 rounded text-slate-400 hover:text-slate-100 transition";
          content.classList.add('hidden');
        }
      });
    }

    function switchWhTab(targetId) {
      ['databricks', 'snowflake', 'bigquery', 'duckdb'].forEach(t => {
        const btn = document.getElementById('wh-tab-' + t);
        const content = document.getElementById('wh-content-' + t);
        if (t === targetId) {
          btn.className = "py-3 px-4 border-b-2 border-indigo-500 text-white bg-surface transition";
          content.classList.remove('hidden');
        } else {
          btn.className = "py-3 px-4 border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition";
          content.classList.add('hidden');
        }
      });
    }

    function getTypeColorClass(typeStr) {
      const t = typeStr.toLowerCase();
      if (t.includes('uuid')) return 'text-indigo-300';
      if (t.includes('timestamp') || t.includes('date')) return 'text-cyan-300';
      if (t.includes('int') || t.includes('float')) return 'text-amber-300';
      if (t.includes('bool')) return 'text-emerald-300';
      return 'text-slate-300';
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
          if (pii === 'DIRECT_PII') piiBadge = '<span class="ml-1 text-[9px] px-1 bg-rose-500/20 text-rose-300 rounded font-semibold">PII:HIGH</span>';
          else if (pii === 'INDIRECT_PII') piiBadge = '<span class="ml-1 text-[9px] px-1 bg-amber-500/20 text-amber-300 rounded font-semibold">PII:MED</span>';
          else if (pii === 'FINANCIAL') piiBadge = '<span class="ml-1 text-[9px] px-1 bg-emerald-500/20 text-emerald-300 rounded font-semibold">FIN</span>';

          columnsHtml += `
            <tr class="border-b border-borderline/60 last:border-0 text-[11px]">
              <td class="py-2 pr-2 font-mono text-slate-200">
                ${cname}
                ${isPK ? '<span class="ml-1 text-[9px] px-1 bg-amber-500/20 text-amber-300 rounded font-semibold">PK</span>' : ''}
                ${isFK ? '<span class="ml-1 text-[9px] px-1 bg-cyan-500/20 text-cyan-300 rounded font-semibold">FK</span>' : ''}
                ${piiBadge}
              </td>
              <td class="py-2 px-2 font-mono ${getTypeColorClass(cinfo.type)}">${cinfo.type}</td>
              <td class="py-2 px-2 text-slate-400">${cinfo.nullable ? 'NULL' : 'NOT NULL'}</td>
              <td class="py-2 pl-2 text-slate-400 max-w-[140px] truncate" title="${cinfo.description}">${cinfo.description}</td>
            </tr>
          `;
        }

        const card = document.createElement('div');
        card.className = "bg-surface border border-borderline rounded-xl p-5 flex flex-col justify-between";
        card.innerHTML = `
          <div>
            <div class="flex items-start justify-between gap-2 mb-2">
              <div>
                <h3 class="text-sm font-semibold text-slate-100 font-mono flex items-center gap-2">
                  <span>${tname}</span>
                  ${tinfo.is_optional ? `<span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/25">${tinfo.optional_flag}</span>` : ''}
                </h3>
                <span class="text-[11px] text-slate-400">${tinfo.domain}</span>
              </div>
              <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-canvas border border-borderline text-slate-400">${tinfo.file}</span>
            </div>
            <p class="text-xs text-slate-400 mb-4 leading-relaxed">${tinfo.description}</p>
            <div class="flex flex-wrap gap-1.5 text-[11px] font-mono mb-3">
              <span class="px-2 py-0.5 rounded bg-canvas border border-borderline text-slate-300">Cols: ${colCount}</span>
              <span class="px-2 py-0.5 rounded bg-canvas border border-borderline text-amber-300">PK: ${pk}</span>
              ${fkCount > 0 ? `<span class="px-2 py-0.5 rounded bg-canvas border border-borderline text-cyan-300">FKs: ${fkCount}</span>` : ''}
              ${piiCount > 0 ? `<span class="px-2 py-0.5 rounded bg-canvas border border-borderline text-rose-300">Tags: ${piiCount}</span>` : ''}
            </div>
          </div>

          <div>
            <div id="cols-container-${tname}" class="hidden mt-3 pt-3 border-t border-borderline overflow-x-auto max-h-64">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="text-[10px] uppercase font-semibold text-slate-500 border-b border-borderline">
                    <th class="pb-1.5 pr-2">Column</th>
                    <th class="pb-1.5 px-2">Type</th>
                    <th class="pb-1.5 px-2">Null</th>
                    <th class="pb-1.5 pl-2">Description</th>
                  </tr>
                </thead>
                <tbody>${columnsHtml}</tbody>
              </table>
            </div>
            <button onclick="toggleTableDetails('${tname}')" id="toggle-btn-${tname}"
                    class="w-full mt-2 py-1.5 rounded-lg bg-elevated hover:bg-canvas text-slate-300 hover:text-white text-xs font-medium border border-borderline transition">
              View ${colCount} Columns
            </button>
          </div>
        `;
        container.appendChild(card);
      }

      if (container.children.length === 0) {
        container.innerHTML = `<div class="col-span-full py-12 text-center text-sm text-slate-400">No matching tables found.</div>`;
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
        document.getElementById(id).className = "px-3.5 py-1.5 rounded-lg text-xs font-medium bg-surface text-slate-300 hover:text-white border border-borderline transition";
      });
      document.getElementById(map[domainName]).className = "px-3.5 py-1.5 rounded-lg text-xs font-medium bg-indigo-600 text-white transition";
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
