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
    ldap_connection,
    notification_rules,
    parent_scan,
    password,
    quick_setup,
    rule,
    ruleset,
    service,
    service_discovery,
    service_group_config,
    site_management,
    time_periods,
    user_config,
    user_role,
    version,
)
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry

from .framework.registry import VersionedEndpointRegistry
from .restful_objects.endpoint_family import EndpointFamilyRegistry
from .shared_endpoint_families.host_config import HOST_CONFIG_FAMILY
from .spec import spec_generator_job


def register(
    endpoint_registry: EndpointRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
    job_registry: BackgroundJobRegistry,
) -> None:
    # TODO: once all legacy endpoints have been migrated the family registry should happen inside
    #  respective endpoint module
    endpoint_family_registry.register(HOST_CONFIG_FAMILY)

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
    ldap_connection.register(endpoint_registry)
    host.register(endpoint_registry)
    host_config.register(endpoint_registry)
    host_group_config.register(endpoint_registry)
    host_internal.register(endpoint_registry)
    host_tag_group.register(endpoint_registry)
    notification_rules.register(endpoint_registry)
    password.register(endpoint_family_registry, endpoint_registry)
    parent_scan.register(endpoint_registry)
    rule.register(endpoint_registry)
    ruleset.register(endpoint_registry)
    service.register(endpoint_registry)
    service_discovery.register(endpoint_registry)
    service_group_config.register(endpoint_registry)
    site_management.register(endpoint_registry)
    time_periods.register(endpoint_registry)
    user_config.register(endpoint_registry)
    user_role.register(endpoint_registry)
    version.register(endpoint_registry)
    spec_generator_job.register(job_registry)
    quick_setup.register(endpoint_registry)
    broker_connection.register(endpoint_registry)
