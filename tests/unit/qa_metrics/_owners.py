#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Fixture checkouts' component definitions, in the layout ``cwz`` reads.

Shared so a change of that layout is one edit, not one per test module.
"""

from pathlib import Path


def define_component(root: Path, component_id: str) -> None:
    """Define ``component_id`` in the checkout at ``root``; a no-op if already defined."""
    definition = root / "component_owners" / component_id
    definition.mkdir(parents=True, exist_ok=True)
    (definition / "OWNERS_DEFINITION").write_text("owner@example.com\n")
    (definition / "component_info.toml").write_text(
        'type = "Component"\ndescription = ""\nmembers_required = 1\n'
    )
