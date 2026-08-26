#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""CI gate for the stricter Content-Security-Policy (CMK-31353, CMK-36955).

For every GUI page that has opted into the strict CSP, loading the page must not
produce any CSP violation. A violation means the page still emits something the
strict policy forbids (an inline script, eval, or a blocked resource) - i.e. it
is not actually ready to be served strict, so CI must fail.

Scope: this catches *load-time* violations (inline <script>, eval, blocked
resource loads), which surface as `securitypolicyviolation` events on load.
Violations that only fire on interaction (inline onclick/onfocus handlers) are
not covered here - exercising those needs per-page interaction.
"""

import logging
from urllib.parse import urljoin

import pytest

from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.testlib.site import Site

logger = logging.getLogger(__name__)

# Pages that serve the strict CSP. Keep in sync with the page handlers that call
# Response.set_content_security_policy(STRICT_CONTENT_SECURITY_POLICY) - see
# cmk.gui.http.STRICT_CONTENT_SECURITY_POLICY. Add a page here when it is opted
# into the strict policy.
STRICT_CSP_PAGES: list[str] = []

# Registered on every navigation before page scripts run, so it captures
# violations from the page's own inline scripts.
_CAPTURE_CSP_VIOLATIONS = """
window.__cspViolations = [];
window.addEventListener('securitypolicyviolation', (event) => {
    window.__cspViolations.push(
        event.violatedDirective + ' blocked ' +
        (event.blockedURI || event.sourceFile || 'inline')
    );
});
"""


@pytest.mark.parametrize("page_name", STRICT_CSP_PAGES)
def test_strict_csp_page_has_no_violations(
    dashboard_page: MainDashboard, test_site: Site, page_name: str
) -> None:
    """A strict-CSP page must load without any Content-Security-Policy violation."""
    page = dashboard_page.page
    page.add_init_script(_CAPTURE_CSP_VIOLATIONS)
    page.goto(urljoin(test_site.internal_url, page_name), wait_until="networkidle")

    violations: list[str] = page.evaluate("window.__cspViolations || []")
    assert not violations, f"{page_name} triggered CSP violations:\n" + "\n".join(violations)
