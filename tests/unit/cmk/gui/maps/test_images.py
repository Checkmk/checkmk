#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for the GUI-owned image/background helpers (``cmk.maps.gui._images``)."""

import re
from types import SimpleNamespace

import pytest

from cmk.ccc.user import UserId
from cmk.gui.exceptions import MKUserError
from cmk.maps.gui import _images
from cmk.maps.gui.store import save_map


def test_bg_stem_is_owner_scoped_and_path_safe() -> None:
    # The owner is folded in (so two users' same-named maps never collide) and
    # hashed, so nothing user-controlled reaches the path.
    stem = _images._bg_stem("alice", "net")  # noqa: SLF001
    assert stem.endswith("__net")
    assert re.fullmatch(r"[0-9a-f]{16}__net", stem)
    # A path-ish owner cannot escape the directory either.
    assert re.fullmatch(r"[0-9a-f]{16}__net", _images._bg_stem("a/../b", "net"))  # noqa: SLF001


@pytest.mark.parametrize(
    "left, right",
    [
        # Sanitising the owner is not injective, hashing it is: these two users
        # would otherwise share a stem.
        pytest.param(("a.b", "net"), ("a_b", "net"), id="owner-sanitisation"),
        # ``__`` is legal in a map name, so the separator alone did not delimit.
        pytest.param(("a", "b__c"), ("a__b", "c"), id="separator-in-name"),
    ],
)
def test_bg_stem_never_collides_across_owners(
    left: tuple[str, str], right: tuple[str, str]
) -> None:
    # A shared stem means one map's background upload unlinks another map's file
    # (the upload globs ``{stem}.*``), leaving a dangling background_image.
    assert _images._bg_stem(*left) != _images._bg_stem(*right)  # noqa: SLF001


def test_builtin_names_include_a_shipped_icon() -> None:
    # The built-in icons ship with the package; the name set is the authority for
    # protecting them from overwrite/delete.
    names = _images._builtin_names()  # noqa: SLF001
    assert "bell.svg" in names
    assert _images._is_builtin("bell.svg")  # noqa: SLF001
    assert not _images._is_builtin("user-upload.png")  # noqa: SLF001


def test_find_image_usage_reports_object_and_background_refs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = [
        SimpleNamespace(
            config=SimpleNamespace(
                name="map-a",
                map_spec={
                    "alias": "Map A",
                    "objects": [
                        {"id": "o1", "image_src": "icon.svg"},
                        {"id": "o2", "display": {"image": "icon.svg"}},
                        {"id": "o3", "image_src": "other.svg"},
                    ],
                    "background_image": "bg.png",
                },
            )
        ),
        SimpleNamespace(
            config=SimpleNamespace(
                name="map-b",
                map_spec={"alias": None, "objects": [], "background_image": "icon.svg"},
            )
        ),
    ]
    monkeypatch.setattr(_images, "get_permitted_maps", lambda: pages)

    usage = _images.find_image_usage("icon.svg")

    by_map = {entry.map_name: entry for entry in usage}
    assert set(by_map) == {"map-a", "map-b"}
    assert by_map["map-a"].object_ids == ["o1", "o2"]
    assert by_map["map-a"].is_background is False
    assert by_map["map-a"].alias == "Map A"
    assert by_map["map-b"].is_background is True


def test_find_image_usage_skips_unrelated_maps(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = [
        SimpleNamespace(
            config=SimpleNamespace(
                name="map-a",
                map_spec={"objects": [{"id": "o1", "image_src": "other.svg"}]},
            )
        ),
    ]
    monkeypatch.setattr(_images, "get_permitted_maps", lambda: pages)
    assert _images.find_image_usage("icon.svg") == []


def test_background_paths_refuse_a_map_name_the_stem_cannot_carry(
    request_context: None,  # noqa: ARG001
    with_admin_login: UserId,
) -> None:
    """A stored name with a glob metacharacter must not reach ``_bg_stem``.

    Both background paths glob ``{stem}.*``, so such a name would let one map's
    upload or delete unlink another map's background and leave it with a dangling
    ``background_image``. The REST create path validates names, but nothing stops
    a hand-edited or migrated store from holding one, so the guard sits on the
    resolve both paths go through.
    """
    save_map(
        with_admin_login,
        "net*",
        {
            "name": "net*",
            "alias": "Glob",
            "connection_id": "cmk_heute",
            "objects": [],
            "view": {"type": "flow"},
        },
        public=False,
    )

    with pytest.raises(MKUserError, match="Invalid map name"):
        _images._editable_map_owner("net*")  # noqa: SLF001
