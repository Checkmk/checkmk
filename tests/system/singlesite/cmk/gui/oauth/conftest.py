#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from tests.testlib.site import Site

# The OMD config variable backing the "Enable MCP server" global setting. Setting
# it to "on" and restarting the site is what ``ConfigDomainOMD`` does when the
# global setting is activated. MCP is the only current oauth.registration.register() caller.
_MCP_SERVER_CONFIG = "MCP_SERVER"


@pytest.fixture(name="mcp_enabled_site", scope="module")
def _mcp_enabled_site(site: Site) -> Iterator[Site]:
    """Enable the MCP server for the tests in this module and restore afterward.

    ``omd_config`` sets ``MCP_SERVER=on`` (restarting the site to apply it) and
    restores the previous value and run state on teardown. Scoped to the module
    so the enable/restore restart happens once for all tests here.
    """
    with site.omd_config(_MCP_SERVER_CONFIG, "on"):
        yield site
