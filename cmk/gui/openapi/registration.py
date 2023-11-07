#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.openapi.endpoints import (
    acknowledgement,
    activate_changes,
    agent,
    audit_log,
    aux_tags,
    bi,
    cert,
    comment,
    contact_group_config,
    downtime,
    host,
    host_group_config,
    host_internal,
    host_tag_group,
    metric,
    notification_rules,
    password,
    rule,
    ruleset,
    service,
    service_group_config,
    site_management,
    time_periods,
    user_config,
    user_role,
    version,
)
from cmk.gui.openapi.restful_objects.endpoint_registry import ENDPOINT_REGISTRY
from cmk.gui.watolib.host_attributes import host_attribute_registry


def register() -> None:
    # This is a hack to make all host attributes available before loading the openapi plugins. The
    # modules would be loaded later on by cmk.gui.cee.agent_bakery.registration.register(), but the
    # openapi code imported here requires all host_attributes to be present before loading it.
    # This can be cleaned up once we have refactored the registration here.
    try:
        from cmk.gui.cee.agent_bakery._host_attribute import (
            HostAttributeBakeAgentPackage,  # pylint: disable=no-name-in-module
        )

        host_attribute_registry.register(HostAttributeBakeAgentPackage)
    except ImportError:
        pass

    from cmk.gui.openapi.endpoints import folder_config, host_config, service_discovery

    acknowledgement.register(ENDPOINT_REGISTRY)
    activate_changes.register(ENDPOINT_REGISTRY)
    agent.register(ENDPOINT_REGISTRY)
    audit_log.register(ENDPOINT_REGISTRY)
    aux_tags.register(ENDPOINT_REGISTRY)
    bi.register(ENDPOINT_REGISTRY)
    cert.register(ENDPOINT_REGISTRY)
    comment.register(ENDPOINT_REGISTRY)
    contact_group_config.register(ENDPOINT_REGISTRY)
    downtime.register(ENDPOINT_REGISTRY)
    folder_config.register(ENDPOINT_REGISTRY)
    host.register(ENDPOINT_REGISTRY)
    host_config.register(ENDPOINT_REGISTRY)
    host_group_config.register(ENDPOINT_REGISTRY)
    host_internal.register(ENDPOINT_REGISTRY)
    host_tag_group.register(ENDPOINT_REGISTRY)
    metric.register(ENDPOINT_REGISTRY)
    notification_rules.register(ENDPOINT_REGISTRY)
    password.register(ENDPOINT_REGISTRY)
    rule.register(ENDPOINT_REGISTRY)
    ruleset.register(ENDPOINT_REGISTRY)
    service.register(ENDPOINT_REGISTRY)
    service_discovery.register(ENDPOINT_REGISTRY)
    service_group_config.register(ENDPOINT_REGISTRY)
    site_management.register(ENDPOINT_REGISTRY)
    time_periods.register(ENDPOINT_REGISTRY)
    user_config.register(ENDPOINT_REGISTRY)
    user_role.register(ENDPOINT_REGISTRY)
    version.register(ENDPOINT_REGISTRY)
