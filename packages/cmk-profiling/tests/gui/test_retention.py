#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.profiling.gui._store import DEFAULT_MAX_PROFILES, retention_kwargs


def test_retention_kwargs_empty_defaults_to_store_defaults() -> None:
    assert retention_kwargs({}) == {
        "max_count": DEFAULT_MAX_PROFILES,
        "max_age_days": None,
    }


def test_retention_kwargs_valid_values() -> None:
    assert retention_kwargs({"max_count": 50, "max_age_days": 7}) == {
        "max_count": 50,
        "max_age_days": 7,
    }


def test_retention_kwargs_rejects_zero() -> None:
    """max_age_days=0 or max_count=0 must fall back; 0 means 'wipe all'."""
    assert retention_kwargs({"max_count": 0, "max_age_days": 0}) == {
        "max_count": DEFAULT_MAX_PROFILES,
        "max_age_days": None,
    }


def test_retention_kwargs_rejects_negative() -> None:
    assert retention_kwargs({"max_count": -5, "max_age_days": -1}) == {
        "max_count": DEFAULT_MAX_PROFILES,
        "max_age_days": None,
    }


def test_retention_kwargs_rejects_wrong_types() -> None:
    assert retention_kwargs({"max_count": "50", "max_age_days": "7"}) == {
        "max_count": DEFAULT_MAX_PROFILES,
        "max_age_days": None,
    }


def test_retention_kwargs_ignores_unknown_keys() -> None:
    assert retention_kwargs({"enabled": True, "other": 42}) == {
        "max_count": DEFAULT_MAX_PROFILES,
        "max_age_days": None,
    }
