#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from typing import get_type_hints

from cmk.ccc.hostaddress import HostName

from cmk.gui.openapi.api_endpoints.host_config.models.response_models import (
    HostConfigModel,
    HostExtensionsModel,
)
from cmk.gui.openapi.api_endpoints.models.host_attribute_models import HostViewAttributeModel
from cmk.gui.openapi.endpoints.utils import folder_slug
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.openapi.restful_objects import constructors
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import Host

agent_links_hook: Callable[[HostName], list[LinkModel]] = lambda h: []
_static_attribute_names = set(get_type_hints(HostAttributes))


def serialize_host(
    host: Host,
    *,
    compute_effective_attributes: bool,
    compute_links: bool,
) -> HostConfigModel:
    links = []
    if compute_links:
        links = generate_links("host_config", host.id())
        links.append(
            LinkModel.create(
                rel="cmk/folder_config",
                href=constructors.object_href("folder_config", folder_slug(host.folder())),
                method="get",
                title="The folder config of the host.",
            )
        )
        links.extend(agent_links_hook(host.name()))

    return HostConfigModel(
        domainType="host_config",
        id=host.id(),
        title=host.alias() or host.name(),
        links=links,
        members=None,
        extensions=HostExtensionsModel(
            folder=host.folder(),
            attributes=HostViewAttributeModel.from_internal(
                host.attributes, _static_attribute_names
            ),
            effective_attributes=HostViewAttributeModel.from_internal(
                host.effective_attributes(), _static_attribute_names
            )
            if compute_effective_attributes
            else ApiOmitted(),
            is_cluster=host.is_cluster(),
            is_offline=host.is_offline(),
            cluster_nodes=host.cluster_nodes(),
        ),
    )
