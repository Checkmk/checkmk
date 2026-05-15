#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Helper for asserting parity between the spec-generator slim registration and
the app registration.

The OpenAPI spec generator uses a stripped-down registration path
(:mod:`cmk.gui.openapi.spec.editions`) that is maintained separately from the
full registration in :mod:`cmk.gui.main_modules`. The helper here lets
per-edition tests verify that the two paths discover the same set of REST
API endpoints, families, and link relations, so the generated spec cannot
silently drift from the live API.

The check should be removed once the spec generator and the app
share a single registration / discovery mechanism.
"""

import pytest

from cmk.ccc.version import Edition
from cmk.gui.openapi import (
    endpoint_family_registry,
    endpoint_registry,
    versioned_endpoint_registry,
)
from cmk.gui.openapi.spec import editions

VersionedKey = tuple[str, str, str, str]
LegacyKey = tuple[str, str, str]


def _versioned_keys() -> set[VersionedKey]:
    return {
        (
            endpoint.family.name,
            endpoint.metadata.link_relation,
            endpoint.metadata.method,
            endpoint.metadata.path,
        )
        for endpoint in versioned_endpoint_registry
    }


def _legacy_keys() -> set[LegacyKey]:
    return {
        (endpoint.method, endpoint.path, endpoint.operation_id) for endpoint in endpoint_registry
    }


def _family_keys() -> set[str]:
    return {family.name for family in endpoint_family_registry.get_all()}


def assert_slim_registration_matches_app(
    edition: Edition,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_versioned = _versioned_keys()
    app_legacy = _legacy_keys()
    app_families = _family_keys()

    assert app_versioned, "app registration left versioned registry empty"
    assert app_families, "app registration left family registry empty"

    monkeypatch.setattr(versioned_endpoint_registry, "_versions", {})
    monkeypatch.setattr(endpoint_registry, "_endpoints", {})
    monkeypatch.setattr(endpoint_registry, "_endpoint_list", [])
    monkeypatch.setattr(endpoint_family_registry, "_families", {})

    editions.register(edition)

    slim_versioned = _versioned_keys()
    slim_legacy = _legacy_keys()
    slim_families = _family_keys()

    assert slim_versioned == app_versioned, (
        f"Slim spec-generator registration for edition {edition.long!r} is out of "
        f"sync with the app registration for versioned endpoints. "
        f"Missing from slim: {sorted(app_versioned - slim_versioned)}. "
        f"Extra in slim: {sorted(slim_versioned - app_versioned)}."
    )
    assert slim_legacy == app_legacy, (
        f"Slim spec-generator registration for edition {edition.long!r} is out of "
        f"sync with the app registration for legacy endpoints. "
        f"Missing from slim: {sorted(app_legacy - slim_legacy)}. "
        f"Extra in slim: {sorted(slim_legacy - app_legacy)}."
    )
    assert slim_families == app_families, (
        f"Slim spec-generator registration for edition {edition.long!r} is out of "
        f"sync with the app registration for endpoint families. "
        f"Missing from slim: {sorted(app_families - slim_families)}. "
        f"Extra in slim: {sorted(slim_families - app_families)}."
    )
