#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import COMMENT_FAMILY
from .create_host_comment import ENDPOINT_CREATE_HOST_COMMENT
from .create_service_comment import ENDPOINT_CREATE_SERVICE_COMMENT
from .delete_comments import ENDPOINT_DELETE_COMMENTS
from .show_comment import ENDPOINT_SHOW_COMMENT
from .show_comments import ENDPOINT_SHOW_COMMENTS


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
) -> None:
    endpoint_family_registry.register(COMMENT_FAMILY)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_COMMENT)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_COMMENTS)
    versioned_endpoint_registry.register(ENDPOINT_CREATE_HOST_COMMENT)
    versioned_endpoint_registry.register(ENDPOINT_CREATE_SERVICE_COMMENT)
    versioned_endpoint_registry.register(ENDPOINT_DELETE_COMMENTS)
