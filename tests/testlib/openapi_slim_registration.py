#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared scaffold for tests that exercise the OpenAPI slim registration path."""

import pytest

from cmk.ccc.version import Edition
from cmk.gui.openapi import (
    endpoint_family_registry,
    endpoint_registry,
    versioned_endpoint_registry,
)
from cmk.gui.openapi.spec import editions


def register_edition_into_empty_registries(
    edition: Edition,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty the OpenAPI registries and register ``edition`` via the slim path.

    ``monkeypatch`` swaps the registries' backing containers for empty ones and
    restores the originals at test teardown, so the ambient (app-registered)
    registries are left untouched for other tests in the session.
    """
    monkeypatch.setattr(versioned_endpoint_registry, "_versions", {})
    monkeypatch.setattr(endpoint_registry, "_endpoints", {})
    monkeypatch.setattr(endpoint_registry, "_endpoint_list", [])
    monkeypatch.setattr(endpoint_family_registry, "_families", {})

    editions.register(edition)
