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

from .api_endpoints.host_config import registration as api_host_config
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
    endpoint_family_registry.register(HOST_CONFIG_FAMILY, ignore_duplicates=False)

    acknowledgement.register(endpoint_registry, ignore_duplicates=False)
    activate_changes.register(endpoint_registry, ignore_duplicates=False)
    agent.register(endpoint_registry, ignore_duplicates=False)
    audit_log.register(endpoint_registry, ignore_duplicates=False)
    aux_tags.register(endpoint_registry, ignore_duplicates=False)
    background_job.register(endpoint_registry, ignore_duplicates=False)
    cert.register(endpoint_registry, ignore_duplicates=False)
    comment.register(endpoint_registry, ignore_duplicates=False)
    contact_group_config.register(endpoint_registry, ignore_duplicates=False)
    downtime.register(endpoint_registry, ignore_duplicates=False)
    folder_config.register(endpoint_registry, ignore_duplicates=False)
    configuration_entity.register(endpoint_registry, ignore_duplicates=False)
    ldap_connection.register(endpoint_registry, ignore_duplicates=False)
    host.register(endpoint_registry, ignore_duplicates=False)
    host_config.register(endpoint_registry, ignore_duplicates=False)
    host_group_config.register(endpoint_registry, ignore_duplicates=False)
    host_internal.register(endpoint_registry, ignore_duplicates=False)
    host_tag_group.register(endpoint_registry, ignore_duplicates=False)
    notification_rules.register(endpoint_registry, ignore_duplicates=False)
    password.register(endpoint_family_registry, endpoint_registry, ignore_duplicates=False)
    parent_scan.register(endpoint_registry, ignore_duplicates=False)
    rule.register(endpoint_registry, ignore_duplicates=False)
    ruleset.register(endpoint_registry, ignore_duplicates=False)
    service.register(endpoint_registry, ignore_duplicates=False)
    service_discovery.register(endpoint_registry, ignore_duplicates=False)
    service_group_config.register(endpoint_registry, ignore_duplicates=False)
    site_management.register(endpoint_registry, ignore_duplicates=False)
    time_periods.register(endpoint_registry, ignore_duplicates=False)
    user_config.register(endpoint_registry, ignore_duplicates=False)
    user_role.register(endpoint_registry, ignore_duplicates=False)
    version.register(endpoint_registry, ignore_duplicates=False)
    spec_generator_job.register(job_registry)
    quick_setup.register(endpoint_registry, ignore_duplicates=False)
    broker_connection.register(endpoint_registry, ignore_duplicates=False)

    api_host_config.register(versioned_endpoint_registry, ignore_duplicates=False)
