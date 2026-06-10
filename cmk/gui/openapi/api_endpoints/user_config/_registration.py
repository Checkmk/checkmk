#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry
from cmk.gui.openapi.shared_endpoint_families.user_config import USER_CONFIG_FAMILY

from .create_user import ENDPOINT_CREATE_USER
from .delete_user import ENDPOINT_DELETE_USER
from .dismiss_user_warning import ENDPOINT_DISMISS_USER_WARNING
from .edit_user import ENDPOINT_EDIT_USER
from .list_users import ENDPOINT_LIST_USERS
from .show_user import ENDPOINT_SHOW_USER
from .trigger_user_sync import ENDPOINT_TRIGGER_USER_SYNC


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
) -> None:
    endpoint_family_registry.register(USER_CONFIG_FAMILY)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_USER)
    versioned_endpoint_registry.register(ENDPOINT_LIST_USERS)
    versioned_endpoint_registry.register(ENDPOINT_CREATE_USER)
    versioned_endpoint_registry.register(ENDPOINT_DELETE_USER)
    versioned_endpoint_registry.register(ENDPOINT_EDIT_USER)
    versioned_endpoint_registry.register(ENDPOINT_DISMISS_USER_WARNING)
    versioned_endpoint_registry.register(ENDPOINT_TRIGGER_USER_SYNC)
