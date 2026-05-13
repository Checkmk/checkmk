#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.agent_registration.api.registration import (
    register_endpoints as agent_registration_register_endpoints,
)
from cmk.gui.availability.openapi.registration import (
    register as availability_register,
)
from cmk.gui.background_job.wato._job_ui import (
    register as background_jobs_register_permissions,
)
from cmk.gui.bi._openapi import register as bi_register
from cmk.gui.bi.permissions import register_permissions as bi_register_permissions
from cmk.gui.dashboard.api._registration import (
    register_endpoints as dashboard_register_endpoints,
)
from cmk.gui.data_source._openapi._registration import (
    register_endpoints as data_source_register_endpoints,
)
from cmk.gui.default_permissions import register as default_permissions_register
from cmk.gui.i18n import _
from cmk.gui.inventory._openapi import register as inventory_register
from cmk.gui.ldap_integration._openapi import register as ldap_register
from cmk.gui.mkeventd._openapi.current_events._registration import (
    register as mkeventd_current_events_register,
)
from cmk.gui.mkeventd._openapi.historical_events._registration import (
    register as mkeventd_historical_events_register,
)
from cmk.gui.mkeventd.permission_section import PERMISSION_SECTION_EVENT_CONSOLE
from cmk.gui.mkeventd.views import (
    register_permissions as mkeventd_views_register_permissions,
)
from cmk.gui.mkeventd.wato import (
    register_permissions as mkeventd_wato_register_permissions,
)
from cmk.gui.openapi import (
    endpoint_family_registry,
    endpoint_registry,
    versioned_endpoint_registry,
)
from cmk.gui.openapi.endpoints import autocomplete
from cmk.gui.openapi.endpoints import metric as metric_endpoint
from cmk.gui.openapi.registration import register as openapi_central_register
from cmk.gui.pagetypes import declare as pagetypes_declare
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.pagetypes._openapi._registration import register as pagetypes_register
from cmk.gui.permissions import permission_registry, permission_section_registry
from cmk.gui.sidebar._openapi.registration import register as sidebar_register
from cmk.gui.user_message.api._registration import (
    register_endpoints as user_message_register_endpoints,
)
from cmk.gui.views._openapi._registration import (
    register_endpoints as views_register_endpoints,
)
from cmk.gui.views.command.commands import (
    register_permissions as command_register_permissions,
)
from cmk.gui.visuals import declare_visual_permissions
from cmk.gui.visuals.filter.api._registration import (
    register as visuals_filter_register,
)
from cmk.gui.visuals.info._openapi._registration import (
    register_endpoints as visuals_info_register_endpoints,
)
from cmk.gui.wato._permissions import register as wato_permissions_register


def register_for_community() -> None:
    default_permissions_register(permission_section_registry, permission_registry)
    wato_permissions_register(permission_section_registry, permission_registry)
    bi_register_permissions(permission_section_registry, permission_registry)
    command_register_permissions(permission_section_registry, permission_registry)
    background_jobs_register_permissions(permission_section_registry, permission_registry)
    permission_section_registry.register(PERMISSION_SECTION_EVENT_CONSOLE)
    mkeventd_views_register_permissions(permission_registry)
    mkeventd_wato_register_permissions(permission_registry)
    declare_visual_permissions("dashboards", _("dashboards"))
    declare_visual_permissions("views", _("views"))
    pagetypes_declare(PagetypeTopics)

    pagetypes_register(
        endpoint_family_registry=endpoint_family_registry,
        versioned_endpoint_registry=versioned_endpoint_registry,
    )
    data_source_register_endpoints(endpoint_family_registry, versioned_endpoint_registry)
    views_register_endpoints(endpoint_family_registry, versioned_endpoint_registry)
    inventory_register(endpoint_family_registry, versioned_endpoint_registry)
    dashboard_register_endpoints(endpoint_family_registry, versioned_endpoint_registry)
    bi_register(endpoint_registry)
    user_message_register_endpoints(endpoint_family_registry, versioned_endpoint_registry)
    agent_registration_register_endpoints(endpoint_family_registry, versioned_endpoint_registry)
    openapi_central_register(
        endpoint_registry,
        versioned_endpoint_registry,
        endpoint_family_registry,
    )
    availability_register(versioned_endpoint_registry, endpoint_family_registry)
    ldap_register(endpoint_registry)
    visuals_filter_register(endpoint_family_registry, versioned_endpoint_registry)
    visuals_info_register_endpoints(endpoint_family_registry, versioned_endpoint_registry)
    sidebar_register(versioned_endpoint_registry, endpoint_family_registry)
    mkeventd_historical_events_register(
        versioned_endpoint_registry=versioned_endpoint_registry,
        endpoint_family_registry=endpoint_family_registry,
    )
    mkeventd_current_events_register(
        versioned_endpoint_registry=versioned_endpoint_registry,
        endpoint_family_registry=endpoint_family_registry,
    )

    autocomplete.register(endpoint_registry)
    metric_endpoint.register(endpoint_registry)
