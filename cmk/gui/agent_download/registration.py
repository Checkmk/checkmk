#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.paths
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.watolib.mode import ModeRegistry

from ._endpoints import download_agent, ENDPOINT_DOWNLOAD_BY_TOKEN
from ._pages import (
    _plugin_family_agents,
    DOWNLOAD_AGENT_PLUGIN_PAGE,
    DOWNLOAD_LOCAL_AGENT_PLUGIN_PAGE,
    ModeDownloadAgentsLinux,
    ModeDownloadAgentsOther,
    ModeDownloadAgentsWindows,
    PageDownloadAgentPlugin,
)


def register_endpoints(
    endpoint_registry: EndpointRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
) -> None:
    endpoint_registry.register(download_agent)
    versioned_endpoint_registry.register(ENDPOINT_DOWNLOAD_BY_TOKEN)


def register(
    page_registry: PageRegistry,
    mode_registry: ModeRegistry,
    endpoint_registry: EndpointRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
) -> None:
    mode_registry.register(ModeDownloadAgentsOther)
    mode_registry.register(ModeDownloadAgentsWindows)
    mode_registry.register(ModeDownloadAgentsLinux)

    # The endpoints handing out the files need to filter for allowed ones themselves!
    # Bonus: fills the cache of _plugin_family_agents at apache load.
    available_dirs = [d.path for family in _plugin_family_agents() for d in family.dirs]
    page_registry.register(
        PageEndpoint(
            f"noauth:{DOWNLOAD_AGENT_PLUGIN_PAGE}",
            PageDownloadAgentPlugin(
                [p for p in available_dirs if not p.is_relative_to(cmk.utils.paths.local_root)],
                require_permission=False,
            ),
        )
    )
    page_registry.register(
        PageEndpoint(
            DOWNLOAD_LOCAL_AGENT_PLUGIN_PAGE,
            PageDownloadAgentPlugin(
                available_dirs,
                require_permission=True,
            ),
        )
    )
    register_endpoints(endpoint_registry, versioned_endpoint_registry)
