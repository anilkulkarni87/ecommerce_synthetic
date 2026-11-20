# Design System — ecommerce-synth Documentation Atlas

## Visual World: Swiss Cartographic Reference Atlas

- **Mode:** Read (technical schema, CLI, and SQL reference for data, analytics, and identity engineers)
- **Surface:** Light warm cartographic paper (`#FAF8F4`) with crisp white map plates (`#FFFFFF`), linen vellum tint (`#F3EFE6`), and 1px hairline rules (`#DFD9CE`).
- **Ink:** Deep slate-navy (`#0F172A`) primary text, muted slate (`#475569`) secondary text.
- **Route Accents:**
  - Cobalt (`#1D4ED8`): Digital e-commerce, primary navigation, and primary keys
  - Amber (`#B45309`): Decoupled retail POS and cross-channel identity stitching
  - Teal (`#0F766E`): Clickstream, fulfillment (BOPIS/BORIS), and verified foreign keys
  - Crimson (`#BE123C`): `DIRECT_PII` governance tags and fraud vectors

## Typography

- **UI & Body:** `Source Sans 3` (workhorse humanist sans, crisp tabular numerals)
- **Code, Identifiers & Coordinates:** `JetBrains Mono`
- **Scale:** `h1` `2.75rem`, `h2` `1.75rem`, `h3` `1.05rem`, body `0.9375rem`

## Structural Rules

- **Sticky Left Wayfinding Rail** (`lg:w-56`) paired with a wide main reading column (`max-w-[1380px]`).
- **Zero Nested Cards:** Panels use hairline borders (`1px solid #DFD9CE`), full-width horizontal/vertical dividers, and subtle surface shifts (`#F3EFE6`) instead of nested bordered boxes.
- **Interactive Layer Map:** SVG topology map supports route-layer filtering (`All Routes`, `Digital & Clickstream`, `Decoupled POS`, `BOPIS & Fulfillment`) and click-to-filter table selection.
