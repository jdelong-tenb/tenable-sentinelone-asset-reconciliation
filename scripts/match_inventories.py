#!/usr/bin/env python3
"""
Standalone preview of the Tenable <-> SentinelOne asset-matching logic used by
the tenable-sentinelone-asset-reconciliation skill. Takes two exported
inventory JSON files (not live API calls) and prints match classification
counts plus a host-level table.

Usage:
    python3 match_inventories.py tenable_assets.json s1_assets.json

Expected input shapes:
    tenable_assets.json: list of {"hostname": str, "ipv4": [str, ...]}
    s1_assets.json:      list of {"name": str, "ipAddress": str,
                                   "networkInterfaces": [{"ip": str, ...}, ...]}
    (i.e. roughly what workbenches_list_assets / list_inventory_items return —
    adapt the extraction helpers below if your export shape differs.)
"""
import ipaddress
import json
import sys


def tenable_keys(asset):
    keys = set()
    hostname = asset.get("hostname")
    if hostname:
        keys.add(hostname.lower())
    for ip in asset.get("ipv4", []):
        keys.add(ip.lower())
    return keys


def s1_keys(asset):
    keys = set()
    name = asset.get("name")
    if name:
        keys.add(name.lower())
    ip_address = asset.get("ipAddress")
    if ip_address:
        keys.add(ip_address.lower())
    for iface in asset.get("networkInterfaces", []):
        ip = iface.get("ip")
        if ip:
            keys.add(ip.lower())
    return keys


def is_ip(key):
    try:
        ipaddress.ip_address(key)
        return True
    except ValueError:
        return False


def classify(tenable_assets, s1_assets):
    s1_index = []
    for s1_asset in s1_assets:
        s1_index.append((s1_keys(s1_asset), s1_asset))

    matched, ambiguous, tenable_only = [], [], []
    matched_s1_object_ids = set()

    for t_asset in tenable_assets:
        t_keys = tenable_keys(t_asset)
        hostname_asset = None
        ip_asset = None
        for keys, s1_asset in s1_index:
            shared = t_keys & keys
            if not shared:
                continue
            matched_s1_object_ids.add(id(s1_asset))
            if any(not is_ip(k) for k in shared):
                if hostname_asset is None:
                    hostname_asset = s1_asset
            else:
                if ip_asset is None:
                    ip_asset = s1_asset

        if hostname_asset is not None:
            matched.append((t_asset, hostname_asset))
        elif ip_asset is not None:
            ambiguous.append((t_asset, ip_asset))
        else:
            tenable_only.append(t_asset)

    s1_only = [a for a in s1_assets if id(a) not in matched_s1_object_ids]

    return {
        "matched": matched,
        "ambiguous": ambiguous,
        "tenable_only": tenable_only,
        "s1_only": s1_only,
    }


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        tenable_assets = json.load(f)
    with open(sys.argv[2]) as f:
        s1_assets = json.load(f)

    result = classify(tenable_assets, s1_assets)

    print(f"Matched (hostname-confirmed):     {len(result['matched'])}")
    print(f"Ambiguous (IP-only match):         {len(result['ambiguous'])}")
    print(f"Tenable-only (no SentinelOne):     {len(result['tenable_only'])}")
    print(f"SentinelOne-only (no Tenable):     {len(result['s1_only'])}")
    print()

    if result["tenable_only"]:
        print("-- Tenable-only (protection gap) --")
        for asset in result["tenable_only"]:
            print(f"  {asset.get('hostname', '(no hostname)')}  {asset.get('ipv4', [])}")

    if result["s1_only"]:
        print("-- SentinelOne-only (exposure blind spot, verify scope before flagging) --")
        for asset in result["s1_only"]:
            print(f"  {asset.get('name', '(no name)')}  {asset.get('ipAddress', '')}")

    if result["ambiguous"]:
        print("-- Ambiguous: IP matched, hostname did not (verify before trusting) --")
        for t_asset, s1_asset in result["ambiguous"]:
            print(f"  {t_asset.get('hostname')} <-> {s1_asset.get('name')}")


if __name__ == "__main__":
    main()
