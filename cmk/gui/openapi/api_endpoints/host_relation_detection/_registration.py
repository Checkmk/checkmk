#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry

from ._family import HOST_RELATION_DETECTION_FAMILY
from .accept_relations import ENDPOINT_ACCEPT_RELATIONS
from .list_relation_rows import ENDPOINT_LIST_RELATION_ROWS
from .scan_relations import ENDPOINT_SCAN_RELATIONS
from .show_relation_job import ENDPOINT_SHOW_RELATION_JOB
from .suggest_evidence import ENDPOINT_SUGGEST_EVIDENCE


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
) -> None:
    endpoint_family_registry.register(HOST_RELATION_DETECTION_FAMILY)
    versioned_endpoint_registry.register(ENDPOINT_SUGGEST_EVIDENCE)
    versioned_endpoint_registry.register(ENDPOINT_SCAN_RELATIONS)
    versioned_endpoint_registry.register(ENDPOINT_ACCEPT_RELATIONS)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_RELATION_JOB)
    versioned_endpoint_registry.register(ENDPOINT_LIST_RELATION_ROWS)
