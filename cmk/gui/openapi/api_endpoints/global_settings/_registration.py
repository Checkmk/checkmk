#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import GLOBAL_SETTINGS_FAMILY
from .delete_global_setting import ENDPOINT_DELETE_GLOBAL_SETTING
from .delete_site_global_setting import ENDPOINT_DELETE_SITE_GLOBAL_SETTING
from .show_global_setting import ENDPOINT_SHOW_GLOBAL_SETTING
from .show_site_global_setting import ENDPOINT_SHOW_SITE_GLOBAL_SETTING
from .update_global_setting import ENDPOINT_UPDATE_GLOBAL_SETTING
from .update_site_global_setting import ENDPOINT_UPDATE_SITE_GLOBAL_SETTING


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
) -> None:
    endpoint_family_registry.register(GLOBAL_SETTINGS_FAMILY)

    versioned_endpoint_registry.register(ENDPOINT_SHOW_GLOBAL_SETTING)
    versioned_endpoint_registry.register(ENDPOINT_UPDATE_GLOBAL_SETTING)
    versioned_endpoint_registry.register(ENDPOINT_DELETE_GLOBAL_SETTING)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_SITE_GLOBAL_SETTING)
    versioned_endpoint_registry.register(ENDPOINT_UPDATE_SITE_GLOBAL_SETTING)
    versioned_endpoint_registry.register(ENDPOINT_DELETE_SITE_GLOBAL_SETTING)
