#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# A ``Dictionary``'s elements are heterogeneous, so ``DictElement[Any]`` is the
# only shape that types them together (as in cmk.gui.wato._notification_parameter).
# mypy: disable-error-code="explicit-any"
"""FormSpecs for the Maps default-value global settings.

Two cohesive ``Dictionary`` globals (``maps_map_defaults`` / ``maps_object_defaults``),
registered as config variables in :mod:`cmk.maps.gui._config_variables`:

- :func:`map_defaults_spec` — defaults pre-selected when creating a new map
  (connection, map type, rendering style, tile URL).
- :func:`object_defaults_spec` — default appearance of new objects (view type,
  icon size, line style, link target, labels, templates).

The backend log level and state refresh interval are separate scalar globals.
"""

from collections.abc import Sequence
from typing import Any

from cmk.gui.form_specs.unstable.legacy_valuespec import LegacyValueSpec
from cmk.gui.i18n import _
from cmk.gui.valuespec import Color
from cmk.maps.gui.form_specs import LINE_STYLES
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    InputHint,
    Integer,
    MultilineText,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import NumberInRange


def _default_connection_element(
    connection_choices: Sequence[tuple[str, str]],
) -> DictElement[Any]:
    """Render Connection as SingleChoice over actual connections.

    A free-text String let a typo silently break every newly created map's
    state lookup. Empty list → keep field disabled with a helpful message
    that nudges the operator toward the Connections page first.
    """
    if connection_choices:
        return DictElement(
            required=True,
            parameter_form=SingleChoice(
                title=Title("Connection"),
                help_text=Help("Pre-selected when creating a new map."),
                elements=[
                    SingleChoiceElement(
                        name=cid,
                        title=Title(label or cid),  # astrein: disable=localization-checker
                    )
                    for cid, label in connection_choices
                ],
                prefill=DefaultValue(connection_choices[0][0]),
            ),
        )
    return DictElement(
        required=True,
        parameter_form=String(
            title=Title("Connection"),
            help_text=Help(
                "No connections configured yet. Open Administration → Connections "
                "and add one — then come back here to set it as the default."
            ),
            field_size=FieldSize.LARGE,
            # Empty means "no default connection", which is exactly what this
            # branch stands for. Without it String's InputHint prefill would
            # leave the whole variable without a saveable default, so a site
            # with no connections yet could not save Map defaults at all.
            prefill=DefaultValue(""),
        ),
    )


def map_defaults_spec(
    connection_choices: Sequence[tuple[str, str]] | None = None,
    title: Title = Title("Map defaults"),
) -> Dictionary:
    """Defaults pre-selected when creating a new map."""
    choices = tuple(connection_choices or ())
    return Dictionary(
        title=title,
        help_text=Help(
            "Default values applied when creating a new map. Per-map overrides take precedence."
        ),
        elements={
            "default_backend_id": _default_connection_element(choices),
            # CascadingSingleChoice so the "Default tile URL" only appears when
            # "Geo map" is selected (it is meaningless for the other types).
            # Full set of map types, mirroring the SPA's New-map modal
            # (cmk-frontend-vue maps/utils/dropdownOptions.ts).
            "default_map_type": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Map type"),
                    help_text=Help("Pre-selected map type in the 'Add map' modal."),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="static",
                            title=Title("Static map"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="worldmap",
                            title=Title("Geo map"),
                            parameter_form=Dictionary(
                                elements={
                                    "tile_url": DictElement(
                                        parameter_form=String(
                                            title=Title("Tile server URL"),
                                            help_text=Help(
                                                "Map-tile server applied to new Geo maps. Use "
                                                "the OSM-style template syntax with {z}/{x}/{y}. "
                                                "This is also the only non-OpenStreetMap server "
                                                "browsers are allowed to load tiles from: a map "
                                                "pointing anywhere else stays empty, because the "
                                                "page's content security policy blocks the "
                                                "request. Leave unset to use OpenStreetMap."
                                            ),
                                            prefill=InputHint(
                                                "https://{s}.basemaps.cartocdn.com/"
                                                "dark_all/{z}/{x}/{y}.png"
                                            ),
                                            field_size=FieldSize.LARGE,
                                        ),
                                    ),
                                },
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="flow",
                            title=Title("Flow map"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="radar",
                            title=Title("Radar (dynamic filter)"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="foldertree",
                            title=Title("Folder tree"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="presentation",
                            title=Title("Presentation"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    prefill=DefaultValue("static"),
                ),
            ),
            "default_render_mode": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Rendering style"),
                    help_text=Help(
                        "Pre-selected rendering style for new maps. NagVis-classic "
                        "anchors objects top-left with flat textboxes on a light "
                        "canvas; imported NagVis maps switch to it automatically "
                        "regardless of this default."
                    ),
                    elements=[
                        SingleChoiceElement(name="default", title=Title("Maps (default)")),
                        SingleChoiceElement(name="nagvis_classic", title=Title("NagVis-classic")),
                    ],
                    prefill=DefaultValue("default"),
                ),
            ),
        },
    )


def object_defaults_spec(title: Title = Title("Object defaults")) -> Dictionary:
    """Default appearance applied to new objects placed on a map."""
    return Dictionary(
        title=title,
        help_text=Help(
            "Default appearance applied to new objects. Per-object overrides take precedence."
        ),
        elements={
            # ── Appearance ──
            "view_type": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("View type"),
                    help_text=Help("How objects are rendered on a map."),
                    elements=[
                        SingleChoiceElement(name="icon", title=Title("Icon")),
                        SingleChoiceElement(name="text", title=Title("Text only")),
                        SingleChoiceElement(name="gadget", title=Title("Gadget")),
                    ],
                    prefill=DefaultValue("icon"),
                ),
            ),
            "icon_size": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Icon size"),
                    help_text=Help("Default pixel size for object icons on a map."),
                    unit_symbol="px",
                    prefill=DefaultValue(30),
                    custom_validate=(NumberInRange(min_value=8, max_value=256),),
                ),
            ),
            # Elements come from cmk.maps.backend.object_options.LINE_STYLES — the
            # canonical name+title list also served by the registry endpoint.
            # The per-object EditPanel hits that same endpoint at boot, so the
            # two surfaces can never drift again.
            "line_style": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Line style"),
                    help_text=Help(
                        "Default stroke style for new objects of type 'line'. "
                        "Has no effect on icons, text or gadgets."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name=name,
                            title=Title(title),  # astrein: disable=localization-checker
                        )
                        for name, title in LINE_STYLES
                    ],
                    prefill=DefaultValue("plain"),
                ),
            ),
            "url_target": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Link target"),
                    help_text=Help("Where object links open."),
                    elements=[
                        SingleChoiceElement(name="_blank", title=Title("New tab")),
                        SingleChoiceElement(name="_self", title=Title("Same tab")),
                    ],
                    prefill=DefaultValue("_blank"),
                ),
            ),
            # "Stacking order (Z)" is deliberately not offered here: the
            # per-object EditPanel exposes it where the few maps that need
            # explicit layering can set it.
            # ── Object defaults / Labels ──
            # ``settings_forms.form_to_global`` flattens this nested shape onto
            # the ``label_*`` keys every map renderer uses. The hidden branch
            # carries no payload, so size/colour are per-branch state and revert
            # to the factory defaults when labels are switched back on.
            "labels": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Labels"),
                    help_text=Help("Caption text shown next to icons."),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="hidden",
                            title=Title("Don't display labels"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="shown",
                            title=Title("Display labels"),
                            parameter_form=Dictionary(
                                elements={
                                    "size": DictElement(
                                        required=True,
                                        parameter_form=Integer(
                                            title=Title("Size"),
                                            unit_symbol="px",
                                            prefill=DefaultValue(11),
                                        ),
                                    ),
                                    # The legacy ``Color`` ValueSpec is the real
                                    # Checkmk colour picker; it stores a plain
                                    # ``#rrggbb``, so the runtime schema is
                                    # unchanged. Optional, like the IconSelector
                                    # of user_icons_and_actions: that keeps the
                                    # legacy element out of the variable's default
                                    # value, which the GUI-save round trip cannot
                                    # render and parse back.
                                    "color": DictElement(
                                        parameter_form=LegacyValueSpec.wrap(
                                            Color(title=_("Color"), default_value="#ffffff")
                                        ),
                                    ),
                                    # Transparent (no box behind the label) or a
                                    # solid colour via the picker. Stored as a
                                    # cascade tuple ``("transparent", None)`` /
                                    # ``("color", "#rrggbb")``; the daemon flattens
                                    # it to the ``label_background`` string.
                                    # Optional for the same reason as ``color``.
                                    "background": DictElement(
                                        parameter_form=CascadingSingleChoice(
                                            title=Title("Background"),
                                            elements=[
                                                CascadingSingleChoiceElement(
                                                    name="transparent",
                                                    title=Title("Transparent"),
                                                    parameter_form=FixedValue(value=None),
                                                ),
                                                CascadingSingleChoiceElement(
                                                    name="color",
                                                    title=Title("Solid colour"),
                                                    parameter_form=LegacyValueSpec.wrap(
                                                        Color(
                                                            title=_("Background colour"),
                                                            default_value="#000000",
                                                        )
                                                    ),
                                                ),
                                            ],
                                            prefill=DefaultValue("transparent"),
                                        ),
                                    ),
                                },
                            ),
                        ),
                    ],
                    prefill=DefaultValue("shown"),
                ),
            ),
            # ── Object defaults / Templates ──
            # MultilineText (not String) because realistic templates run
            # several lines — HTML markup, multiple placeholders, leading
            # newline for layout. A single-line field forces operators to
            # type unreadable one-liners.
            "hover_template": DictElement(
                parameter_form=MultilineText(
                    title=Title("Hover template"),
                    help_text=Help("Shown on hover when a map has no template of its own."),
                    prefill=InputHint("e.g. {{name}} is {{state}}"),
                ),
            ),
            "context_template": DictElement(
                parameter_form=MultilineText(
                    title=Title("Context-menu template"),
                    help_text=Help(
                        "Right-click fallback. Same placeholders as the hover template."
                    ),
                    prefill=InputHint("e.g. {{name}} is {{state}}"),
                ),
            ),
        },
    )
