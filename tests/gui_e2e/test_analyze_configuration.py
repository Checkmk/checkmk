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

DEFAULT_STATUSES = {
    "Broken GUI extensions": "OK",
    "Deprecated GUI extensions": "OK",
    "Deprecated HW/SW Inventory plug-ins": "OK",
    "Deprecated PNP templates": "OK",
    "Deprecated check man pages": "OK",
    "Deprecated check plug-ins (legacy)": "OK",
    "Deprecated check plug-ins (v1)": "OK",
    "Deprecated legacy GUI extensions": "OK",
    "Deprecated rule sets": "OK",
    "Unknown check parameter rule sets": "OK",
    "Alert handler: Don't handle all check executions": "OK",
    "Apache number of processes": "WARN",
    "Apache process usage": "OK",
    "Check helper usage": "OK",
    "Checkmk checker count": "OK",
    "Checkmk checker usage": "OK",
    "Checkmk fetcher usage": "OK",
    "Checkmk helper usage": "OK",
    "Livestatus usage": "OK",
    "Number of users": "OK",
    "Temporary filesystem mounted": "OK",
    "Backup configured": "WARN",
    "Encrypt notification daemon communication": "OK",
    "Escape HTML globally enabled": "OK",
    "Livestatus encryption": "CRIT",
    "Secure GUI (HTTP)": "WARN",
}

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
        "local/lib/check_mk/gui/plugins",
        "local/share/check_mk/inventory",
        "local/share/check_mk/pnp-templates",
        "local/share/check_mk/checkman",
        "local/share/check_mk/checks",
        "local/lib/check_mk/base/plugins/agent_based",
        "local/share/check_mk/web",
    ]
    for path in paths:
        test_site.makedirs(path)
        test_site.write_text_file(f"{path}/fake.py", "print('Fake')")
    yield
    for path in paths:
        test_site.delete_file(f"{path}/fake.py")


def test_analyze_configuration_statuses(dashboard_page: Dashboard) -> None:
    """Navigate to the 'Analyze configuration' page and verify that configuration checks
    have the expected statuses.
    """
    analyze_configuration_page = AnalyzeConfiguration(dashboard_page.page)
    analyze_configuration_page.verify_checks_statuses(DEFAULT_STATUSES)


def test_deprecated_configuration_statuses(
    dashboard_page: Dashboard, simulate_deprecations: None
) -> None:
    """Test that 'Deprecations' file-based checks are working as expected.

    Simulate deprecated extensions, plug-ins, etc. and verify that the configuration checks
    statuses are updated accordingly.
    """
    analyze_configuration_page = AnalyzeConfiguration(dashboard_page.page)
    analyze_configuration_page.verify_checks_statuses(DEPRECATION_STATUSES)
