#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import FOLDER_CONFIG_FAMILY
from .bulk_update_folder import ENDPOINT_BULK_UPDATE_FOLDER
from .create_folder import ENDPOINT_CREATE_FOLDER
from .delete_folder import ENDPOINT_DELETE_FOLDER
from .hosts_of_folder import ENDPOINT_HOSTS_OF_FOLDER
from .list_folders import ENDPOINT_LIST_FOLDERS
from .move_folder import ENDPOINT_MOVE_FOLDER
from .show_folder import ENDPOINT_SHOW_FOLDER
from .update_folder import ENDPOINT_UPDATE_FOLDER


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
) -> None:
    endpoint_family_registry.register(FOLDER_CONFIG_FAMILY)
    versioned_endpoint_registry.register(ENDPOINT_CREATE_FOLDER)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_FOLDER)
    versioned_endpoint_registry.register(ENDPOINT_LIST_FOLDERS)
    versioned_endpoint_registry.register(ENDPOINT_UPDATE_FOLDER)
    versioned_endpoint_registry.register(ENDPOINT_MOVE_FOLDER)
    versioned_endpoint_registry.register(ENDPOINT_DELETE_FOLDER)
    versioned_endpoint_registry.register(ENDPOINT_BULK_UPDATE_FOLDER)
    versioned_endpoint_registry.register(ENDPOINT_HOSTS_OF_FOLDER)
