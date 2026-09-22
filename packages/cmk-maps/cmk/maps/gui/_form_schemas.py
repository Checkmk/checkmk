#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Serve the Maps admin FormSpec schemas from the GUI, and translate their values.

Rendering a FormSpec (``serialize_data_for_frontend``) needs the full GUI
request + authenticated-user context — e.g. the ``Password`` form spec lists
the logged-in user's password store. The ``cmk.maps.backend`` daemon is a
Flask-free FastAPI service and cannot provide that, so the schemas are rendered
here, in the GUI process, as the logged-in user. The two internal REST endpoints
in :mod:`cmk.maps.rest_api.internal.form_schemas` expose what this module
builds; the frontend's ``FormEdit`` consumes it.

A FormSpec's *values* also travel through here, in both directions, because the
wire form of a value is not its stored form: a ``SingleChoice`` sends an opaque
id per element (``option_id`` hashes the element name, which may be any object),
and only the form spec's visitor knows that mapping. The SPA therefore hands its
stored values to :func:`render_form_schema` and its edited values back to
:func:`parse_form_values` rather than reading the data bag directly — the same
arrangement notification parameters and the quick setup use.

The connections, map/object defaults and logging/integration settings are
*not* served here — they are native Checkmk global settings (Setup → Global
settings → "Maps"), edited in WATO; see ``cmk.maps.gui._config_variables``.
What remains here is the per-map map metadata / flow-view editor the SPA
renders inline.
"""

from collections.abc import Sequence
from dataclasses import asdict
from typing import Literal

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.form_specs import (
    DEFAULT_VALUE,
    get_visitor,
    IncomingData,
    RawDiskData,
    RawFrontendData,
    serialize_data_for_frontend,
    VisitorOptions,
)
from cmk.maps.gui._settings import connection_choices
from cmk.maps.gui.form_specs.map_metadata import (
    flow_view_spec,
    map_bulk_metadata_spec,
    map_metadata_spec,
)
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.shared_typing.vue_formspec_components import ValidationMessage

# The dialogs the SPA renders from a server-side FormSpec.
type FormSchemaName = Literal["map_metadata", "map_bulk_metadata", "flow_view"]


def _build_spec(spec_name: FormSchemaName) -> Dictionary:
    """The whole form spec, including the fields a given map type does not offer.

    Which of them a dialog renders is presentation, while every stored value
    still has to make the round trip: serialising a narrowed spec would drop the
    hidden ones from the bag and save them back as their defaults.
    """
    match spec_name:
        case "map_metadata":
            return map_metadata_spec(connection_choices=connection_choices())
        case "map_bulk_metadata":
            return map_bulk_metadata_spec(connection_choices=connection_choices())
        case "flow_view":
            return flow_view_spec()


def render_form_schema(
    spec_name: FormSchemaName, stored: dict[str, object] | None
) -> tuple[dict[str, object], dict[str, object]]:
    """Render a Maps FormSpec to the Checkmk Vue wire format, with its values.

    ``stored`` holds the values to prefill in their stored form; ``None`` renders
    the form spec's own prefills, which is what the bulk-edit dialog (it starts
    out empty) and a brand-new map want.

    Answers the component tree and the encoded values, which is what ``FormEdit``
    takes — the rest of the ``VueAppConfig`` envelope is of no use to it.
    """
    value: IncomingData = DEFAULT_VALUE if stored is None else RawDiskData(stored)
    rendered = asdict(
        serialize_data_for_frontend(_build_spec(spec_name), "maps", do_validate=False, value=value)
    )
    return rendered["spec"], rendered["data"] or {}


def parse_form_values(
    spec_name: FormSchemaName, values: dict[str, object]
) -> tuple[dict[str, object] | None, Sequence[ValidationMessage]]:
    """Translate an edited FormSpec value bag back into stored values.

    The way back from :func:`render_form_schema`: the SPA posts the bag its form
    produced and gets the values as they are stored, which is what it then sends
    to the Maps REST API. The form spec's own validators run here too, so a bad
    value is reported against the field that carries it instead of surfacing as
    an API rejection with no field to blame.

    Returns ``(values, [])`` on success and ``(None, messages)`` when the form
    spec refused the input — the messages are an answer rather than an error,
    because the dialog renders each one on its own field.
    """
    # Validate and translate through one visitor, the way a notification
    # parameter is saved.
    visitor = get_visitor(
        _build_spec(spec_name), VisitorOptions(migrate_values=False, mask_values=False)
    )
    incoming = RawFrontendData(values)
    if messages := visitor.validate(incoming):
        return None, messages
    # Every Maps form spec is a ``Dictionary``, so its disk value is a mapping;
    # the visitor's return type cannot say so (the same narrowing a notification
    # parameter does on save).
    stored = visitor.to_disk(incoming)
    if not isinstance(stored, dict):
        raise MKGeneralException(f"Maps form spec {spec_name!r} did not produce a mapping.")
    return stored, []
