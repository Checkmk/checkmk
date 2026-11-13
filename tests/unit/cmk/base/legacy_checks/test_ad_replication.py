#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.ad_replication import parse_ad_replication_info


def test_parse_yields_no_rows_without_data() -> None:
    assert parse_ad_replication_info([]) == []


def test_parse_splits_row_into_11_fields() -> None:
    rows = parse_ad_replication_info(
        [
            [
                'showrepl_INFO,SITE-A,DC01,"DC=example,DC=local",SITE-B,DC02,RPC,0,0,2026-11-12',
                "09:48:38,0",
            ]
        ]
    )

    assert rows == [
        [
            "showrepl_INFO",
            "SITE-A",
            "DC01",
            '"DC=example;DC=local"',
            "SITE-B",
            "DC02",
            "RPC",
            "0",
            "0",
            "2026-11-12 09:48:38",
            "0",
        ]
    ]


def test_parse_keeps_naming_context_with_several_commas_in_one_field() -> None:
    rows = parse_ad_replication_info(
        [
            [
                'showrepl_INFO,SITE-A,DC01,"CN=Schema,CN=Configuration,DC=example,DC=local",SITE-B,DC02,RPC,0,0,2026-11-12',
                "09:48:38,0",
            ]
        ]
    )

    assert rows == [
        [
            "showrepl_INFO",
            "SITE-A",
            "DC01",
            '"CN=Schema;CN=Configuration;DC=example;DC=local"',
            "SITE-B",
            "DC02",
            "RPC",
            "0",
            "0",
            "2026-11-12 09:48:38",
            "0",
        ]
    ]


def test_parse_merges_unquoted_naming_context_into_destination_dc_field() -> None:
    rows = parse_ad_replication_info(
        [["showrepl_INFO,SITE-A,DC01,DC=local,SITE-B,DC02,RPC,0,0,2026-11-12", "09:48:38,0"]]
    )

    assert rows == [
        [
            "showrepl_INFO",
            "SITE-A",
            "DC01;DC=local",
            "SITE-B",
            "DC02",
            "RPC",
            "0",
            "0",
            "2026-11-12 09:48:38",
            "0",
        ]
    ]


def test_parse_drops_appended_columns() -> None:
    rows = parse_ad_replication_info(
        [
            [
                'showrepl_INFO,SITE-A,DC01,"DC=example,DC=local",SITE-B,DC02,RPC,0,0,2026-11-12',
                '09:48:38,0,dc01.example.local,dc02.example.local,"DC=example,DC=local","DC=example,DC=local"',
            ]
        ]
    )

    assert rows == [
        [
            "showrepl_INFO",
            "SITE-A",
            "DC01",
            '"DC=example;DC=local"',
            "SITE-B",
            "DC02",
            "RPC",
            "0",
            "0",
            "2026-11-12 09:48:38",
            "0",
        ]
    ]


def test_parse_drops_appended_columns_after_unquoted_naming_context() -> None:
    rows = parse_ad_replication_info(
        [
            [
                "showrepl_INFO,SITE-A,DC01,DC=local,SITE-B,DC02,RPC,0,0,2026-11-12",
                '09:48:38,0,dc01.example.local,dc02.example.local,"DC=example,DC=local","DC=example,DC=local"',
            ]
        ]
    )

    assert rows == [
        [
            "showrepl_INFO",
            "SITE-A",
            "DC01;DC=local",
            "SITE-B",
            "DC02",
            "RPC",
            "0",
            "0",
            "2026-11-12 09:48:38",
            "0",
        ]
    ]


def test_parse_drops_row_with_fewer_than_10_fields() -> None:
    assert parse_ad_replication_info([["showrepl_INFO,SITE-A,DC01,DC=local"]]) == []
