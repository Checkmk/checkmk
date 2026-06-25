#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pin the GUI-side wire types against the daemon's authoritative map model.

``cmk.maps.shared.map_payload`` spells out the flat map shape so GUI-side
producers (the NagVis ``.cfg`` importer, the built-in maps) can build a map with
real types instead of ``dict[str, object]``. It is a hand-written subset of what
the daemon validates, so without these tests a rename on either side would only
surface as a map the daemon rejects at runtime.

Pinned here: key names, which keys are mandatory, and the ``Literal`` domain of
every key that has one. Value types and numeric constraints are not.
"""

from __future__ import annotations

import types
import typing

import pytest
from pydantic import BaseModel

from cmk.maps.backend.schemas import map as daemon
from cmk.maps.backend.schemas import presentation as daemon_presentation
from cmk.maps.shared import map_payload as wire

_TYPED_DICT_TO_MODEL: list[tuple[type, type[BaseModel]]] = [
    (wire.MapPayload, daemon.MapConfig),
    (wire.MapObject, daemon.MapElement),
    (wire.MapLabel, daemon.LabelConfig),
    (wire.MapDisplay, daemon.DisplayConfig),
    (wire.StaticView, daemon.StaticView),
    (wire.WorldmapView, daemon.WorldmapView),
    (wire.RadarView, daemon.RadarView),
    (wire.FlowView, daemon.FlowView),
    (wire.FolderTreeView, daemon.FolderTreeView),
    (wire.PresentationView, daemon_presentation.PresentationView),
    (wire.TextElement, daemon_presentation.TextElement),
    (wire.DataElement, daemon_presentation.DataElement),
    (wire.ElementDisplay, daemon_presentation.ElementDisplay),
    (wire.ElementLabel, daemon_presentation.ElementLabel),
]


def _literal_values(annotation: object) -> set[object]:
    """Collect an annotation's Literal members, through the wrappers it may carry."""
    origin = typing.get_origin(annotation)
    if origin is typing.Literal:
        return set(typing.get_args(annotation))
    if origin in (types.UnionType, typing.Union, typing.Annotated, typing.NotRequired):
        return {v for arg in typing.get_args(annotation) for v in _literal_values(arg)}
    return set()


def _wire_keys(typed_dict: type) -> set[str]:
    return set(typed_dict.__required_keys__) | set(typed_dict.__optional_keys__)  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "typed_dict, model", _TYPED_DICT_TO_MODEL, ids=lambda p: getattr(p, "__name__", "")
)
def test_every_wire_key_exists_on_the_daemon_model(
    typed_dict: type, model: type[BaseModel]
) -> None:
    assert not _wire_keys(typed_dict) - set(model.model_fields)


@pytest.mark.parametrize(
    "typed_dict, model", _TYPED_DICT_TO_MODEL, ids=lambda p: getattr(p, "__name__", "")
)
def test_keys_the_daemon_requires_are_required_here(
    typed_dict: type, model: type[BaseModel]
) -> None:
    """A key the daemon has no default for must be present, and mandatory, here.

    Both directions matter: a daemon field gaining a required status the wire
    type spells as optional, and one added to the daemon that the wire type does
    not know about at all — producers would omit it and the daemon would 422.
    """
    mandatory = {name for name, f in model.model_fields.items() if f.is_required()}
    assert mandatory <= typed_dict.__required_keys__  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "typed_dict, model", _TYPED_DICT_TO_MODEL, ids=lambda p: getattr(p, "__name__", "")
)
def test_literal_domains_match_the_daemon(typed_dict: type, model: type[BaseModel]) -> None:
    """Every wire key spelled as a Literal must offer the daemon's exact choices.

    Walks the keys rather than a hand-kept list, so an inline Literal — the view
    discriminators, ``graph_embed_type``, ``kind`` — cannot escape the pin.
    """
    hints = typing.get_type_hints(typed_dict, include_extras=True)
    compared = {
        key: (_literal_values(hint), _literal_values(model.model_fields[key].annotation))
        for key, hint in hints.items()
        if _literal_values(hint)
    }
    assert compared, f"{typed_dict.__name__} declares no Literal — drop it from this test"
    assert {key: wire_values for key, (wire_values, _daemon) in compared.items()} == {
        key: daemon_values for key, (_wire, daemon_values) in compared.items()
    }


def test_view_types_cover_every_daemon_view() -> None:
    """``MapViewType`` must name exactly the discriminators the daemon accepts."""
    daemon_views = typing.get_args(typing.get_args(daemon.MapView)[0])
    discriminators = {
        v for view in daemon_views for v in _literal_values(view.model_fields["type"].annotation)
    }
    assert discriminators
    assert _literal_values(wire.MapViewType) == discriminators


def test_every_wire_typed_dict_is_pinned() -> None:
    """No TypedDict may be added to the wire module without landing in the table."""
    declared = {
        obj
        for name, obj in vars(wire).items()
        if not name.startswith("_") and hasattr(obj, "__required_keys__")
    }
    assert not declared - {typed_dict for typed_dict, _model in _TYPED_DICT_TO_MODEL}
