#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""FormSpec definitions for the Checkmk Maps admin forms.

Rendering FormSpecs needs the full GUI context (visitor registry, request +
authenticated-user context for e.g. the password store), so the specs live in
``cmk.maps.gui`` and are serialised in the GUI process — not by the
``cmk.maps.backend`` daemon, which is a Flask-free FastAPI service. The daemon
keeps the data CRUD + the flat form-dict mappers (which depend on its own
schemas); these spec builders are GUI-side and dependency-free of the daemon.
"""

from dataclasses import dataclass

from cmk.rulesets.internal.form_specs import DictGroupExtended, DictionaryGroupLayout

# Line-style choices for the object-default dropdown. Mirrors the daemon's
# ``cmk.maps.backend.object_options.LINE_STYLES`` (the daemon owns the runtime
# list for its object-options endpoint; the GUI carries this static copy for
# rendering the global-settings form, since it cannot import the daemon).
LINE_STYLES: tuple[tuple[str, str], ...] = (
    ("plain", "Simple line"),
    ("dashed", "Dashed"),
    ("arrow_end", "Arrow at end"),
    ("arrow_start", "Arrow at start"),
    ("arrow_both", "Arrows on both ends"),
    ("arrow_inward", "Arrows pointing inward"),
)


@dataclass(frozen=True, kw_only=True)
class MapsDictGroup(DictGroupExtended):
    """A Checkmk ``DictGroupExtended`` defaulting to a vertical layout."""

    layout: DictionaryGroupLayout = DictionaryGroupLayout.vertical


__all__ = [
    "LINE_STYLES",
    "MapsDictGroup",
]
