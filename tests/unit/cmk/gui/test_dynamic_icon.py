#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.dynamic_icon import resolve_icon_name
from cmk.shared_typing import icon as st


class _ThemeStub:
    def detect_icon_path(self, icon_name: str, prefix: str) -> str:
        return f"themes/facelift/images/{prefix}{icon_name}.png"


def test_resolve_icon_name_with_none_icon_returns_missing() -> None:
    resolved = resolve_icon_name(None, _ThemeStub())  # type: ignore[arg-type]

    assert resolved == st.DefaultIcon(id="missing")


def test_resolve_icon_name_with_none_icon_in_dict_returns_missing_with_emblem() -> None:
    resolved = resolve_icon_name(
        {"icon": None, "emblem": "warning"},  # type: ignore[arg-type]
        _ThemeStub(),  # type: ignore[arg-type]
    )

    assert resolved == st.EmblemIcon(icon=st.DefaultIcon(id="missing"), emblem="warning")


@pytest.mark.parametrize(
    "icon_payload",
    [
        123,  # integer instead of string
        [],  # list instead of string
        {},  # empty dict instead of string
        "",  # empty string
    ],
)
def test_resolve_icon_name_with_invalid_icon_type_returns_missing(
    icon_payload: object,
) -> None:
    resolved = resolve_icon_name(icon_payload, _ThemeStub())  # type: ignore[arg-type]

    assert resolved == st.DefaultIcon(id="missing")


def test_resolve_icon_name_with_invalid_emblem_type_ignores_emblem() -> None:
    resolved = resolve_icon_name(
        {"icon": "status", "emblem": 123},  # type: ignore[arg-type]  # integer emblem
        _ThemeStub(),  # type: ignore[arg-type]
    )

    # Should render icon normally without emblem wrapper since emblem type is invalid
    assert isinstance(resolved, st.DefaultIcon)
    assert resolved.id == "status"


def test_resolve_icon_name_with_none_emblem_ignores_emblem() -> None:
    resolved = resolve_icon_name(
        {"icon": "status", "emblem": None},  # type: ignore[arg-type]
        _ThemeStub(),  # type: ignore[arg-type]
    )

    # emblem=None is the valid "no emblem" value (DynamicIconWithEmblem allows
    # str | None), so the plain icon renders without an emblem wrapper.
    assert isinstance(resolved, st.DefaultIcon)
    assert resolved.id == "status"
