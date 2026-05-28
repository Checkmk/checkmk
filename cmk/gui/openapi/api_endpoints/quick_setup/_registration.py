#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import QUICK_SETUP_FAMILY
from .edit_quick_setup import ENDPOINT_EDIT_QUICK_SETUP
from .get_action_result import ENDPOINT_GET_ACTION_RESULT
from .get_quick_setup import ENDPOINT_GET_QUICK_SETUP
from .get_stage_action_result import ENDPOINT_GET_STAGE_ACTION_RESULT
from .get_stage_structure import ENDPOINT_GET_STAGE_STRUCTURE
from .run_quick_setup_action import ENDPOINT_RUN_QUICK_SETUP_ACTION
from .run_stage_action import ENDPOINT_RUN_STAGE_ACTION


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
) -> None:
    endpoint_family_registry.register(QUICK_SETUP_FAMILY)
    versioned_endpoint_registry.register(ENDPOINT_GET_QUICK_SETUP)
    versioned_endpoint_registry.register(ENDPOINT_GET_STAGE_STRUCTURE)
    versioned_endpoint_registry.register(ENDPOINT_RUN_STAGE_ACTION)
    versioned_endpoint_registry.register(ENDPOINT_GET_STAGE_ACTION_RESULT)
    versioned_endpoint_registry.register(ENDPOINT_RUN_QUICK_SETUP_ACTION)
    versioned_endpoint_registry.register(ENDPOINT_EDIT_QUICK_SETUP)
    versioned_endpoint_registry.register(ENDPOINT_GET_ACTION_RESULT)
