#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""FormSpec for the metadata subset of a map.

Covers the fields the Pilot vendor renders cleanly: alias, connection,
icon-size override, rotation, templates, click action and visibility.

Type-specific view geometry (worldmap lat/lng/zoom, flow root, radar
filter) plus background image stay in the existing custom Vue surface
because they need live previews / pickers FormSpec doesn't ship.
"""

from collections.abc import Sequence

from cmk.maps.gui.form_specs import MapsDictGroup
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    InputHint,
    Integer,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import NumberInRange

_IDENTIFICATION = MapsDictGroup(
    title=Title("Identification"),
    help_text=Help("Display name and the monitoring connection this map pulls data from."),
)
_BEHAVIOR = MapsDictGroup(
    title=Title("Behavior"),
    help_text=Help("How the map appears in the rotation and reacts to clicks."),
)
_DISPLAY = MapsDictGroup(
    title=Title("Display defaults"),
    help_text=Help("Per-map overrides of the global object defaults."),
)
_TEMPLATES = MapsDictGroup(
    title=Title("Templates"),
    help_text=Help(
        "Per-map overrides for the global hover / context-menu fallback. "
        "Placeholders: {{name}}, {{state}}, {{output}}, {{host}}, {{service}}."
    ),
)


def _connection_form(
    choices: Sequence[tuple[str, str]] | None,
) -> SingleChoice | String:
    # Empty list keeps the form editable on fresh installs that have no
    # connections registered yet — falls back to free-text so the operator
    # can still type the ID they're about to create.
    if not choices:
        return String(
            title=Title("Connection"),
            help_text=Help(
                "Connection ID this map pulls monitoring data from. "
                "Individual objects can override this."
            ),
            prefill=InputHint("live_1"),
            field_size=FieldSize.LARGE,
        )
    return SingleChoice(
        title=Title("Connection"),
        help_text=Help(
            "Monitoring connection this map pulls data from. Individual objects can override this."
        ),
        elements=[
            SingleChoiceElement(
                name=cid,
                title=Title(label or cid),  # astrein: disable=localization-checker
            )
            for cid, label in choices
        ],
    )


def map_metadata_spec(
    connection_choices: Sequence[tuple[str, str]] | None = None,
) -> Dictionary:
    return Dictionary(
        title=Title("Map settings"),
        help_text=Help(
            "Metadata that applies to the whole map. Type-specific "
            "view geometry and the background image stay in the custom "
            "editor."
        ),
        elements={
            "alias": DictElement(
                required=True,
                group=_IDENTIFICATION,
                parameter_form=String(
                    title=Title("Display name"),
                    help_text=Help(
                        "Shown on map cards and in the header. Leave blank to "
                        "fall back to the technical name."
                    ),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "connection_id": DictElement(
                required=True,
                group=_IDENTIFICATION,
                parameter_form=_connection_form(connection_choices),
            ),
            "icon_size": DictElement(
                group=_DISPLAY,
                parameter_form=Integer(
                    title=Title("Icon size override"),
                    help_text=Help(
                        "Leave the field disabled to inherit the global Icon "
                        "defaults. Individual objects on the map can still "
                        "override this."
                    ),
                    unit_symbol="px",
                    prefill=DefaultValue(30),
                ),
            ),
            "default_z": DictElement(
                required=True,
                group=_DISPLAY,
                parameter_form=Integer(
                    title=Title("Default layer (z)"),
                    help_text=Help(
                        "Layer for objects that have no explicit z value. Higher "
                        "numbers render on top. Lets unset objects share a sensible "
                        "layer instead of all collapsing into the background."
                    ),
                    prefill=DefaultValue(1),
                    custom_validate=(NumberInRange(min_value=0),),
                ),
            ),
            "render_mode": DictElement(
                required=True,
                group=_DISPLAY,
                parameter_form=SingleChoice(
                    title=Title("Rendering style"),
                    help_text=Help(
                        "Maps renders objects centered on their coordinates "
                        "with the modern glass look. NagVis-classic anchors "
                        "objects top-left, draws flat textboxes on a light "
                        "canvas and is auto-selected when importing a legacy "
                        "NagVis .cfg map for a 1:1 result."
                    ),
                    elements=[
                        SingleChoiceElement(name="default", title=Title("Maps (default)")),
                        SingleChoiceElement(name="nagvis_classic", title=Title("NagVis-classic")),
                    ],
                    prefill=DefaultValue("default"),
                ),
            ),
            "rotation_interval": DictElement(
                required=True,
                group=_BEHAVIOR,
                # Modeled as CascadingSingleChoice so "off" is an explicit
                # branch instead of the magic value 0; the API endpoint
                # (and the host modal) flattens it back to the on-wire int.
                parameter_form=CascadingSingleChoice(
                    title=Title("Auto-rotate"),
                    help_text=Help(
                        "Show the next map in the rotation after the chosen "
                        "interval. Pick Off to keep this map open until the "
                        "operator switches manually. Rotation order follows "
                        "the maps list; only maps with auto-rotate enabled "
                        "participate."
                    ),
                    prefill=DefaultValue("off"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="off",
                            title=Title("Off"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="every",
                            title=Title("Every N seconds"),
                            parameter_form=Integer(
                                title=Title("Interval"),
                                unit_symbol="s",
                                prefill=DefaultValue(30),
                                custom_validate=(NumberInRange(min_value=1),),
                            ),
                        ),
                    ],
                ),
            ),
            "click_action": DictElement(
                required=True,
                group=_BEHAVIOR,
                parameter_form=BooleanChoice(
                    title=Title("Interactive"),
                    label=Label("Clicks open object details or follow links"),
                    help_text=Help(
                        "Turn off for read-only lobby / TV displays where clicks "
                        "should do nothing. When on (default), clicks open the "
                        "details slide-in, follow an object URL, or navigate to "
                        "a linked sub-map."
                    ),
                    prefill=DefaultValue(True),
                ),
            ),
            "show_in_lists": DictElement(
                required=True,
                group=_BEHAVIOR,
                parameter_form=BooleanChoice(
                    title=Title("Visibility"),
                    label=Label("Show this map in the maps list"),
                    help_text=Help(
                        "When unchecked, the map is hidden from regular users "
                        "in the maps list and dashboard. Direct links continue "
                        "to work for users who already have view permission."
                    ),
                    prefill=DefaultValue(True),
                ),
            ),
            "hover_template": DictElement(
                group=_TEMPLATES,
                parameter_form=String(
                    title=Title("Hover template"),
                    help_text=Help(
                        "Leave unchecked to inherit the global Hover template "
                        "(Settings → Object defaults). When enabled, overrides "
                        "the global default for this map only. "
                        "Placeholders: {{name}}, {{state}}, {{output}}, "
                        "{{host}}, {{service}}. "
                        "Example: '{{name}}: {{state}}' renders as 'db-prod-01: CRIT'."
                    ),
                    prefill=InputHint("e.g. {{name}} is {{state}}"),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "context_template": DictElement(
                group=_TEMPLATES,
                parameter_form=String(
                    title=Title("Context template"),
                    help_text=Help(
                        "Leave unchecked to inherit the global Context template "
                        "(Settings → Object defaults). When enabled, overrides "
                        "the global default for this map only. Same "
                        "placeholders as the hover template. "
                        "Example: 'Service {{service}} on {{host}}' renders as "
                        "'Service HTTP on web-srv-01'."
                    ),
                    prefill=InputHint("e.g. {{name}} is {{state}}"),
                    field_size=FieldSize.LARGE,
                ),
            ),
        },
    )


# Metadata fields the FormSpec covers; used by the API to slice
# MapRead → form-data and merge form-data → MapUpdate. Anything not
# in this set stays out of the FormSpec contract.
METADATA_FIELDS = (
    "alias",
    "connection_id",
    "icon_size",
    "default_z",
    "render_mode",
    "rotation_interval",
    "click_action",
    "show_in_lists",
    "hover_template",
    "context_template",
)

# ``alias`` stays single-map: applying one alias to many would collapse
# their identities. Everything else is safe to overwrite in bulk.
BULK_METADATA_FIELDS = tuple(f for f in METADATA_FIELDS if f != "alias")


def _build_bulk_metadata_spec(
    connection_choices: Sequence[tuple[str, str]] | None,
) -> Dictionary:
    # required=False makes FormEdit render a per-field activation checkbox,
    # so only the elements the operator ticks end up in the wire payload.
    single = map_metadata_spec(connection_choices)
    elements = {
        key: DictElement(
            required=False,
            group=elem.group,
            parameter_form=elem.parameter_form,
        )
        for key, elem in single.elements.items()
        if key in BULK_METADATA_FIELDS
    }
    return Dictionary(
        title=Title("Apply to selected maps"),
        help_text=Help(
            "Pick the fields you want to overwrite on every selected map. "
            "Unchecked fields stay untouched. Read-only demo maps are "
            "skipped automatically."
        ),
        elements=elements,
    )


def map_bulk_metadata_spec(
    connection_choices: Sequence[tuple[str, str]] | None = None,
) -> Dictionary:
    return _build_bulk_metadata_spec(connection_choices)


_TOPOLOGY = MapsDictGroup(
    title=Title("Hosts & Layer"),
    help_text=Help(
        "Which slice of the host graph this Flow map renders, and how "
        "many service rows are drawn per host."
    ),
)


def flow_view_spec() -> Dictionary:
    """FormSpec for the per-map fields of :class:`schemas.map.FlowView`.

    Mirrors the field ranges declared on the Pydantic model so the
    serialized schema and the on-wire validation can't drift.
    Every field is optional — unchecked means "use the global default".
    """
    return Dictionary(
        title=Title("Hosts & Layer"),
        elements={
            "root": DictElement(
                group=_TOPOLOGY,
                parameter_form=String(
                    title=Title("Root host"),
                    help_text=Help(
                        "Host the topology is anchored on. Leave unchecked "
                        "to render the full topology."
                    ),
                    prefill=InputHint("Choose root host…"),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "child_layers": DictElement(
                group=_TOPOLOGY,
                parameter_form=Integer(
                    title=Title("Child layers"),
                    help_text=Help(
                        "Hops downward from the root. -1 means unlimited "
                        "(default), 0–20 otherwise. Leave unchecked to "
                        "inherit the global default."
                    ),
                    unit_symbol="layers",
                    prefill=DefaultValue(-1),
                    custom_validate=(NumberInRange(min_value=-1, max_value=20),),
                ),
            ),
            "parent_layers": DictElement(
                group=_TOPOLOGY,
                parameter_form=Integer(
                    title=Title("Parent layers"),
                    help_text=Help(
                        "Hops upward from the root. -1 means unlimited, "
                        "0 means none (default), max 20. Leave unchecked "
                        "to inherit the global default."
                    ),
                    unit_symbol="layers",
                    prefill=DefaultValue(0),
                    custom_validate=(NumberInRange(min_value=-1, max_value=20),),
                ),
            ),
            "top_affected_hosts": DictElement(
                group=_TOPOLOGY,
                parameter_form=Integer(
                    title=Title("Hosts with service detail"),
                    help_text=Help(
                        "How many top-affected hosts get service detail "
                        "(0–1000). Leave unchecked to inherit the global "
                        "default (25)."
                    ),
                    unit_symbol="hosts",
                    prefill=DefaultValue(25),
                    custom_validate=(NumberInRange(min_value=0, max_value=1000),),
                ),
            ),
            "max_services_per_host": DictElement(
                group=_TOPOLOGY,
                parameter_form=Integer(
                    title=Title("Services per host"),
                    help_text=Help(
                        "Maximum services rendered per host (0–500). "
                        "Leave unchecked to inherit the global default (50)."
                    ),
                    unit_symbol="services",
                    prefill=DefaultValue(50),
                    custom_validate=(NumberInRange(min_value=0, max_value=500),),
                ),
            ),
        },
    )
