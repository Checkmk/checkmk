#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import RULE_FAMILY
from .create_rule import ENDPOINT_CREATE_RULE
from .delete_rule import ENDPOINT_DELETE_RULE
from .edit_rule import ENDPOINT_EDIT_RULE
from .list_rules import ENDPOINT_LIST_RULES
from .move_rule import ENDPOINT_MOVE_RULE
from .show_rule import ENDPOINT_SHOW_RULE


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
) -> None:
    endpoint_family_registry.register(RULE_FAMILY)
    versioned_endpoint_registry.register(ENDPOINT_MOVE_RULE)
    versioned_endpoint_registry.register(ENDPOINT_CREATE_RULE)
    versioned_endpoint_registry.register(ENDPOINT_LIST_RULES)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_RULE)
    versioned_endpoint_registry.register(ENDPOINT_DELETE_RULE)
    versioned_endpoint_registry.register(ENDPOINT_EDIT_RULE)
