#!/usr/bin/env python3
"""Builds docs/index.html with embedded schema and interactive components."""

import json
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
schema_file = repo_root / "config" / "schema.json"

with open(schema_file) as f:
    schema = json.load(f)

# Table domain mappings
DOMAINS = {
    "orders_online": "Omnichannel Sales & POS",
    "order_items_online": "Omnichannel Sales & POS",
    "orders_instore": "Omnichannel Sales & POS",
    "order_items_instore": "Omnichannel Sales & POS",
    "stores": "Omnichannel Sales & POS",
    "products": "Omnichannel Sales & POS",
    "customers": "Customer 360 & Demographics",
    "addresses": "Customer 360 & Demographics",
    "instore_accounts": "Customer 360 & Demographics",
    "loyalty_members": "Customer 360 & Demographics",
    "clickstream": "Engagement & Retention",
    "email_campaigns": "Engagement & Retention",
    "email_events": "Engagement & Retention",
    "loyalty_transactions": "Engagement & Retention",
    "reviews": "Engagement & Retention",
    "support_tickets": "Engagement & Retention",
    "experiments": "Experimentation & Fraud",
    "experiment_assignments": "Experimentation & Fraud",
    "fraud_flags": "Experimentation & Fraud",
}

# Attach domain to schema
for tname, tinfo in schema["tables"].items():
    tinfo["domain"] = DOMAINS.get(tname, "General")

schema_json_str = json.dumps(schema, indent=2)

html_template = '''<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ecommerce Synthetic Data Generator | Enterprise Omnichannel Datasets</title>
  <meta name="description" content="A realistic, referentially-intact omnichannel synthetic ecommerce data generator for Apache Parquet, Databricks Unity Catalog, Snowflake, BigQuery, and DuckDB.">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🛒</text></svg>">
  
  <!-- Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      darkMode: 'class',
      theme: {{
        extend: {{
          fontFamily: {{
            sans: ['Inter', 'sans-serif'],
            mono: ['Fira Code', 'monospace'],
          }},
          colors: {{
            brand: {{
              50: '#eef2ff',
              100: '#e0e7ff',
              400: '#818cf8',
              500: '#6366f1',
              600: '#4f46e5',
              700: '#4338ca',
            }},
            surface: {{
              900: '#060913',
              850: '#0b1120',
              800: '#111827',
              700: '#1e293b',
              600: '#334155',
            }}
          }}
        }}
      }}
    }}
  </script>

  <style>
    /* Custom Scrollbar */
    ::-webkit-scrollbar {{
      width: 8px;
      height: 8px;
    }}
    ::-webkit-scrollbar-track {{
      background: #060913;
    }}
    ::-webkit-scrollbar-thumb {{
      background: #1e293b;
      border-radius: 4px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
      background: #334155;
    }}

    .glass-card {{
      background: rgba(11, 17, 32, 0.75);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.08);
    }}

    .glass-card:hover {{
      border-color: rgba(99, 102, 241, 0.35);
    }}

    .code-glow {{
      box-shadow: 0 0 50px -10px rgba(99, 102, 241, 0.15);
    }}

    .gradient-text {{
      background: linear-gradient(135deg, #a5b4fc 0%, #6366f1 50%, #38bdf8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}

    .glow-cyan {{
      box-shadow: 0 0 40px -10px rgba(56, 189, 248, 0.2);
    }}
  </style>
</head>
<body class="bg-surface-900 text-slate-100 font-sans antialiased selection:bg-brand-500 selection:text-white">

  <!-- Header / Navigation -->
  <header class="sticky top-0 z-50 glass-card border-b border-surface-700/60 bg-surface-900/80 backdrop-blur-md">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-cyan-500 p-0.5 shadow-lg shadow-brand-500/20 flex items-center justify-center">
          <div class="w-full h-full bg-surface-900 rounded-[10px] flex items-center justify-center">
            <span class="text-xl">🛒</span>
          </div>
        </div>
        <div>
          <span class="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-brand-400 bg-clip-text text-transparent">ecommerce-synth</span>
          <span class="ml-2 px-2 py-0.5 text-xs font-semibold rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">v1.0.0</span>
        </div>
      </div>

      <nav class="hidden md:flex items-center gap-7 text-sm font-medium text-slate-300">
        <a href="#features" class="hover:text-white transition">Features</a>
        <a href="#tiers" class="hover:text-white transition">Volume Tiers</a>
        <a href="#schema" class="hover:text-white transition flex items-center gap-1.5">
          <span>Schema</span>
          <span class="text-xs px-1.5 py-0.2 bg-surface-700 rounded text-brand-300 font-mono">19</span>
        </a>
        <a href="#warehouses" class="hover:text-white transition">Exporters</a>
        <a href="#personas" class="hover:text-white transition">Personas</a>
        <a href="#quickstart" class="hover:text-white transition">Quickstart</a>
      </nav>

      <div class="flex items-center gap-3">
        <a href="https://github.com/anilkulkarni87/ecommerce_synthetic" target="_blank" rel="noopener noreferrer" 
           class="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-800 hover:bg-surface-700 border border-slate-700 text-sm font-medium text-slate-200 transition shadow-sm hover:shadow">
          <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24">
            <path fill-rule="evenodd" clip-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
          </svg>
          <span>Star on GitHub</span>
        </a>
      </div>
    </div>
  </header>

  <!-- Hero Section -->
  <section class="relative pt-20 pb-28 overflow-hidden">
    <!-- Ambient Background Glows -->
    <div class="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[350px] bg-brand-500/15 blur-[120px] rounded-full pointer-events-none"></div>
    <div class="absolute top-1/3 left-1/4 w-[400px] h-[300px] bg-cyan-500/10 blur-[100px] rounded-full pointer-events-none"></div>

    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
      <div class="text-center max-w-3xl mx-auto mb-14">
        <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-300 text-xs font-semibold mb-6">
          <span class="flex h-2 w-2 relative">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          Production-Ready Synthetic Retail Lakehouse
        </div>
        
        <h1 class="text-4xl sm:text-6xl font-extrabold tracking-tight mb-6 leading-tight">
          Omnichannel Ecommerce Data <br>
          <span class="gradient-text">at Enterprise Scale</span>
        </h1>
        
        <p class="text-lg sm:text-xl text-slate-400 font-normal leading-relaxed mb-8">
          A high-performance synthetic data generator creating referentially-intact omnichannel retail datasets across 
          <span class="text-slate-200 font-semibold">19 relational tables</span>. Models in-store POS, online checkouts, clickstream funnels, 7 customer personas, and automated multi-warehouse loading.
        </p>

        <div class="flex flex-wrap items-center justify-center gap-4">
          <a href="#quickstart" class="px-6 py-3.5 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-semibold shadow-lg shadow-brand-500/25 transition flex items-center gap-2">
            <span>Get Started with CLI</span>
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
          </a>
          <a href="#schema" class="px-6 py-3.5 rounded-xl bg-surface-800 hover:bg-surface-700 text-slate-200 font-semibold border border-surface-600/60 transition flex items-center gap-2">
            <span>Explore 19-Table Schema</span>
            <span class="px-2 py-0.5 text-xs bg-brand-500/20 text-brand-300 rounded font-mono">Interactive</span>
          </a>
        </div>
      </div>

      <!-- Stats Bar -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto mb-16">
        <div class="glass-card p-5 rounded-2xl text-center">
          <div class="text-3xl font-extrabold text-white mb-1">19 Tables</div>
          <div class="text-xs text-slate-400 font-medium">Complete Data Catalog</div>
        </div>
        <div class="glass-card p-5 rounded-2xl text-center">
          <div class="text-3xl font-extrabold text-emerald-400 mb-1">29 Invariants</div>
          <div class="text-xs text-slate-400 font-medium">100% Referential Integrity</div>
        </div>
        <div class="glass-card p-5 rounded-2xl text-center">
          <div class="text-3xl font-extrabold text-cyan-400 mb-1">4 Destinations</div>
          <div class="text-xs text-slate-400 font-medium">Databricks, Snowflake, BQ, DuckDB</div>
        </div>
        <div class="glass-card p-5 rounded-2xl text-center">
          <div class="text-3xl font-extrabold text-brand-400 mb-1">Up to 500M+</div>
          <div class="text-xs text-slate-400 font-medium">Event Scale (Small to XL)</div>
        </div>
      </div>

      <!-- Interactive Hero Terminal -->
      <div class="max-w-4xl mx-auto glass-card rounded-2xl overflow-hidden code-glow border border-surface-700/80 shadow-2xl">
        <div class="bg-surface-850 px-4 py-3 border-b border-surface-700/80 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="w-3 h-3 rounded-full bg-red-500/80"></span>
            <span class="w-3 h-3 rounded-full bg-yellow-500/80"></span>
            <span class="w-3 h-3 rounded-full bg-green-500/80"></span>
            <span class="ml-2 text-xs font-mono text-slate-400">bash — ecommerce-synth demo</span>
          </div>
          <!-- Terminal Tabs -->
          <div class="flex items-center gap-1 bg-surface-900 p-1 rounded-lg border border-surface-700/60 text-xs font-mono">
            <button onclick="switchTerminalTab('generate')" id="term-tab-generate" class="px-2.5 py-1 rounded bg-brand-600 text-white font-medium transition">1. Generate</button>
            <button onclick="switchTerminalTab('export')" id="term-tab-export" class="px-2.5 py-1 rounded text-slate-400 hover:text-white transition">2. Export</button>
            <button onclick="switchTerminalTab('validate')" id="term-tab-validate" class="px-2.5 py-1 rounded text-slate-400 hover:text-white transition">3. Validate</button>
            <button onclick="switchTerminalTab('stream')" id="term-tab-stream" class="px-2.5 py-1 rounded text-slate-400 hover:text-white transition">4. Stream</button>
          </div>
        </div>

        <div class="p-6 font-mono text-xs sm:text-sm bg-surface-900/90 text-slate-300 leading-relaxed overflow-x-auto min-h-[300px]">
          <!-- Tab 1: Generate -->
          <div id="term-content-generate">
            <div class="flex items-center justify-between text-slate-400 mb-2">
              <span class="text-brand-400">$ ecommerce-synth generate --tier medium --output ./output/medium/</span>
              <button onclick="copyCommand('ecommerce-synth generate --tier medium --output ./output/medium/')" class="hover:text-white text-xs px-2 py-0.5 rounded bg-surface-800 border border-slate-700">Copy</button>
            </div>
            <p class="text-slate-500">── Generating Omnichannel Ecommerce Dataset [tier=medium, seed=42] ──</p>
            <p class="text-cyan-400">  [1/11] Generating products catalog (2,000 SKUs)... <span class="text-emerald-400">✓ Done</span></p>
            <p class="text-cyan-400">  [2/11] Generating stores dimension (50 locations)... <span class="text-emerald-400">✓ Done</span></p>
            <p class="text-cyan-400">  [3/11] Generating 50,000 customers with 7 behavioral personas... <span class="text-emerald-400">✓ Done</span></p>
            <p class="text-cyan-400">  [4/11] Generating physical shipping & billing addresses... <span class="text-emerald-400">✓ Done</span></p>
            <p class="text-cyan-400">  [5/11] Simulating 100,000 online checkouts & 240,000 line items... <span class="text-emerald-400">✓ Done</span></p>
            <p class="text-cyan-400">  [6/11] Simulating 40,000 store POS transactions & in-store accounts... <span class="text-emerald-400">✓ Done</span></p>
            <p class="text-cyan-400">  [7/11] Generating 5,000,000 clickstream conversion events... <span class="text-emerald-400">✓ Done</span></p>
            <p class="text-cyan-400">  [8/11] Simulating loyalty program & point ledger transactions... <span class="text-emerald-400">✓ Done</span></p>
            <p class="text-cyan-400">  [9/11] Injecting fraud anomalies (card testing, ATO, promo abuse)... <span class="text-emerald-400">✓ Done</span></p>
            <p class="text-emerald-400 font-bold mt-2">✓ Success: All 19 Parquet tables serialized with Snappy compression (342.6 MB in 18.4s)</p>
          </div>

          <!-- Tab 2: Export -->
          <div id="term-content-export" class="hidden">
            <div class="flex items-center justify-between text-slate-400 mb-2">
              <span class="text-brand-400">$ ecommerce-synth export ./output/medium/ --target snowflake --database ECOM_DB --schema PROD</span>
              <button onclick="copyCommand('ecommerce-synth export ./output/medium/ --target snowflake --database ECOM_DB --schema PROD')" class="hover:text-white text-xs px-2 py-0.5 rounded bg-surface-800 border border-slate-700">Copy</button>
            </div>
            <p class="text-cyan-300">❄️  Exporting to Snowflake: ECOM_DB.PROD</p>
            <p class="text-slate-400">📦 Staging 19 Parquet files to Snowflake Stage: @ECOM_DB.PROD.ecommerce_stage/</p>
            <p class="text-slate-500">  ✓ Staged customers.parquet (2.1 MB) | clickstream.parquet (148.2 MB)</p>
            <p class="text-cyan-300">❄️  Compiling DDL & executing bulk load:</p>
            <p class="text-emerald-400">  ✓ Loaded table ECOM_DB.PROD.customers (50,000 rows)</p>
            <p class="text-emerald-400">  ✓ Loaded table ECOM_DB.PROD.orders_online (100,000 rows)</p>
            <p class="text-emerald-400">  ✓ Loaded table ECOM_DB.PROD.orders_instore (40,000 rows)</p>
            <p class="text-emerald-400">  ✓ Loaded table ECOM_DB.PROD.clickstream (5,000,000 rows)</p>
            <p class="text-slate-400">👁️  Deploying analytical views: <span class="text-white">v_omnichannel_sales</span>, <span class="text-white">v_customer_360</span></p>
            <p class="text-emerald-400 font-bold mt-2">✓ Snowflake export complete! 19 tables and 2 views created in 32.1s</p>
          </div>

          <!-- Tab 3: Validate -->
          <div id="term-content-validate" class="hidden">
            <div class="flex items-center justify-between text-slate-400 mb-2">
              <span class="text-brand-400">$ ecommerce-synth validate ./output/medium/</span>
              <button onclick="copyCommand('ecommerce-synth validate ./output/medium/')" class="hover:text-white text-xs px-2 py-0.5 rounded bg-surface-800 border border-slate-700">Copy</button>
            </div>
            <p class="text-slate-400">🔍 Auditing 29 referential integrity and foreign-key constraints...</p>
            <p class="text-emerald-400">  ✓ addresses.customer_id -> customers.customer_id (0 orphans)</p>
            <p class="text-emerald-400">  ✓ orders_online.customer_id -> customers.customer_id (0 orphans)</p>
            <p class="text-emerald-400">  ✓ order_items_online.order_id -> orders_online.order_id (0 orphans)</p>
            <p class="text-emerald-400">  ✓ order_items_online.product_id -> products.product_id (0 orphans)</p>
            <p class="text-emerald-400">  ✓ orders_instore.store_id -> stores.store_id (0 orphans)</p>
            <p class="text-emerald-400">  ✓ clickstream.session_id -> orders_online.session_id (0 orphans)</p>
            <p class="text-emerald-400">  ✓ loyalty_transactions.loyalty_id -> loyalty_members.loyalty_id (0 orphans)</p>
            <p class="text-emerald-400">  ✓ fraud_flags.customer_id -> customers.customer_id (0 orphans)</p>
            <p class="text-emerald-400 font-bold mt-2">✓ ALL 29 INTEGRITY CHECKS PASSED: Zero broken references across 5.8M rows.</p>
          </div>

          <!-- Tab 4: Stream -->
          <div id="term-content-stream" class="hidden">
            <div class="flex items-center justify-between text-slate-400 mb-2">
              <span class="text-brand-400">$ ecommerce-synth stream ./output/medium/ --speed 50 --json</span>
              <button onclick="copyCommand('ecommerce-synth stream ./output/medium/ --speed 50 --json')" class="hover:text-white text-xs px-2 py-0.5 rounded bg-surface-800 border border-slate-700">Copy</button>
            </div>
            <p class="text-slate-500">── Live Chronological Event Stream [speed=50x real-time] ──</p>
            <p class="text-yellow-400">{"timestamp": "2024-05-18T10:14:02Z", "channel": "web", "event_type": "page_view", "user_id": "c_92a1", "page": "/category/electronics"}</p>
            <p class="text-yellow-400">{"timestamp": "2024-05-18T10:14:15Z", "channel": "pos", "event_type": "store_checkout", "store": "STORE-012", "amount": 84.50}</p>
            <p class="text-yellow-400">{"timestamp": "2024-05-18T10:14:28Z", "channel": "web", "event_type": "add_to_cart", "user_id": "c_92a1", "sku": "SKU-0042"}</p>
            <p class="text-red-400">{"timestamp": "2024-05-18T10:14:31Z", "channel": "security", "event_type": "fraud_flag", "type": "velocity_spike", "severity": "high"}</p>
            <p class="text-yellow-400">{"timestamp": "2024-05-18T10:14:49Z", "channel": "web", "event_type": "purchase_complete", "order_id": "ord_8812f", "total": 129.99}</p>
            <p class="text-slate-500 mt-2">Streaming 142.5 events/sec... (Press Ctrl+C to stop)</p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Interactive Volume Tiers Section -->
  <section id="tiers" class="py-24 border-t border-surface-700/60 bg-surface-850/50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="text-center max-w-3xl mx-auto mb-14">
        <h2 class="text-xs font-bold uppercase tracking-wider text-brand-400 mb-2">Scalable Architecture</h2>
        <p class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-4">Volume Tiers & Live Calculator</p>
        <p class="text-slate-400 text-base">Select a tier below to preview exact synthetic entity volumes and generate targeted CLI commands.</p>
      </div>

      <!-- Tier Selector Buttons -->
      <div class="flex justify-center mb-12">
        <div class="inline-flex p-1.5 rounded-2xl bg-surface-800 border border-surface-700">
          <button onclick="selectTier('small')" id="tier-btn-small" class="px-6 py-2.5 rounded-xl text-sm font-semibold transition text-slate-300 hover:text-white">Small</button>
          <button onclick="selectTier('medium')" id="tier-btn-medium" class="px-6 py-2.5 rounded-xl text-sm font-semibold transition bg-brand-600 text-white shadow-lg shadow-brand-500/20">Medium</button>
          <button onclick="selectTier('large')" id="tier-btn-large" class="px-6 py-2.5 rounded-xl text-sm font-semibold transition text-slate-300 hover:text-white">Large</button>
          <button onclick="selectTier('xl')" id="tier-btn-xl" class="px-6 py-2.5 rounded-xl text-sm font-semibold transition text-slate-300 hover:text-white">XL (Enterprise)</button>
        </div>
      </div>

      <!-- Live Reactive Metrics Cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-5 max-w-5xl mx-auto mb-12">
        <div class="glass-card p-6 rounded-2xl border-l-4 border-l-brand-500">
          <div class="text-xs text-slate-400 font-medium mb-1">Customers</div>
          <div id="stat-customers" class="text-3xl font-extrabold text-white font-mono">50,000</div>
          <div class="text-[11px] text-slate-500 mt-2">7 Behavioral Personas</div>
        </div>
        <div class="glass-card p-6 rounded-2xl border-l-4 border-l-indigo-500">
          <div class="text-xs text-slate-400 font-medium mb-1">Online Orders</div>
          <div id="stat-online-orders" class="text-3xl font-extrabold text-white font-mono">100,000</div>
          <div class="text-[11px] text-slate-500 mt-2">~240,000 Line Items</div>
        </div>
        <div class="glass-card p-6 rounded-2xl border-l-4 border-l-emerald-500">
          <div class="text-xs text-slate-400 font-medium mb-1">In-Store POS Txns</div>
          <div id="stat-store-txns" class="text-3xl font-extrabold text-white font-mono">40,000</div>
          <div class="text-[11px] text-slate-500 mt-2">Across 50 Retail Stores</div>
        </div>
        <div class="glass-card p-6 rounded-2xl border-l-4 border-l-cyan-500">
          <div class="text-xs text-slate-400 font-medium mb-1">Clickstream Events</div>
          <div id="stat-clickstream" class="text-3xl font-extrabold text-white font-mono">5,000,000</div>
          <div class="text-[11px] text-slate-500 mt-2">Full Conversion Funnels</div>
        </div>
        <div class="glass-card p-6 rounded-2xl border-l-4 border-l-amber-500">
          <div class="text-xs text-slate-400 font-medium mb-1">Emails Delivered</div>
          <div id="stat-emails" class="text-3xl font-extrabold text-white font-mono">500,000</div>
          <div class="text-[11px] text-slate-500 mt-2">Open & Click Tracking</div>
        </div>
        <div class="glass-card p-6 rounded-2xl border-l-4 border-l-purple-500">
          <div class="text-xs text-slate-400 font-medium mb-1">Loyalty Members</div>
          <div id="stat-loyalty" class="text-3xl font-extrabold text-white font-mono">30,000</div>
          <div class="text-[11px] text-slate-500 mt-2">Bronze, Silver, Gold, Platinum</div>
        </div>
        <div class="glass-card p-6 rounded-2xl border-l-4 border-l-rose-500">
          <div class="text-xs text-slate-400 font-medium mb-1">Support Tickets</div>
          <div id="stat-support" class="text-3xl font-extrabold text-white font-mono">12,000</div>
          <div class="text-[11px] text-slate-500 mt-2">CSAT Scores & Resolution Times</div>
        </div>
        <div class="glass-card p-6 rounded-2xl border-l-4 border-l-teal-500">
          <div class="text-xs text-slate-400 font-medium mb-1">Est. Parquet Size</div>
          <div id="stat-size" class="text-3xl font-extrabold text-white font-mono">~350 MB</div>
          <div class="text-[11px] text-slate-500 mt-2">Snappy-compressed</div>
        </div>
      </div>

      <!-- Dynamic Command Generator Box -->
      <div class="max-w-4xl mx-auto glass-card rounded-2xl p-6 border border-surface-700/80">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div>
            <h3 class="text-sm font-semibold text-white">Generated Command for Selected Tier</h3>
            <p class="text-xs text-slate-400">Copy-paste ready for your terminal or CI/CD test runner.</p>
          </div>
          <div class="flex items-center gap-2">
            <label class="text-xs text-slate-400">Target Warehouse:</label>
            <select id="cmd-warehouse-select" onchange="updateGeneratedCommand()" class="text-xs bg-surface-900 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-200 focus:outline-none focus:border-brand-500">
              <option value="none">Parquet Only (No Export)</option>
              <option value="duckdb">DuckDB (.duckdb file)</option>
              <option value="databricks">Databricks Unity Catalog</option>
              <option value="snowflake">Snowflake</option>
              <option value="bigquery">Google BigQuery</option>
            </select>
          </div>
        </div>

        <div class="flex items-center justify-between bg-surface-900 px-4 py-3 rounded-xl border border-surface-700/80 font-mono text-xs sm:text-sm text-brand-300 overflow-x-auto">
          <span id="generated-command-display" class="whitespace-nowrap">ecommerce-synth generate --tier medium</span>
          <button onclick="copyGeneratedCommand()" id="btn-copy-gen-cmd" class="ml-4 px-3 py-1 rounded bg-brand-600 hover:bg-brand-500 text-white text-xs font-sans font-semibold transition shrink-0">
            Copy Command
          </button>
        </div>
      </div>
    </div>
  </section>

  <!-- Interactive 19-Table Schema & ERD Explorer Section -->
  <section id="schema" class="py-24 border-t border-surface-700/60">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
        <div>
          <h2 class="text-xs font-bold uppercase tracking-wider text-brand-400 mb-2">Machine-Readable Catalog</h2>
          <p class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-2">19-Table Schema & Data Dictionary</p>
          <p class="text-slate-400 text-sm max-w-2xl">
            Explore table architectures, primary keys, foreign-key relationships, and column data types defined in <code class="text-brand-300 font-mono">config/schema.json</code>.
          </p>
        </div>

        <!-- Search Bar -->
        <div class="w-full md:w-80">
          <div class="relative">
            <input type="text" id="schema-search" oninput="filterSchema()" placeholder="Search tables or columns..." 
                   class="w-full bg-surface-800 border border-slate-700 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500">
            <svg class="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
          </div>
        </div>
      </div>

      <!-- Domain Category Filters -->
      <div class="flex flex-wrap gap-2 mb-8">
        <button onclick="filterDomain('all')" id="domain-pill-all" class="px-4 py-1.5 rounded-full text-xs font-medium bg-brand-600 text-white transition">All Tables (19)</button>
        <button onclick="filterDomain('Omnichannel Sales & POS')" id="domain-pill-sales" class="px-4 py-1.5 rounded-full text-xs font-medium bg-surface-800 text-slate-300 hover:text-white border border-slate-700 transition">Omnichannel Sales & POS (6)</button>
        <button onclick="filterDomain('Customer 360 & Demographics')" id="domain-pill-cust" class="px-4 py-1.5 rounded-full text-xs font-medium bg-surface-800 text-slate-300 hover:text-white border border-slate-700 transition">Customer 360 & Demographics (4)</button>
        <button onclick="filterDomain('Engagement & Retention')" id="domain-pill-eng" class="px-4 py-1.5 rounded-full text-xs font-medium bg-surface-800 text-slate-300 hover:text-white border border-slate-700 transition">Engagement & Retention (6)</button>
        <button onclick="filterDomain('Experimentation & Fraud')" id="domain-pill-fraud" class="px-4 py-1.5 rounded-full text-xs font-medium bg-surface-800 text-slate-300 hover:text-white border border-slate-700 transition">Experimentation & Fraud (3)</button>
      </div>

      <!-- Tables Grid Container -->
      <div id="schema-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <!-- Rendered via JavaScript -->
      </div>
    </div>
  </section>

  <!-- Multi-Warehouse Exporters & Views Section -->
  <section id="warehouses" class="py-24 border-t border-surface-700/60 bg-surface-850/50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="text-center max-w-3xl mx-auto mb-14">
        <h2 class="text-xs font-bold uppercase tracking-wider text-brand-400 mb-2">Automated Lakehouse Ingestion</h2>
        <p class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-4">Multi-Warehouse Exporter Framework</p>
        <p class="text-slate-400 text-base">Two-stage staging + native bulk loading with automated catalog initialization, primary/foreign key constraints, and business KPI views.</p>
      </div>

      <!-- Warehouse Tabs -->
      <div class="max-w-5xl mx-auto glass-card rounded-2xl overflow-hidden border border-surface-700">
        <div class="grid grid-cols-2 sm:grid-cols-4 border-b border-surface-700 bg-surface-850">
          <button onclick="switchWhTab('databricks')" id="wh-tab-databricks" class="py-4 px-4 text-center text-sm font-semibold border-b-2 border-brand-500 text-white bg-surface-800/60 transition flex items-center justify-center gap-2">
            <span>🧱 Databricks UC</span>
          </button>
          <button onclick="switchWhTab('snowflake')" id="wh-tab-snowflake" class="py-4 px-4 text-center text-sm font-semibold border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition flex items-center justify-center gap-2">
            <span>❄️ Snowflake</span>
          </button>
          <button onclick="switchWhTab('bigquery')" id="wh-tab-bigquery" class="py-4 px-4 text-center text-sm font-semibold border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition flex items-center justify-center gap-2">
            <span>⚡ BigQuery</span>
          </button>
          <button onclick="switchWhTab('duckdb')" id="wh-tab-duckdb" class="py-4 px-4 text-center text-sm font-semibold border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition flex items-center justify-center gap-2">
            <span>🦆 DuckDB</span>
          </button>
        </div>

        <div class="p-8">
          <!-- Databricks Content -->
          <div id="wh-content-databricks">
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div class="lg:col-span-1 space-y-4">
                <h3 class="text-lg font-bold text-white">Unity Catalog Automation</h3>
                <p class="text-xs text-slate-400 leading-relaxed">
                  Stages Parquet files to Unity Catalog Volumes via multipart S3 uploads, then executes Serverless Delta Lake CTAS statements, attaches PK/FK constraints, and applies column comments.
                </p>
                <div class="space-y-2 text-xs">
                  <div class="flex items-center gap-2 text-slate-300"><span class="text-emerald-400">✓</span> Auto-creates Catalog & Schema</div>
                  <div class="flex items-center gap-2 text-slate-300"><span class="text-emerald-400">✓</span> UC Volume Multipart Staging</div>
                  <div class="flex items-center gap-2 text-slate-300"><span class="text-emerald-400">✓</span> Delta Lake Format with Constraints</div>
                  <div class="flex items-center gap-2 text-slate-300"><span class="text-emerald-400">✓</span> Creates v_omnichannel_sales</div>
                </div>
              </div>
              <div class="lg:col-span-2">
                <div class="bg-surface-900 rounded-xl p-4 font-mono text-xs text-slate-300 border border-slate-700/80 overflow-x-auto">
                  <div class="text-slate-500 mb-2"># CLI Execution:</div>
                  <div class="text-brand-300 mb-4">$ ecommerce-synth export ./output/medium/ --target databricks --catalog analytics --schema ecommerce_raw</div>
                  <div class="text-slate-500 mb-2">-- Delta Lake DDL Compiled:</div>
                  <div class="text-cyan-300">CREATE OR REPLACE TABLE analytics.ecommerce_raw.orders_online</div>
                  <div class="text-slate-400">AS SELECT * FROM read_files('/Volumes/analytics/ecommerce_raw/ecommerce_raw/orders_online.parquet');</div>
                  <div class="text-cyan-300 mt-2">ALTER TABLE analytics.ecommerce_raw.orders_online ADD CONSTRAINT orders_pk PRIMARY KEY (order_id);</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Snowflake Content -->
          <div id="wh-content-snowflake" class="hidden">
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div class="lg:col-span-1 space-y-4">
                <h3 class="text-lg font-bold text-white">Snowflake Internal Stage Loading</h3>
                <p class="text-xs text-slate-400 leading-relaxed">
                  Uploads files to an internal schema stage (<code class="text-cyan-300 font-mono">@ecommerce_stage</code>), establishes typed table DDL with comments, and loads data using <code class="text-cyan-300 font-mono">COPY INTO ... MATCH_BY_COLUMN_NAME</code>.
                </p>
                <div class="space-y-2 text-xs">
                  <div class="flex items-center gap-2 text-slate-300"><span class="text-emerald-400">✓</span> Auto-discovers connections.toml</div>
                  <div class="flex items-center gap-2 text-slate-300"><span class="text-emerald-400">✓</span> 4-Hour MFA Token Caching</div>
                  <div class="flex items-center gap-2 text-slate-300"><span class="text-emerald-400">✓</span> CREATE OR REPLACE TABLE idempotency</div>
                  <div class="flex items-center gap-2 text-slate-300"><span class="text-emerald-400">✓</span> Verified Row Count Auditing</div>
                </div>
              </div>
              <div class="lg:col-span-2">
                <div class="bg-surface-900 rounded-xl p-4 font-mono text-xs text-slate-300 border border-slate-700/80 overflow-x-auto">
                  <div class="text-slate-500 mb-2"># CLI Execution:</div>
                  <div class="text-brand-300 mb-4">$ ecommerce-synth export ./output/medium/ --target snowflake --database ANALYTICS_DB --schema PROD</div>
                  <div class="text-slate-500 mb-2">-- Bulk Load Statement Executed:</div>
                  <div class="text-cyan-300">COPY INTO ANALYTICS_DB.PROD.orders_online</div>
                  <div class="text-slate-400">FROM @ANALYTICS_DB.PROD.ecommerce_stage/orders_online.parquet</div>
                  <div class="text-slate-400">FILE_FORMAT = (TYPE = PARQUET) MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;</div>
                </div>
              </div>
            </div>
          </div>

          <!-- BigQuery Content -->
          <div id="wh-content-bigquery" class="hidden">
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div class="lg:col-span-1 space-y-4">
                <h3 class="text-lg font-bold text-white">Google Cloud BigQuery</h3>
                <p class="text-xs text-slate-400 leading-relaxed">
                  Direct file streaming or GCS bucket staging with BigQuery <code class="text-cyan-300 font-mono">LoadJobs</code>. Applies BigQuery SQL DDL with column descriptions and un-enforced primary keys.
                </p>
                <div class="space-y-2 text-xs">
                  <div class="flex items-center gap-2 text-slate-300"><span class="text-emerald-400">✓</span> Zero-staging Direct Parquet Streaming</div>
                  <div class="flex items-center gap-2 text-slate-300"><span class="text-emerald-400">✓</span> Cloud Storage (GCS) Fast Staging Option</div>
                  <div class="flex items-center gap-2 text-slate-300"><span class="text-emerald-400">✓</span> Native BigQuery Schema Mapping</div>
                  <div class="flex items-center gap-2 text-slate-300"><span class="text-emerald-400">✓</span> Deploys Customer 360 Views</div>
                </div>
              </div>
              <div class="lg:col-span-2">
                <div class="bg-surface-900 rounded-xl p-4 font-mono text-xs text-slate-300 border border-slate-700/80 overflow-x-auto">
                  <div class="text-slate-500 mb-2"># CLI Execution:</div>
                  <div class="text-brand-300 mb-4">$ ecommerce-synth export ./output/medium/ --target bigquery --project my-gcp-project --dataset ecommerce_prod</div>
                  <div class="text-slate-500 mb-2">-- BigQuery View Definition:</div>
                  <div class="text-cyan-300">CREATE OR REPLACE VIEW `my-gcp-project.ecommerce_prod.v_customer_360` AS</div>
                  <div class="text-slate-400">SELECT c.customer_id, c.email, COUNT(DISTINCT o.order_id) AS online_orders, ...</div>
                </div>
              </div>
            </div>
          </div>

          <!-- DuckDB Content -->
          <div id="wh-content-duckdb" class="hidden">
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div class="lg:col-span-1 space-y-4">
                <h3 class="text-lg font-bold text-white">Standalone DuckDB Bundle</h3>
                <p class="text-xs text-slate-400 leading-relaxed">
                  Creates a high-performance, single-file <code class="text-cyan-300 font-mono">.duckdb</code> database with zero external dependencies. Ideal for local analytics, CI/CD regression tests, and MotherDuck deployments.
                </p>
                <div class="space-y-2 text-xs">
                  <div class="flex items-center gap-2 text-slate-300"><span class="text-emerald-400">✓</span> Zero Cloud Configuration Needed</div>
                  <div class="flex items-center gap-2 text-slate-300"><span class="text-emerald-400">✓</span> Instant Table Creation with read_parquet()</div>
                  <div class="flex items-center gap-2 text-slate-300"><span class="text-emerald-400">✓</span> Supports Direct Physical Copy or Zero-Copy Views</div>
                  <div class="flex items-center gap-2 text-slate-300"><span class="text-emerald-400">✓</span> Compatible with dbt-duckdb</div>
                </div>
              </div>
              <div class="lg:col-span-2">
                <div class="bg-surface-900 rounded-xl p-4 font-mono text-xs text-slate-300 border border-slate-700/80 overflow-x-auto">
                  <div class="text-slate-500 mb-2"># CLI Execution:</div>
                  <div class="text-brand-300 mb-4">$ ecommerce-synth export ./output/medium/ --target duckdb --database ./ecommerce_bundle.duckdb</div>
                  <div class="text-slate-500 mb-2">-- Instant DuckDB Query:</div>
                  <div class="text-cyan-300">SELECT channel, count(*) as txns, sum(total_amount) as revenue</div>
                  <div class="text-slate-400">FROM v_omnichannel_sales GROUP BY channel;</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Behavioral Customer Personas & Fraud Section -->
  <section id="personas" class="py-24 border-t border-surface-700/60">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="text-center max-w-3xl mx-auto mb-14">
        <h2 class="text-xs font-bold uppercase tracking-wider text-brand-400 mb-2">Behavioral Realism</h2>
        <p class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-4">7 Behavioral Personas & Fraud Engine</p>
        <p class="text-slate-400 text-base">Customers do not behave uniformly. Synthetic activity is driven by empirical distributions across spending, channels, loyalty, and anomalous fraud vectors.</p>
      </div>

      <!-- Personas Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-16">
        <div class="glass-card p-6 rounded-2xl border-t-4 border-t-amber-400">
          <div class="flex items-center gap-3 mb-3">
            <span class="text-2xl">👑</span>
            <div>
              <h3 class="text-base font-bold text-white">Power Shopper</h3>
              <span class="text-xs text-amber-400 font-medium">5% of customer base</span>
            </div>
          </div>
          <p class="text-xs text-slate-400 leading-relaxed mb-4">High Average Order Value ($1,200+), omni-channel purchaser, frequent reviews, and top Platinum loyalty tier enrollment.</p>
          <div class="text-[11px] font-mono text-slate-500">AOV: $120–$450 | Frequency: Weekly</div>
        </div>

        <div class="glass-card p-6 rounded-2xl border-t-4 border-t-brand-400">
          <div class="flex items-center gap-3 mb-3">
            <span class="text-2xl">🛒</span>
            <div>
              <h3 class="text-base font-bold text-white">Regular Shopper</h3>
              <span class="text-xs text-brand-400 font-medium">30% of customer base</span>
            </div>
          </div>
          <p class="text-xs text-slate-400 leading-relaxed mb-4">Predictable bi-weekly re-orders, balanced across Apparel, Electronics, and Home goods. Strong responsive open rates to email campaigns.</p>
          <div class="text-[11px] font-mono text-slate-500">AOV: $60–$140 | Frequency: Bi-weekly</div>
        </div>

        <div class="glass-card p-6 rounded-2xl border-t-4 border-t-cyan-400">
          <div class="flex items-center gap-3 mb-3">
            <span class="text-2xl">🏷️</span>
            <div>
              <h3 class="text-base font-bold text-white">Bargain Hunter</h3>
              <span class="text-xs text-cyan-400 font-medium">20% of customer base</span>
            </div>
          </div>
          <p class="text-xs text-slate-400 leading-relaxed mb-4">Disproportionate sensitivity to promo codes, flash sales, and clearance items. Rarely completes checkout at standard MSRP.</p>
          <div class="text-[11px] font-mono text-slate-500">AOV: $30–$80 | Frequency: Monthly</div>
        </div>

        <div class="glass-card p-6 rounded-2xl border-t-4 border-t-slate-400">
          <div class="flex items-center gap-3 mb-3">
            <span class="text-2xl">🏃</span>
            <div>
              <h3 class="text-base font-bold text-white">One-and-Done</h3>
              <span class="text-xs text-slate-400 font-medium">20% of customer base</span>
            </div>
          </div>
          <p class="text-xs text-slate-400 leading-relaxed mb-4">High impulse single order via search ad or social link. Minimal session browsing, never registers a loyalty account.</p>
          <div class="text-[11px] font-mono text-slate-500">AOV: $40–$110 | Frequency: 1 Order Ever</div>
        </div>

        <div class="glass-card p-6 rounded-2xl border-t-4 border-t-emerald-400">
          <div class="flex items-center gap-3 mb-3">
            <span class="text-2xl">☕</span>
            <div>
              <h3 class="text-base font-bold text-white">Occasional Shopper</h3>
              <span class="text-xs text-emerald-400 font-medium">15% of customer base</span>
            </div>
          </div>
          <p class="text-xs text-slate-400 leading-relaxed mb-4">Seasonal surge shopper (Black Friday, Cyber Week, Prime Days, Valentine's). Dormant across rest-of-year periods.</p>
          <div class="text-[11px] font-mono text-slate-500">AOV: $90–$250 | Frequency: Quarterly/Holidays</div>
        </div>

        <div class="glass-card p-6 rounded-2xl border-t-4 border-t-rose-500">
          <div class="flex items-center gap-3 mb-3">
            <span class="text-2xl">🚨</span>
            <div>
              <h3 class="text-base font-bold text-rose-400">Fraudster</h3>
              <span class="text-xs text-rose-400 font-medium">2% of customer base</span>
            </div>
          </div>
          <p class="text-xs text-slate-400 leading-relaxed mb-4">Synthetic identity, rapid card-testing bursts, promo stacking abuse, and chargeback anomalies labeled in <code class="text-rose-300 font-mono">fraud_flags</code>.</p>
          <div class="text-[11px] font-mono text-rose-400/80">Ground Truth ML Labels for Risk Models</div>
        </div>
      </div>
    </div>
  </section>

  <!-- Quickstart & CLI Reference Section -->
  <section id="quickstart" class="py-24 border-t border-surface-700/60 bg-surface-850/50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="text-center max-w-3xl mx-auto mb-14">
        <h2 class="text-xs font-bold uppercase tracking-wider text-brand-400 mb-2">Developer Experience</h2>
        <p class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-4">Quickstart & CLI Reference</p>
        <p class="text-slate-400 text-base">Install the package and start producing production-quality ecommerce datasets in seconds.</p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-5xl mx-auto">
        <!-- Installation Box -->
        <div class="glass-card p-6 rounded-2xl">
          <h3 class="text-base font-bold text-white mb-3 flex items-center gap-2">
            <span>📦</span> <span>Installation Options</span>
          </h3>
          <div class="space-y-4 font-mono text-xs text-slate-300">
            <div>
              <span class="text-slate-500 block mb-1"># Core Package (DuckDB + Parquet)</span>
              <div class="bg-surface-900 p-3 rounded-lg border border-slate-700/80 flex items-center justify-between">
                <span>pip install -e ".[dev]"</span>
                <button onclick="copyCommand('pip install -e \".[dev]\"')" class="text-slate-400 hover:text-white">Copy</button>
              </div>
            </div>
            <div>
              <span class="text-slate-500 block mb-1"># With Databricks Unity Catalog Connector</span>
              <div class="bg-surface-900 p-3 rounded-lg border border-slate-700/80 flex items-center justify-between">
                <span>pip install -e ".[databricks]"</span>
                <button onclick="copyCommand('pip install -e \".[databricks]\"')" class="text-slate-400 hover:text-white">Copy</button>
              </div>
            </div>
            <div>
              <span class="text-slate-500 block mb-1"># With Snowflake Connector</span>
              <div class="bg-surface-900 p-3 rounded-lg border border-slate-700/80 flex items-center justify-between">
                <span>pip install -e ".[snowflake]"</span>
                <button onclick="copyCommand('pip install -e \".[snowflake]\"')" class="text-slate-400 hover:text-white">Copy</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Command Cheat Sheet -->
        <div class="glass-card p-6 rounded-2xl">
          <h3 class="text-base font-bold text-white mb-3 flex items-center gap-2">
            <span>⚡</span> <span>Essential CLI Commands</span>
          </h3>
          <div class="space-y-3 font-mono text-xs text-slate-300">
            <div class="bg-surface-900 p-3 rounded-lg border border-slate-700/80">
              <span class="text-slate-500 block mb-1"># Generate Full Dataset:</span>
              <span class="text-brand-300">ecommerce-synth generate --tier small</span>
            </div>
            <div class="bg-surface-900 p-3 rounded-lg border border-slate-700/80">
              <span class="text-slate-500 block mb-1"># Validate Referential FK Integrity:</span>
              <span class="text-emerald-400">ecommerce-synth validate ./output/small_run/</span>
            </div>
            <div class="bg-surface-900 p-3 rounded-lg border border-slate-700/80">
              <span class="text-slate-500 block mb-1"># Preview Sample Table Data:</span>
              <span class="text-cyan-300">ecommerce-synth preview ./output/small_run/ orders_online -n 5</span>
            </div>
            <div class="bg-surface-900 p-3 rounded-lg border border-slate-700/80">
              <span class="text-slate-500 block mb-1"># Stream Real-Time Events:</span>
              <span class="text-amber-400">ecommerce-synth stream ./output/small_run/ --speed 100</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Footer -->
  <footer class="py-12 border-t border-surface-700/60 bg-surface-900 text-slate-400 text-xs text-center">
    <div class="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
      <div class="flex items-center gap-2">
        <span class="text-base">🛒</span>
        <span class="font-bold text-slate-200">ecommerce-synth</span>
        <span>— Released under Apache-2.0 / MIT.</span>
      </div>
      <div>
        <a href="https://github.com/anilkulkarni87/ecommerce_synthetic" target="_blank" rel="noopener noreferrer" class="hover:text-white transition">
          GitHub Repository
        </a>
      </div>
    </div>
  </footer>

  <!-- Modal / Floating Notification for Copied Feedback -->
  <div id="copy-toast" class="fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-xl bg-brand-600 text-white text-xs font-semibold shadow-2xl flex items-center gap-2 transform translate-y-20 opacity-0 transition-all duration-300 pointer-events-none">
    <svg class="w-4 h-4 text-emerald-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
    <span id="toast-message">Command copied to clipboard!</span>
  </div>

  <!-- Embedded Schema Data & Interactive Logic -->
  <script>
    const SCHEMA = __SCHEMA_JSON__;

    const TIERS = {
      small: {{
        customers: "500",
        onlineOrders: "1,000",
        storeTxns: "500",
        clickstream: "50,000",
        emails: "5,000",
        loyalty: "300",
        support: "150",
        size: "< 5 MB",
        cmd: "ecommerce-synth generate --tier small"
      }},
      medium: {{
        customers: "50,000",
        onlineOrders: "100,000",
        storeTxns: "40,000",
        clickstream: "5,000,000",
        emails: "500,000",
        loyalty: "30,000",
        support: "12,000",
        size: "~350 MB",
        cmd: "ecommerce-synth generate --tier medium"
      }},
      large: {{
        customers: "500,000",
        onlineOrders: "1,000,000",
        storeTxns: "400,000",
        clickstream: "50,000,000",
        emails: "5,000,000",
        loyalty: "300,000",
        support: "120,000",
        size: "~3.5 GB",
        cmd: "ecommerce-synth generate --tier large"
      }},
      xl: {{
        customers: "5,000,000",
        onlineOrders: "10,000,000",
        storeTxns: "4,000,000",
        clickstream: "500,000,000",
        emails: "50,000,000",
        loyalty: "3,000,000",
        support: "1,200,000",
        size: "~35 GB",
        cmd: "ecommerce-synth generate --tier xl"
      }}
    }};

    let currentTier = "medium";
    let currentDomain = "all";

    function selectTier(tierKey) {{
      currentTier = tierKey;
      ['small', 'medium', 'large', 'xl'].forEach(k => {{
        const btn = document.getElementById('tier-btn-' + k);
        if (k === tierKey) {{
          btn.className = "px-6 py-2.5 rounded-xl text-sm font-semibold transition bg-brand-600 text-white shadow-lg shadow-brand-500/20";
        }} else {{
          btn.className = "px-6 py-2.5 rounded-xl text-sm font-semibold transition text-slate-300 hover:text-white";
        }}
      }});

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
    }}

    function updateGeneratedCommand() {{
      const wh = document.getElementById('cmd-warehouse-select').value;
      let cmd = `ecommerce-synth generate --tier ${{currentTier}}`;
      if (wh === 'duckdb') {{
        cmd += ` --export duckdb`;
      }} else if (wh === 'databricks') {{
        cmd += ` --export databricks --catalog dev_catalog --schema ecommerce`;
      }} else if (wh === 'snowflake') {{
        cmd += ` --export snowflake --database ECOM_DB --schema PROD`;
      }} else if (wh === 'bigquery') {{
        cmd += ` --export bigquery --project my-gcp-project --dataset ecommerce`;
      }}
      document.getElementById('generated-command-display').textContent = cmd;
    }}

    function copyGeneratedCommand() {{
      const cmd = document.getElementById('generated-command-display').textContent;
      copyCommand(cmd);
    }}

    function copyCommand(text) {{
      navigator.clipboard.writeText(text);
      const toast = document.getElementById('copy-toast');
      const msg = document.getElementById('toast-message');
      msg.textContent = `Copied: ${{text.length > 35 ? text.substring(0, 35) + '...' : text}}`;
      toast.classList.remove('translate-y-20', 'opacity-0');
      toast.classList.add('translate-y-0', 'opacity-100');
      setTimeout(() => {{
        toast.classList.add('translate-y-20', 'opacity-0');
        toast.classList.remove('translate-y-0', 'opacity-100');
      }}, 2500);
    }}

    function switchTerminalTab(tabId) {{
      ['generate', 'export', 'validate', 'stream'].forEach(t => {{
        const btn = document.getElementById('term-tab-' + t);
        const content = document.getElementById('term-content-' + t);
        if (t === tabId) {{
          btn.className = "px-2.5 py-1 rounded bg-brand-600 text-white font-medium transition";
          content.classList.remove('hidden');
        }} else {{
          btn.className = "px-2.5 py-1 rounded text-slate-400 hover:text-white transition";
          content.classList.add('hidden');
        }}
      }});
    }}

    function switchWhTab(targetId) {{
      ['databricks', 'snowflake', 'bigquery', 'duckdb'].forEach(t => {{
        const btn = document.getElementById('wh-tab-' + t);
        const content = document.getElementById('wh-content-' + t);
        if (t === targetId) {{
          btn.className = "py-4 px-4 text-center text-sm font-semibold border-b-2 border-brand-500 text-white bg-surface-800/60 transition flex items-center justify-center gap-2";
          content.classList.remove('hidden');
        }} else {{
          btn.className = "py-4 px-4 text-center text-sm font-semibold border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition flex items-center justify-center gap-2";
          content.classList.add('hidden');
        }}
      }});
    }}

    function getTypeColorClass(typeStr) {{
      const t = typeStr.toLowerCase();
      if (t.includes('uuid')) return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      if (t.includes('timestamp')) return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20';
      if (t.includes('date')) return 'bg-teal-500/10 text-teal-400 border-teal-500/20';
      if (t.includes('int')) return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      if (t.includes('float')) return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      if (t.includes('bool')) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      return 'bg-slate-700/50 text-slate-300 border-slate-600/40';
    }}

    function renderSchemaCards() {{
      const container = document.getElementById('schema-grid');
      container.innerHTML = '';

      const query = document.getElementById('schema-search').value.toLowerCase().trim();

      for (const [tname, tinfo] of Object.entries(SCHEMA.tables)) {{
        // Filter domain
        if (currentDomain !== 'all' && tinfo.domain !== currentDomain) {{
          continue;
        }}

        // Filter search
        const colNames = Object.keys(tinfo.columns).join(' ').toLowerCase();
        const matchesQuery = !query || tname.toLowerCase().includes(query) || tinfo.description.toLowerCase().includes(query) || colNames.includes(query);
        if (!matchesQuery) {{
          continue;
        }}

        const colCount = Object.keys(tinfo.columns).length;
        const pk = tinfo.primary_key || 'None';
        const fkCount = tinfo.foreign_keys ? Object.keys(tinfo.foreign_keys).length : 0;

        const card = document.createElement('div');
        card.className = "glass-card rounded-2xl p-5 transition flex flex-col justify-between";

        let columnsHtml = '';
        for (const [cname, cinfo] of Object.entries(tinfo.columns)) {{
          const isPK = cname === pk;
          const isFK = tinfo.foreign_keys && tinfo.foreign_keys[cname];
          const badgeClass = getTypeColorClass(cinfo.type);

          columnsHtml += `
            <tr class="border-b border-surface-700/40 last:border-0 hover:bg-surface-800/40 text-[11px]">
              <td class="py-2 pr-2 font-mono text-slate-200">
                ${{cname}}
                ${{isPK ? '<span class="ml-1 text-[9px] px-1 py-0.2 bg-amber-500/20 text-amber-300 rounded font-bold">PK</span>' : ''}}
                ${{isFK ? '<span class="ml-1 text-[9px] px-1 py-0.2 bg-cyan-500/20 text-cyan-300 rounded font-bold">FK</span>' : ''}}
              </td>
              <td class="py-2 px-2">
                <span class="px-1.5 py-0.5 rounded border ${{badgeClass}} font-mono">${{cinfo.type}}</span>
              </td>
              <td class="py-2 px-2 text-slate-400">
                ${{cinfo.nullable ? '<span class="text-slate-500">NULL</span>' : '<span class="text-emerald-400/80 font-semibold">NOT NULL</span>'}}
              </td>
              <td class="py-2 pl-2 text-slate-400 max-w-[140px] truncate" title="${{cinfo.description}}">
                ${{cinfo.description}}
              </td>
            </tr>
          `;
        }}

        card.innerHTML = `
          <div>
            <div class="flex items-start justify-between gap-2 mb-2">
              <div>
                <h3 class="text-base font-bold text-white font-mono flex items-center gap-2">
                  <span>${{tname}}</span>
                </h3>
                <span class="text-[11px] text-brand-400 font-medium">${{tinfo.domain}}</span>
              </div>
              <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-800 border border-slate-700 text-slate-400">
                ${{tinfo.file}}
              </span>
            </div>

            <p class="text-xs text-slate-400 mb-4 line-clamp-2 leading-relaxed">
              ${{tinfo.description}}
            </p>

            <div class="flex flex-wrap gap-2 text-[11px] mb-4">
              <span class="px-2 py-0.5 rounded bg-surface-800 text-slate-300 font-mono">Cols: ${{colCount}}</span>
              <span class="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 font-mono">PK: ${{pk}}</span>
              ${{fkCount > 0 ? `<span class="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-mono">FKs: ${{fkCount}}</span>` : ''}}
            </div>
          </div>

          <div>
            <div id="cols-container-${{tname}}" class="hidden mt-3 pt-3 border-t border-surface-700/80 overflow-x-auto max-h-64">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="text-[10px] uppercase font-bold text-slate-500 border-b border-surface-700/80">
                    <th class="pb-1 pr-2">Column</th>
                    <th class="pb-1 px-2">Type</th>
                    <th class="pb-1 px-2">Null</th>
                    <th class="pb-1 pl-2">Description</th>
                  </tr>
                </thead>
                <tbody>
                  ${{columnsHtml}}
                </tbody>
              </table>
            </div>

            <button onclick="toggleTableDetails('${{tname}}')" id="toggle-btn-${{tname}}" 
                    class="w-full mt-3 py-1.5 rounded-lg bg-surface-800 hover:bg-surface-700 text-slate-300 hover:text-white text-xs font-medium border border-slate-700/60 transition flex items-center justify-center gap-1.5">
              <span>View ${{colCount}} Columns</span>
              <svg class="w-3.5 h-3.5 transition-transform" id="arrow-${{tname}}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
            </button>
          </div>
        `;

        container.appendChild(card);
      }}

      if (container.children.length === 0) {{
        container.innerHTML = `
          <div class="col-span-full py-16 text-center text-slate-400">
            <p class="text-base font-semibold text-slate-300">No matching tables found.</p>
            <p class="text-xs mt-1">Try searching for another keyword or change domain filters.</p>
          </div>
        `;
      }}
    }}

    function toggleTableDetails(tableName) {{
      const container = document.getElementById('cols-container-' + tableName);
      const btn = document.getElementById('toggle-btn-' + tableName);
      const arrow = document.getElementById('arrow-' + tableName);

      if (container.classList.contains('hidden')) {{
        container.classList.remove('hidden');
        btn.querySelector('span').textContent = 'Hide Columns';
        arrow.classList.add('rotate-180');
      }} else {{
        container.classList.add('hidden');
        const count = Object.keys(SCHEMA.tables[tableName].columns).length;
        btn.querySelector('span').textContent = `View ${{count}} Columns`;
        arrow.classList.remove('rotate-180');
      }}
    }}

    function filterDomain(domainName) {{
      currentDomain = domainName;
      ['all', 'sales', 'cust', 'eng', 'fraud'].forEach(d => {{
        const btn = document.getElementById('domain-pill-' + d);
        btn.className = "px-4 py-1.5 rounded-full text-xs font-medium bg-surface-800 text-slate-300 hover:text-white border border-slate-700 transition";
      }});

      if (domainName === 'all') document.getElementById('domain-pill-all').className = "px-4 py-1.5 rounded-full text-xs font-medium bg-brand-600 text-white transition";
      else if (domainName.includes('Sales')) document.getElementById('domain-pill-sales').className = "px-4 py-1.5 rounded-full text-xs font-medium bg-brand-600 text-white transition";
      else if (domainName.includes('Customer')) document.getElementById('domain-pill-cust').className = "px-4 py-1.5 rounded-full text-xs font-medium bg-brand-600 text-white transition";
      else if (domainName.includes('Engagement')) document.getElementById('domain-pill-eng').className = "px-4 py-1.5 rounded-full text-xs font-medium bg-brand-600 text-white transition";
      else if (domainName.includes('Experiment')) document.getElementById('domain-pill-fraud').className = "px-4 py-1.5 rounded-full text-xs font-medium bg-brand-600 text-white transition";

      renderSchemaCards();
    }}

    function filterSchema() {{
      renderSchemaCards();
    }}

    // Initial render
    document.addEventListener('DOMContentLoaded', () => {{
      renderSchemaCards();
    }});
  </script>
</body>
</html>
'''

html_content = html_template.replace("__SCHEMA_JSON__", schema_json_str)

# Convert any double braces left in the template into single braces
html_content = html_content.replace("{{", "{").replace("}}", "}")

output_path = repo_root / "docs" / "index.html"
with open(output_path, "w") as f:
    f.write(html_content)

print(f"Generated {output_path} successfully ({len(html_content):,} bytes).")
