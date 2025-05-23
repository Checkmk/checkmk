#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from omdlib.package_manager import get_edition, select_matching_packages

from cmk.ccc import version


@pytest.mark.parametrize("edition", list(version.Edition))
def test_get_edition(edition: version._EditionValue) -> None:
    assert get_edition(f"1.2.3.{edition.short}") != "unknown"


@pytest.mark.parametrize(
    "version, expected",
    [
        ("2.0.0p39.cee", ["check-mk-enterprise-2.0.0p39"]),
        ("2.1.0p45.cee", ["check-mk-enterprise-2.1.0p45"]),
        ("2.3.0.cee", ["check-mk-enterprise-2.3.0"]),
        ("2.3.0p10.cce", ["check-mk-cloud-2.3.0p10"]),
        ("2.3.0p10.cme", ["check-mk-managed-2.3.0p10"]),
        ("2.3.0-2024.07.16.cee", ["check-mk-enterprise-2.3.0-2024.07.16"]),
        ("2.4.0-2024.07.16.cee", ["check-mk-enterprise-2.4.0-2024.07.16"]),
    ],
)
def test_select_matching_packages(version: str, expected: Sequence[str]) -> None:
    installed_packages = [
        "check-mk-agent",
        "check-mk-cloud-2.3.0p10",
        "check-mk-cloud-2.3.0p8",
        "check-mk-enterprise-2.0.0p39",
        "check-mk-enterprise-2.1.0p45",
        "check-mk-enterprise-2.2.0p11",
        "check-mk-enterprise-2.2.0p23",
        "check-mk-enterprise-2.3.0",
        "check-mk-enterprise-2.3.0-2024.07.16",
        "check-mk-enterprise-2.3.0p9",
        "check-mk-enterprise-2.4.0-2024.07.16",
        "check-mk-free-2.1.0p40",
        "check-mk-free-2.1.0p41",
        "check-mk-managed-2.3.0p10",
        "check-mk-managed-2.3.0p7",
        "check-mk-raw-2.2.0p26",
        "check-mk-raw-2.3.0p7",
        "check-mk-raw-2.4.0-2024.03.18",
        "check-mk-raw-2.4.0-2024.04.16",
        "cheese",
    ]
    assert select_matching_packages(version, installed_packages) == expected
