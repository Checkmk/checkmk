#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Presentation map schemas — a design-first, slide-style map type.

The presentation map deliberately departs from the static map's
config-/binding-first model. Instead of a flat ``list[MapElement]`` whose
entry point is a monitoring binding, it holds a discriminated union of design
*elements* (shapes, text, images) plus a data-bound element whose monitoring
binding is a secondary attribute, not the way in.

Elements live inside the view (``PresentationView.elements``) rather than in
``MapConfig.objects`` so the whole slide saves atomically through the existing
``PUT /{name}`` + ``If-Match`` optimistic locking — a natural fit for the
editor's snapshot-based undo/redo. Coordinates are absolute pixels on a fixed
slide stage (``width × height``), not the static map's percentages.

Kept self-contained on purpose: the module imports nothing from ``map.py`` so
``map.py`` can import ``PresentationView`` for its view union without a cycle,
and so the whole feature reverts cleanly as one unit.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from cmk.maps.shared.map_payload import (
    PresentationObjectType,
    PresentationTheme,
)
from cmk.maps.shared.validators import validate_color, validate_user_url

# font-family reaches an inline style on the frontend; keep CSS-breaking
# characters (;{}()<>/:) out so it can't escape the property like the color
# fields are guarded against.
_FONT_RE = re.compile(r"^[a-zA-Z0-9 ,_'\"\-.]{1,128}$")


def _validate_font_family(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    s = value.strip()
    if not _FONT_RE.fullmatch(s):
        raise ValueError(f"invalid font family: {value!r}")
    return s


def _validate_image_src(value: str | None) -> str | None:
    return validate_user_url(value)


class ElementDisplay(BaseModel):
    """Render mode for a data-bound element. Wire-compatible with the static
    map's ``DisplayConfig`` so the frontend ``GadgetRenderer`` consumes both."""

    mode: Literal["icon", "text", "gadget"] = "icon"
    image: str | None = None
    image_size: int | None = None
    gadget_type: Literal["gauge", "bar", "trafficlight", "value"] | None = None
    gadget_metric: str | None = None


class ElementLabel(BaseModel):
    show: bool = True
    text: str | None = None
    size: int = 12
    # None on a color means "inherit the slide theme" — resolved in the renderer.
    color: str | None = None
    background: str | None = None
    weight: Literal["normal", "bold"] | None = None
    align: Literal["left", "right", "center"] | None = None

    @field_validator("color", "background")
    @classmethod
    def _v_color(cls, v: str | None) -> str | None:
        return validate_color(v)


class _ElementBase(BaseModel):
    # Client-generated; uniqueness enforced on PresentationView.
    id: str = Field(min_length=1)
    # Absolute slide pixels — deliberately not the static map's percentages.
    x: float = 0
    y: float = 0
    w: float = 120
    h: float = 80
    rotation: float = 0
    z: int = 0
    opacity: float = Field(default=1.0, ge=0, le=1)
    locked: bool = False
    hidden: bool = False
    name: str | None = None


class ShapeElement(_ElementBase):
    kind: Literal["shape"] = "shape"
    shape: Literal["rect", "ellipse", "line", "arrow"] = "rect"
    fill: str | None = "#3b82f6"
    stroke: str | None = None
    stroke_width: float = Field(default=1, ge=0, le=64)
    corner_radius: float = Field(default=0, ge=0)
    dash: Literal["solid", "dashed", "dotted"] = "solid"
    # Optional monitoring binding. When set, the shape colours itself by the
    # bound object's state (fill for rect/ellipse, stroke for line/arrow) and
    # can show a state label — the foundation weathermap links build on.
    connection_id: str | None = None
    # ``None`` keeps the legacy derivation (service when a service_description
    # is set, else host) so pre-existing maps stay wire-compatible.
    object_type: PresentationObjectType | None = None
    host_name: str | None = None
    service_description: str | None = None
    group_name: str | None = None
    aggregation_id: str | None = None
    # See ``DataElement.auto_host``: resolve the connection's primary host at
    # state-fetch when no explicit ``host_name`` is set (weathermap templates).
    auto_host: bool = False
    only_hard_states: bool = False
    label: ElementLabel | None = None
    # Endpoint docking (line/arrow only): the start/end follows the referenced
    # element's centre instead of the shape's own box, turning the line into a
    # connector that tracks the elements it links.
    start_ref: str | None = None
    end_ref: str | None = None
    # Weathermap flow styling: animate the connector and drive its colour /
    # width / flow speed from a utilisation metric (``flow_metric`` from the
    # bound object's perf-data; falls back to state colour when absent).
    # ``flow_metric_back`` adds the classic two-way weathermap: the connector
    # splits at its midpoint, the far half showing the return direction.
    flow: bool = False
    flow_metric: str | None = None
    flow_metric_back: str | None = None
    # Marks the shape as an intended data slot (template placeholder): the
    # editor's connect-data walkthrough counts it as unbound until a host is
    # set, while a plain decorative shape is never treated as one.
    data_slot: bool = False

    @field_validator("fill", "stroke")
    @classmethod
    def _v_color(cls, v: str | None) -> str | None:
        return validate_color(v)


class TextElement(_ElementBase):
    kind: Literal["text"] = "text"
    text: str = "Text"
    font_family: str | None = None
    font_size: float = Field(default=16, ge=4, le=512)
    font_weight: Literal["normal", "bold"] = "normal"
    font_style: Literal["normal", "italic"] = "normal"
    text_align: Literal["left", "center", "right", "justify"] = "left"
    line_height: float = Field(default=1.3, ge=0.5, le=4)
    # None means "inherit the slide theme" — resolved in the renderer.
    color: str | None = None
    background: str | None = None
    letter_spacing: float = 0

    @field_validator("color", "background")
    @classmethod
    def _v_color(cls, v: str | None) -> str | None:
        return validate_color(v)

    @field_validator("font_family")
    @classmethod
    def _v_font(cls, v: str | None) -> str | None:
        return _validate_font_family(v)


class ImageElement(_ElementBase):
    kind: Literal["image"] = "image"
    src: str | None = None
    fit: Literal["cover", "contain", "fill"] = "contain"
    alt: str | None = None

    @field_validator("src")
    @classmethod
    def _v_src(cls, v: str | None) -> str | None:
        return _validate_image_src(v)


class DataElement(_ElementBase):
    """A live-status element. The monitoring binding is optional and secondary —
    an unbound data element renders as a styled placeholder."""

    kind: Literal["data"] = "data"
    connection_id: str | None = None
    # ``None`` keeps the legacy derivation (service when a service_description
    # is set, else host) so pre-existing maps stay wire-compatible.
    object_type: PresentationObjectType | None = None
    host_name: str | None = None
    service_description: str | None = None
    group_name: str | None = None
    aggregation_id: str | None = None
    # Auto-bind to the connection's primary host (the Checkmk server itself),
    # resolved by the daemon at state-fetch time. Lets a shipped/template map
    # show live data on a fresh install without hard-coding a site's host name.
    # Ignored once ``host_name`` is set explicitly.
    auto_host: bool = False
    only_hard_states: bool = False
    display: ElementDisplay = ElementDisplay()
    label: ElementLabel | None = ElementLabel()
    fill: str | None = None
    stroke: str | None = None

    @field_validator("fill", "stroke")
    @classmethod
    def _v_color(cls, v: str | None) -> str | None:
        return validate_color(v)


class GroupElement(_ElementBase):
    """A real group. ``children`` are element ids in the same flat ``elements``
    list (flat references keep z-order, hit-testing and the layers panel simple)."""

    kind: Literal["group"] = "group"
    children: list[str] = []


PresentationElement = Annotated[
    ShapeElement | TextElement | ImageElement | DataElement | GroupElement,
    Field(discriminator="kind"),
]


class PresentationView(BaseModel):
    type: Literal["presentation"] = "presentation"
    width: int = Field(default=1920, ge=320, le=8192)
    height: int = Field(default=1080, ge=320, le=8192)
    theme: PresentationTheme = "midnight"
    background: str | None = None
    # Optional slide background image (image-store filename or external URL),
    # layered over ``background`` / the theme default by the renderer. Same
    # scheme guard as ImageElement.src so it can't carry a data:/js: payload.
    background_image: str | None = None
    elements: list[PresentationElement] = []
    problems_only: bool = False

    @field_validator("background")
    @classmethod
    def _v_bg(cls, v: str | None) -> str | None:
        return validate_color(v)

    @field_validator("background_image")
    @classmethod
    def _v_bg_image(cls, v: str | None) -> str | None:
        return _validate_image_src(v)

    @model_validator(mode="after")
    def _unique_ids(self) -> PresentationView:
        seen: set[str] = set()
        for el in self.elements:
            if el.id in seen:
                raise ValueError(f"duplicate element id: {el.id!r}")
            seen.add(el.id)
        return self
