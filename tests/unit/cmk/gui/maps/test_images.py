#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for the GUI-owned image/background helpers (``cmk.maps.gui._images``)."""

import re
import threading
from pathlib import Path

import pytest

import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.user import UserId
from cmk.gui.exceptions import MKUserError
from cmk.maps.gui import _images
from cmk.maps.gui.store import save_map, user_maps_path

_PNG = b"\x89PNG\r\n\x1a\n"


def _backgrounds() -> Path:
    return cmk.utils.paths.omd_root / "var/maps/backgrounds"


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
        _images._editable_map("net*")  # noqa: SLF001


def test_a_background_that_lost_its_file_keeps_its_name() -> None:
    ref = _images._bg_stem("alice", "net") + ".gone.png"  # noqa: SLF001

    assert _images.rotate_background("alice", "net", ref) == ref


def test_a_background_is_stored_only_once_the_owners_maps_are_unlocked() -> None:
    stored: list[str] = []
    storing = threading.Thread(
        target=lambda: stored.append(
            _images.store_background("alice", "floor", ".png", b"\x89PNG\r\n\x1a\n", saved=None)
        )
    )

    with store.locked(user_maps_path(UserId("alice"))):
        storing.start()
        storing.join(timeout=0.2)
        held_up = not stored
    storing.join()

    assert held_up
    assert stored


def test_the_backgrounds_of_a_user_without_profile_are_removed(tmp_path: Path) -> None:
    kept = _images.store_background("alice", "floor", ".png", _PNG, saved=None)
    removed = _images.store_background("bob", "floor", ".png", _PNG, saved=None)
    (tmp_path / "alice").mkdir()

    _images.remove_backgrounds_of_removed_users(tmp_path, _backgrounds())

    assert (_backgrounds() / kept).exists()
    assert not (_backgrounds() / removed).exists()


def test_no_background_is_removed_while_no_profile_is_found(tmp_path: Path) -> None:
    stored = _images.store_background("bob", "floor", ".png", _PNG, saved=None)

    _images.remove_backgrounds_of_removed_users(tmp_path, _backgrounds())

    assert (_backgrounds() / stored).exists()


def test_the_background_cleanup_passes_a_site_without_backgrounds(tmp_path: Path) -> None:
    (tmp_path / "alice").mkdir()

    _images.remove_backgrounds_of_removed_users(tmp_path, tmp_path / "backgrounds")


def test_a_file_stored_for_no_map_is_left_by_the_background_cleanup(tmp_path: Path) -> None:
    (tmp_path / "alice").mkdir()
    _backgrounds().mkdir(parents=True, exist_ok=True)
    (_backgrounds() / "plan.png").write_bytes(_PNG)

    _images.remove_backgrounds_of_removed_users(tmp_path, _backgrounds())

    assert (_backgrounds() / "plan.png").exists()
