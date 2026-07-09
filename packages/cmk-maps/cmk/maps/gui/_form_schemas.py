#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Serve the Maps admin FormSpec schemas from the GUI, and translate their values.

Rendering a FormSpec (``serialize_data_for_frontend``) needs the full GUI
request + authenticated-user context — e.g. the ``Password`` form spec lists
the logged-in user's password store. The ``cmk.maps.backend`` daemon is a
Flask-free FastAPI service and cannot provide that, so the schemas are rendered
here (an AjaxPage runs in the normal GUI request as the logged-in user). One
endpoint dispatches on the ``spec`` query parameter; the frontend's FormApp
consumes the returned config.

A FormSpec's *values* also travel through here, in both directions, because the
wire form of a value is not its stored form: a ``SingleChoice`` sends an opaque
id per element (``option_id`` hashes the element name, which may be any object),
and only the form spec's visitor knows that mapping. The SPA therefore hands its
stored values to ``AjaxMapsFormSchema`` and its edited values back to
``AjaxMapsFormParse`` rather than reading the data bag directly — the same
arrangement notification parameters and the quick setup use.

The connections, map/object defaults and logging/integration settings are
*not* served here — they are native Checkmk global settings (Setup → Global
settings → "Maps"), edited in WATO; see ``cmk.maps.gui._config_variables``.
What remains here is the per-map map metadata / flow-view editor the SPA
renders inline.
"""

from dataclasses import asdict
from typing import override

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs import (
    DEFAULT_VALUE,
    get_visitor,
    IncomingData,
    RawDiskData,
    RawFrontendData,
    serialize_data_for_frontend,
    VisitorOptions,
)
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import AjaxPage, PageContext, PageResult
from cmk.maps.gui._settings import connection_choices
from cmk.maps.gui.form_specs.map_metadata import (
    flow_view_spec,
    map_bulk_metadata_spec,
    map_metadata_spec,
)
from cmk.rulesets.v1.form_specs import Dictionary


def _build_spec(spec_name: str) -> Dictionary:
    match spec_name:
        case "map_metadata":
            return map_metadata_spec(connection_choices=connection_choices())
        case "map_bulk_metadata":
            return map_bulk_metadata_spec(connection_choices=connection_choices())
        case "flow_view":
            return flow_view_spec()
        case _:
            raise MKGeneralException(f"Unknown Maps form spec: {spec_name!r}")


def _requested_spec(ctx: PageContext) -> Dictionary:
    """The form spec the caller asked for.

    Always the whole spec, including the fields a given map type does not
    offer: which of them a dialog renders is presentation, while every stored
    value still has to make the round trip. Serialising a narrowed spec would
    drop the hidden ones from the bag and save them back as their defaults.
    """
    return _build_spec(ctx.request.get_ascii_input_mandatory("spec"))


def _values_sent(ctx: PageContext) -> object | None:
    """The value bag the SPA sent, or ``None`` if it sent none."""
    values = ctx.request.get_request(exclude_vars=["_csrf_token", "spec"]).get("data")
    if values is None:
        return None
    if not isinstance(values, dict):
        raise MKUserError("data", _("The form values must be sent as an object."))
    return values


class AjaxMapsFormSchema(AjaxPage):
    """Render a Maps admin FormSpec, and its values, to the Checkmk Vue wire format.

    ``maps.py?...`` → SPA → ``ajax_maps_form_schema.py?spec=<name>``.

    ``data`` holds the stored values to prefill, in their stored form; omitting
    it renders the form spec's own prefills, which is what the bulk-edit dialog
    (it starts out empty) and a brand-new map want.
    """

    @override
    def page(self, ctx: PageContext) -> PageResult:
        user.need_permission("maps.use")
        stored = _values_sent(ctx)
        value: IncomingData = DEFAULT_VALUE if stored is None else RawDiskData(stored)
        return asdict(
            serialize_data_for_frontend(
                _requested_spec(ctx), "maps", do_validate=False, value=value
            )
        )


class AjaxMapsFormParse(AjaxPage):
    """Translate an edited FormSpec value bag back into stored values.

    The way back from ``AjaxMapsFormSchema``: the SPA posts the bag its form
    produced and gets the values as they are stored, which is what it then sends
    to the Maps REST API. The form spec's own validators run here too, so a bad
    value is reported against the field that carries it instead of surfacing as
    an API rejection with no field to blame.

    Answers ``{"data": ...}`` on success and ``{"validation": [...]}`` when the
    form spec refused the input — the shape the dialog's ``backend-validation``
    already renders.
    """

    @override
    def page(self, ctx: PageContext) -> PageResult:
        user.need_permission("maps.use")
        values = _values_sent(ctx)
        if values is None:
            raise MKUserError("data", _("No form values were sent."))
        # Validate and translate through one visitor, the way a notification
        # parameter is saved. The messages are the answer here rather than an
        # exception, because the dialog renders them on their own fields.
        visitor = get_visitor(
            _requested_spec(ctx), VisitorOptions(migrate_values=False, mask_values=False)
        )
        incoming = RawFrontendData(values)
        if messages := visitor.validate(incoming):
            return {"validation": [asdict(message) for message in messages]}
        return {"data": visitor.to_disk(incoming)}
