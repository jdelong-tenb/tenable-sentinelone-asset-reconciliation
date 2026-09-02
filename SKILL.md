---
name: tenable-sentinelone-asset-reconciliation
description: Cross-references Tenable's asset inventory against SentinelOne's agent inventory to find protection gaps (Tenable-visible hosts with no SentinelOne agent) and exposure blind spots (SentinelOne-protected hosts Tenable never scans). Invoke when someone says things like "what's on my network that SentinelOne isn't protecting," "find our EDR coverage gaps," "reconcile Tenable and SentinelOne inventory," or "which assets does SentinelOne see that Tenable doesn't."
---

# Tenable + SentinelOne Asset Reconciliation

## Why this exists

Tenable and SentinelOne each maintain an independent view of "everything on the network" — one built from vulnerability/exposure scanning, the other from EDR agent telemetry. Nothing automatically checks whether the two agree. That leaves two blind spots: assets SentinelOne protects that Tenable never scans (invisible to exposure management), and assets Tenable can see that have no SentinelOne agent at all (a protection gap). This skill pulls both inventories independently and reconciles them.

This is a community-built skill, not official guidance from either vendor. There is no vendor-to-vendor bridge — it reads each product's own API/MCP server and does the matching inside your orchestrating AI client.

## Phase 1 — Pull both inventories

**Tenable side:** call `workbenches_list_assets` for hostname, IP, and OS. Note it caps at 5,000 assets — larger environments need the Tenable assets export API, or `tenable_one_search_assets` (Tenable One customers) with pagination instead.

**SentinelOne side:** call `mcp__purple-mcp__list_inventory_items` (or `search_inventory_items` for filtered pulls) with `fetch_fields` including at least `["id","name","ipAddress","networkInterfaces","lastActiveDt"]`. Filter by `surface` — `ENDPOINT` for traditional agents, `CLOUD` for workloads, `IDENTITY`, `NETWORK_DISCOVERY` for Ranger-discovered devices — depending on what's in scope for this reconciliation.

**Important field caveat:** SentinelOne's inventory record has no single canonical "hostname" field and no top-level MAC address field. `name` is frequently just an IP or a generated label, and per-interface IP/MAC pairs live nested inside `networkInterfaces[]`. Build your match key from `name` + `ipAddress` + every `networkInterfaces[].ip`, not from one field.

**Example user prompts:**
- "Pull our SentinelOne and Tenable asset inventories"
- "Show me everything SentinelOne is watching in our cloud environment"

## Phase 2 — Match

For each Tenable asset, look for a SentinelOne record where the Tenable hostname or IP equals the S1 `name`, or appears in any `networkInterfaces[].ip`, or equals `ipAddress`. Do the same in reverse. Classify each host:

- **Matched** (protected + scanned) — no action needed
- **Tenable-only** (no S1 agent) — protection gap
- **S1-only** (no Tenable visibility) — exposure blind spot; note this may include cloud/ephemeral assets that are legitimately outside Tenable's configured scan scope, not necessarily a real gap

Flag anything that matched on IP alone but not hostname as **ambiguous**, and say so explicitly rather than promoting it to "matched." Dynamic IP assignment (DHCP, containers, cloud autoscaling) produces false IP-only matches — this is the single biggest source of wrong answers in this skill.

**Example user prompts:**
- "Which of these are real matches vs just an IP coincidence?"
- "Show me the ambiguous ones separately"

## Phase 3 — Report and act

Present counts (Tenable-only / S1-only / matched / ambiguous) and a table of specific hosts, not just totals. For Tenable-only assets, offer — but always ask first — to tag them in Tenable for follow-up (e.g. a tag category like "S1 Coverage: Missing"). For S1-only assets, confirm with the user whether these are genuinely out-of-scope-by-design before treating every one as an exposure gap; don't assume.

**Example user prompts:**
- "Tag the unprotected hosts so we can track remediation"
- "Which of the S1-only assets should actually be in Tenable's scan scope?"

## MCP tools used

- `mcp__purple-mcp__list_inventory_items` / `search_inventory_items` — SentinelOne asset inventory (read-only)
- `workbenches_list_assets` or `tenable_one_search_assets` — Tenable asset inventory
- `tenable_one_list_inventory_properties` — discover available Tenable One filter fields if using `tenable_one_search_assets`

## Known limitations

- **No shared schema between vendors.** Every cross-vendor match here is best-effort hostname/IP matching performed by the orchestrating AI client — not a vendor-native join, because neither product links its inventory to the other's identifiers. In dynamic environments, IP reuse will produce false matches; treat single-signal (IP-only) matches as tentative, not confirmed.
- **SentinelOne inventory has no single canonical hostname or MAC field** — matching relies on `name` + `ipAddress` + nested `networkInterfaces[].ip`, which is noisier than a clean hostname join.
- **`workbenches_list_assets` caps at 5,000 records.** Large fleets need the Tenable assets export API or paginated `tenable_one_search_assets` instead.
- **Read-only on both sides, by design.** This skill identifies gaps — it doesn't deploy a SentinelOne agent or launch a Tenable scan. Pair it with your own onboarding/remediation tooling for auto-fix.
