#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass

from cmk.rulesets.v1.form_specs import FormSpec


@dataclass(frozen=True, kw_only=True)
class StaticText(FormSpec[str]):
    """Read-only display of a string. No input field is rendered; the string
    passed in at render time is shown as-is and round-tripped back unchanged
    on submit.

    Useful for computed / derived values that should appear inside a form
    but are not editable (e.g. URLs assembled from other fields, or summary
    blocks describing inherited configuration).

    ``multiline=True`` preserves newlines and renders the text inside a
    ``<pre>`` block so an indented multi-line summary stays formatted.
    """

    multiline: bool = False
