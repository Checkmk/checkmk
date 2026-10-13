#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _

# TODO: replace this suffix match with a real resource server registration
# mechanism once more than one OAuth resource exists. The MCP server builds
# its resource URL in cmk.gui.nonfree.pro.mcp.mcp_server_url() -- not
# imported here, since the OAuth token list pages must stay edition-agnostic.
_MCP_RESOURCE_SUFFIX = "/check_mk/mcp"


def resource_display_name(resource: str | None) -> str:
    """A human-readable label for a token's bound resource, or the raw value if unknown."""
    if resource is None:
        return ""
    if resource.endswith(_MCP_RESOURCE_SUFFIX):
        return _("MCP")
    return resource
