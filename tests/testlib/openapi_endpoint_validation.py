#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Helper for validating that every registered versioned endpoint is framework-valid.

Endpoint validity is a static property of an endpoint definition (its handler
annotations, request/response models, parameter sources), independent of which
edition or feature configuration happens to register it. The unit test lanes are
edition-pinned, so a test walking the ambient registry only ever validates the
endpoints registered for its own edition; endpoints exposed only by another
edition slip through unchecked.

This helper drives the per-edition slim registration (the same path the spec
generator uses) into freshly emptied registries, so a per-edition test validates
exactly the endpoints that edition exposes. Run once per edition lane, the set of
these tests covers every endpoint the product ships.
"""

import pytest

from cmk.ccc.version import Edition
from cmk.gui.openapi import versioned_endpoint_registry
from cmk.gui.openapi.framework import validate_endpoint_definition
from cmk.gui.openapi.framework.api_config import APIConfig
from tests.testlib.openapi_slim_registration import register_edition_into_empty_registries


def assert_registered_endpoints_valid(
    edition: Edition,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate every versioned endpoint the given edition registers.

    Re-registers ``edition`` via the slim registration path into emptied
    registries, then asserts that every endpoint passes framework validation and
    that no two endpoints share a (family, link relation) key within the same API
    version. A single endpoint may expose several API versions (e.g. a stable and
    an internal shape), so the key uniqueness is per version, not global.
    """
    register_edition_into_empty_registries(edition, monkeypatch)

    versioned_endpoints = list(versioned_endpoint_registry)
    if not versioned_endpoints:
        raise AssertionError(
            f"slim registration for edition {edition.long!r} left the versioned registry empty"
        )

    for endpoint in versioned_endpoints:
        validate_endpoint_definition(endpoint)

    for version in APIConfig.RELEASED_VERSIONS_IN_ORDER:
        seen_endpoints: set[tuple[str, str]] = set()
        for endpoint in versioned_endpoint_registry.specified_endpoints(version):
            endpoint_key = (endpoint.family.name, endpoint.metadata.link_relation)
            if endpoint_key in seen_endpoints:
                raise AssertionError(
                    f"Duplicate endpoint detected in version {version.value}: {endpoint_key}"
                )
            seen_endpoints.add(endpoint_key)
