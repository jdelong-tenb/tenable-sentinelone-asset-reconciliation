# Tenable + SentinelOne Asset Reconciliation

A Claude Code skill that cross-references Tenable's asset inventory against SentinelOne's agent inventory to surface protection gaps and exposure blind spots.

## What it does

Tenable and SentinelOne each independently track "everything on the network" — one from scanning, one from EDR agent telemetry. Nothing checks whether the two agree. This skill:

1. **Pulls both inventories** — Tenable via Workbenches/Tenable One, SentinelOne via its public `purple-mcp` server
2. **Matches assets** across vendors on hostname/IP (there's no shared identifier, so this is best-effort — see limitations)
3. **Classifies gaps** — Tenable-only (no SentinelOne agent), SentinelOne-only (outside Tenable's scan scope), matched, or ambiguous
4. **Reports and optionally tags** unprotected hosts in Tenable for follow-up, with confirmation before any write

This is a community-built skill, not official guidance from Tenable or SentinelOne.

## Prerequisites

- Claude Code (or another skill-compatible client) with:
  - A Tenable MCP server connected (Workbenches / Tenable One access)
  - SentinelOne's [`purple-mcp`](https://github.com/Sentinel-One/purple-mcp) server connected, with your own SentinelOne API token
- No write access required for the reconciliation itself — only if you choose to have it tag gap assets in Tenable

## How to run

1. Copy or symlink this directory into your Claude Code skills path:
   ```bash
   cp -r tenable-sentinelone-asset-reconciliation ~/.claude/skills/
   ```
2. Ensure both MCP servers are configured and connected.
3. In a Claude Code session, say something like:
   - "Find gaps between our Tenable and SentinelOne coverage"
   - "What's on the network that SentinelOne isn't protecting?"
   - "Which SentinelOne-protected assets does Tenable never scan?"

The skill activates automatically from its description, or you can invoke it explicitly.

You can also run the matching logic directly against exported inventory JSON to preview results outside a live session:
```bash
python3 scripts/match_inventories.py tenable_assets.json s1_assets.json
```

## What it produces

- Counts: matched / Tenable-only / SentinelOne-only / ambiguous
- A host-level table, not just totals
- Optional Tenable tagging of unprotected hosts (asks first)

## Known limitations

See [SKILL.md Known Limitations](SKILL.md#known-limitations) — most importantly: there's no shared schema between the two vendors, so every match is best-effort hostname/IP correlation, not a vendor-native join. Dynamic IP reuse (DHCP, containers, cloud autoscaling) is the main source of false matches.

## License

MIT — see [LICENSE](LICENSE).
