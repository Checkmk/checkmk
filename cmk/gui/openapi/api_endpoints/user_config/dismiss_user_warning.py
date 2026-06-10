#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.shared_endpoint_families.user_config import USER_CONFIG_FAMILY

from .models.request_models import UserDismissWarningModel


def dismiss_user_warning_v1(body: UserDismissWarningModel) -> None:
    """Save a warning dismissal for the current user."""
    warnings = user.dismissed_warnings or set()
    warnings.add(body.warning)
    user.dismissed_warnings = warnings


ENDPOINT_DISMISS_USER_WARNING = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("user_config", "dismiss-warning"),
        link_relation=".../action",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(),
    doc=EndpointDoc(family=USER_CONFIG_FAMILY.name, group="Checkmk Internal"),
    versions={APIVersion.V1: EndpointHandler(handler=dismiss_user_warning_v1)},
)
