#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator

import pytest

from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.setup.analyze_configuration import (
    AnalyzeConfiguration,
)
from tests.testlib.site import Site

EXPECTED_CHECKS = [
    "Broken GUI extensions",
    "Deprecated GUI extensions",
    "Deprecated HW/SW Inventory plug-ins",
    "Deprecated PNP templates",
    "Deprecated check man pages",
    "Deprecated check plug-ins (legacy)",
    "Deprecated check plug-ins (v1)",
    "Deprecated legacy GUI extensions",
    "Deprecated rule sets",
    "Unknown check parameter rule sets",
    "Alert handler: Don't handle all check executions",
    "Apache number of processes",
    "Apache process usage",
    "Check helper usage",
    "Checkmk checker count",
    "Checkmk checker usage",
    "Checkmk fetcher usage",
    "Checkmk helper usage",
    "Livestatus usage",
    "Number of users",
    "Temporary filesystem mounted",
    "Backup configured",
    "Encrypt notification daemon communication",
    "Escape HTML globally enabled",
    "Livestatus encryption",
    "Secure GUI (HTTP)",
]

DEPRECATION_STATUSES = {
    "Deprecated GUI extensions": "WARN",
    "Deprecated HW/SW Inventory plug-ins": "CRIT",
    "Deprecated PNP templates": "CRIT",
    "Deprecated check man pages": "CRIT",
    "Deprecated check plug-ins (legacy)": "CRIT",
    "Deprecated check plug-ins (v1)": "CRIT",
    "Deprecated legacy GUI extensions": "WARN",
}


@pytest.fixture
def simulate_deprecations(test_site: Site) -> Iterator[None]:
    """Simulate deprecated extensions, plug-ins, PNP templates, etc. by creating
    fake files in the specified locations."""
    paths = [
        "local/lib/python3/cmk/gui/plugins",
        "local/share/check_mk/inventory",
        "local/share/check_mk/pnp-templates",
        "local/share/check_mk/checkman",
        "local/share/check_mk/checks",
        "local/lib/python3/cmk/base/plugins/agent_based",
        "local/share/check_mk/web",
    ]
    for path in paths:
        test_site.makedirs(path)
        test_site.write_file(f"{path}/fake.py", "print('Fake')")
    yield
    for path in paths:
        test_site.delete_file(f"{path}/fake.py")


def test_analyze_configuration_page(dashboard_page: Dashboard, simulate_deprecations: None) -> None:
    """Test 'Analyze configuration' page when 'Deprecations' file-based checks are triggered.

    1. Trigger 'Deprecations' file-based checks by adding fake files in the specified locations.
    2. Navigate to the 'Analyze configuration' page and verify that all expected checks are present.
    3. Verify that 'Deprecations' file-based checks have the expected statuses.
    """
    analyze_configuration_page = AnalyzeConfiguration(dashboard_page.page)
    analyze_configuration_page.verify_all_expected_checks_are_present(EXPECTED_CHECKS)
    analyze_configuration_page.verify_checks_statuses(DEPRECATION_STATUSES)
