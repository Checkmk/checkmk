#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.background_job import BackgroundJobRegistry
from cmk.gui.openapi.endpoints import (
    acknowledgement,
    activate_changes,
    agent,
    audit_log,
    aux_tags,
    background_job,
    broker_connection,
    cert,
    comment,
    configuration_entity,
    contact_group_config,
    downtime,
    folder_config,
    host,
    host_config,
    host_group_config,
    host_internal,
    host_tag_group,
    notification_rules,
    parent_scan,
    quick_setup,
    rule,
    ruleset,
    service,
    service_discovery,
    service_group_config,
    time_periods,
    user_config,
    version,
)
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry

from .api_endpoints import agent_download, icon, pagetype_topic, site_management
from .api_endpoints import host_config as api_host_config
from .api_endpoints import host_config_internal as api_host_config_internal
from .api_endpoints.graph_timerange import registration as api_graph_timerange
from .api_endpoints.password import registration as api_password
from .api_endpoints.sidebar_element import registration as sidebar_element
from .api_endpoints.user_role import registration as api_user_role
from .framework.registry import VersionedEndpointRegistry
from .restful_objects.endpoint_family import EndpointFamilyRegistry
from .shared_endpoint_families.agent import AGENTS_FAMILY
from .shared_endpoint_families.host_config import HOST_CONFIG_FAMILY


def register(
    endpoint_registry: EndpointRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
    job_registry: BackgroundJobRegistry,
) -> None:
    # TODO: once all legacy endpoints have been migrated the family registry should happen inside
    #  respective endpoint module
    endpoint_family_registry.register(HOST_CONFIG_FAMILY)
    endpoint_family_registry.register(AGENTS_FAMILY)

    acknowledgement.register(endpoint_registry)
    activate_changes.register(endpoint_registry)
    agent.register(endpoint_registry)
    audit_log.register(endpoint_registry)
    aux_tags.register(endpoint_registry)
    background_job.register(endpoint_registry)
    cert.register(endpoint_registry)
    comment.register(endpoint_registry)
    contact_group_config.register(endpoint_registry)
    downtime.register(endpoint_registry)
    folder_config.register(endpoint_registry)
    configuration_entity.register(endpoint_registry)
    host.register(endpoint_registry)
    host_config.register(endpoint_registry)
    host_group_config.register(endpoint_registry)
    host_internal.register(endpoint_registry)
    host_tag_group.register(endpoint_registry)
    notification_rules.register(endpoint_registry)
    parent_scan.register(endpoint_registry)
    rule.register(endpoint_registry)
    ruleset.register(endpoint_registry)
    service.register(endpoint_registry)
    service_discovery.register(endpoint_registry)
    service_group_config.register(endpoint_registry)
    time_periods.register(endpoint_registry)
    user_config.register(endpoint_registry)
    version.register(endpoint_registry)
    quick_setup.register(endpoint_registry)
    broker_connection.register(endpoint_registry)

    agent_download.register(versioned_endpoint_registry)
    api_host_config.register(versioned_endpoint_registry)
    api_host_config_internal.register(versioned_endpoint_registry)
    api_user_role.register(
        versioned_endpoint_registry=versioned_endpoint_registry,
        endpoint_family_registry=endpoint_family_registry,
    )
    api_password.register(
        versioned_endpoint_registry=versioned_endpoint_registry,
        endpoint_family_registry=endpoint_family_registry,
    )
    api_graph_timerange.register(
        versioned_endpoint_registry=versioned_endpoint_registry,
        endpoint_family_registry=endpoint_family_registry,
    )
    pagetype_topic.register(
        versioned_endpoint_registry=versioned_endpoint_registry,
        endpoint_family_registry=endpoint_family_registry,
    )
    sidebar_element.register(
        versioned_endpoint_registry=versioned_endpoint_registry,
        endpoint_family_registry=endpoint_family_registry,
    )
    site_management.register(
        versioned_endpoint_registry=versioned_endpoint_registry,
        endpoint_family_registry=endpoint_family_registry,
    )
    icon.register(
        versioned_endpoint_registry=versioned_endpoint_registry,
        endpoint_family_registry=endpoint_family_registry,
    )
