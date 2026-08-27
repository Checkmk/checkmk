#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.authorization import READ_PERMISSIONS
from cmk.gui.openapi.framework.registry import versioned_endpoint_registry
from cmk.gui.openapi.restful_objects.registry import endpoint_registry
from cmk.gui.utils.permission_verification import BasePerm

# The REST endpoints used by the MCP tools. May diverge, but for now they are simple enough.
_READ_ONLY_TOOL_ENDPOINTS = [
    ("checkmk_version", "get", "/version"),
    ("get_hosts", "post", "/domain-types/host/collections/all"),
    ("get_services", "post", "/domain-types/service/collections/all"),
    ("get_monitoring_overview", "post", "/domain-types/host/collections/all"),
    ("get_monitoring_overview", "post", "/domain-types/service/collections/all"),
    ("get_comments", "get", "/domain-types/comment/collections/{collection_name}"),
    ("get_downtimes", "get", "/domain-types/downtime/collections/all"),
    ("get_ec_events", "get", "/domain-types/event_console/collections/all"),
    ("get_ec_events", "get", "/domain-types/historical_event/collections/all"),
    ("get_availability", "get", "/objects/host_availability/{host_name}"),
    ("get_availability", "get", "/domain-types/service_availability/collections/all"),
    ("get_metric_history", "post", "/domain-types/metric/actions/get/invoke"),
    ("get_metric_history", "post", "/domain-types/graph/actions/translate_metric_names/invoke"),
    ("get_config_changes", "get", "/domain-types/audit_log/collections/all"),
    ("read_setup_configuration", "get", "/objects/host_config/{host_name}"),
    ("read_setup_configuration", "get", "/objects/folder_config/{folder}"),
]


def _declared_permissions(method: str, path: str) -> BasePerm | None:
    """Return the set of permissions an endpoint declares (see BasePerm)."""
    for endpoint in versioned_endpoint_registry:
        if endpoint.metadata.method == method and endpoint.metadata.path == path:
            return endpoint.permissions.required
    for legacy_endpoint in endpoint_registry:
        if legacy_endpoint.method == method and legacy_endpoint.path == path:
            return legacy_endpoint.permissions_required
    raise LookupError(f"no endpoint registered for {method.upper()} {path}")


@pytest.mark.usefixtures("load_plugins")
@pytest.mark.parametrize(("tool", "method", "path"), _READ_ONLY_TOOL_ENDPOINTS)
def test_read_scope_satisfies_the_endpoints_of_a_read_only_tool(
    tool: str, method: str, path: str
) -> None:
    """
    Check that the read-only scope (READ_PERMISSIONS) is sufficient to call the endpoints behind
    the MCP's read-only tools.

    This is checked via declared permissions system from cmk.web.utils.permission_verification,
    not by actually calling the endpoint.
    """
    if required := _declared_permissions(method, path):
        assert required.validate(sorted(READ_PERMISSIONS)), (
            f"{tool} would be denied: {method.upper()} {path} requires {required}"
        )
