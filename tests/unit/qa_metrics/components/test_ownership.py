#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from tests.qa_metrics.components import (
    ComponentOwnership,
    OwnershipUnavailableError,
    UnknownComponentError,
)
from tests.qa_metrics.components._ownership import _assert_usable, _owner_ids


def _ownership() -> ComponentOwnership:
    """Ownership as ``load_ownership`` would return it, without touching Gerrit.

    ``cmk/shared.py`` is co-owned and ``cmk/orphan.py`` unowned, the two cases
    that make per-component file sets not add up to the whole.
    """
    return ComponentOwnership(
        owners_by_path={
            Path("cmk/gui/wato/one.py"): ["ui_setup"],
            Path("cmk/bi/two.py"): ["business_intelligence"],
            Path("cmk/shared.py"): ["business_intelligence", "ui_setup"],
            Path("cmk/orphan.py"): [],
        },
        component_ids=frozenset({"business_intelligence", "ui_setup", "owns_nothing_here"}),
    )


def test_owner_ids_of_unowned_path_is_empty() -> None:
    assert _owner_ids(None) == []


def test_owner_ids_of_single_owner() -> None:
    assert _owner_ids("ui_setup") == ["ui_setup"]


def test_owner_ids_splits_joined_owners() -> None:
    assert _owner_ids("business_intelligence, ui_setup") == [
        "business_intelligence",
        "ui_setup",
    ]


def test_owners_of_known_path() -> None:
    assert _ownership().owners_of(Path("cmk/bi/two.py")) == ["business_intelligence"]


def test_owners_of_unresolved_path_is_empty() -> None:
    assert _ownership().owners_of(Path("cmk/never/resolved.py")) == []


def test_paths_owned_by_is_sorted() -> None:
    assert _ownership().paths_owned_by("ui_setup") == [
        Path("cmk/gui/wato/one.py"),
        Path("cmk/shared.py"),
    ]


def test_paths_owned_by_counts_co_owned_path_for_every_owner() -> None:
    ownership = _ownership()
    assert Path("cmk/shared.py") in ownership.paths_owned_by("ui_setup")
    assert Path("cmk/shared.py") in ownership.paths_owned_by("business_intelligence")


def test_paths_owned_by_excludes_unowned_path() -> None:
    ownership = _ownership()
    assert not any(
        Path("cmk/orphan.py") in ownership.paths_owned_by(component)
        for component in ownership.component_ids
    )


def test_paths_owned_by_known_component_without_files_is_empty() -> None:
    assert _ownership().paths_owned_by("owns_nothing_here") == []


def test_paths_owned_by_unknown_component_raises() -> None:
    with pytest.raises(UnknownComponentError):
        _ownership().paths_owned_by("no_such_component")


def test_unknown_component_error_suggests_close_match() -> None:
    with pytest.raises(UnknownComponentError, match="Did you mean.*ui_setup"):
        _ownership().paths_owned_by("ui_setups")


def test_assert_usable_accepts_components_with_rules() -> None:
    _assert_usable(component_count=1, rule_count=1)


def test_assert_usable_rejects_ownership_without_any_component() -> None:
    with pytest.raises(OwnershipUnavailableError, match="no component at all"):
        _assert_usable(component_count=0, rule_count=0)


def test_assert_usable_rejects_components_without_any_rule() -> None:
    with pytest.raises(OwnershipUnavailableError, match="not one OWNERS rule"):
        _assert_usable(component_count=2, rule_count=0)
