#!/usr/bin/env python3
"""
Fixture tests for match_inventories.py, covering the 3 bugs a prior
adversarial review found and fixed (object-identity matching instead of the
S1 record's own `id` field, and full IPv4/IPv6 classification via
`ipaddress.ip_address`). Pure stdlib, no dependencies.

Usage:
    python3 tests/test_match_inventories.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from match_inventories import classify, is_ip  # noqa: E402


class TestIsIp(unittest.TestCase):
    def test_ipv4_recognized(self):
        self.assertTrue(is_ip("10.0.0.1"))

    def test_ipv6_recognized(self):
        self.assertTrue(is_ip("fe80::1"))

    def test_hostname_not_recognized_as_ip(self):
        self.assertFalse(is_ip("web-01"))


class TestClassify(unittest.TestCase):
    def test_hostname_match_wins_over_stale_duplicate_nic(self):
        # Regression: the matching loop used to overwrite the matched S1
        # asset with whichever record was examined last, not the one that
        # actually hostname-matched — a stale/duplicate NIC entry scanned
        # after the real hostname match would silently clobber it.
        tenable = [{"hostname": "web-01", "ipv4": ["10.0.0.5"]}]
        s1 = [
            {"name": "stale-dup-nic", "ipAddress": "10.0.0.5"},  # IP-only
            {"name": "web-01", "ipAddress": "10.0.0.9"},  # hostname match
        ]
        result = classify(tenable, s1)
        self.assertEqual(len(result["matched"]), 1)
        matched_s1 = result["matched"][0][1]
        self.assertEqual(matched_s1["name"], "web-01")
        self.assertEqual(result["ambiguous"], [])

    def test_id_less_s1_assets_do_not_collide_on_none(self):
        # Regression: S1 records missing an `id` field used to collide on
        # `None` and get wrongly excluded from s1_only as a group.
        tenable = []
        s1 = [
            {"name": "no-id-a", "ipAddress": "10.0.0.1"},
            {"name": "no-id-b", "ipAddress": "10.0.0.2"},
        ]
        result = classify(tenable, s1)
        self.assertEqual(len(result["s1_only"]), 2)
        names = {a["name"] for a in result["s1_only"]}
        self.assertEqual(names, {"no-id-a", "no-id-b"})

    def test_ipv6_match_is_ambiguous_not_hostname_confirmed(self):
        # Regression: is_ip() used to only recognize IPv4, so an IPv6-only
        # match got wrongly promoted to "hostname-confirmed".
        tenable = [{"hostname": "web-02", "ipv4": []}]
        s1 = [{"name": "different-name", "networkInterfaces": [{"ip": "fe80::1"}]}]
        tenable[0]["ipv4"] = ["fe80::1"]
        result = classify(tenable, s1)
        self.assertEqual(result["matched"], [])
        self.assertEqual(len(result["ambiguous"]), 1)

    def test_tenable_only_when_no_shared_keys(self):
        tenable = [{"hostname": "orphan", "ipv4": ["10.0.0.99"]}]
        s1 = [{"name": "unrelated", "ipAddress": "10.0.0.100"}]
        result = classify(tenable, s1)
        self.assertEqual(len(result["tenable_only"]), 1)
        self.assertEqual(result["matched"], [])
        self.assertEqual(result["ambiguous"], [])


if __name__ == "__main__":
    unittest.main()
