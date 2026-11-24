#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""How a link from a legacy view names the filters it could not take over, so that the monitoring
page it opens can say which of them it does not apply."""

from collections.abc import Callable, Sequence
from typing import Final

from cmk.gui.http import Request
from cmk.gui.type_defs import FilterName

_UNAPPLIED_FILTERS_VAR: Final = "unapplied"

type FilterTitleLookup = Callable[[FilterName], str | None]
"""Looks up the title of a legacy filter, ``None`` for a name that is no legacy filter."""


def encode_unapplied_filters(unapplied: Sequence[FilterName]) -> list[tuple[str, str]]:
    """Encode the filters a link could not take over as URL variables. Return none if it took
    over all of them."""
    return [(_UNAPPLIED_FILTERS_VAR, ",".join(unapplied))] if unapplied else []


def read_unapplied_filter_titles(
    request: Request, look_up_title: FilterTitleLookup
) -> list[tuple[FilterName, str]]:
    """Read from the URL of ``request`` the filters a link could not take over, with their
    titles. Leave out a name that is no legacy filter: the page only ever names real filters,
    whatever the URL says."""
    return [
        (name, title)
        for name in dict.fromkeys((request.var(_UNAPPLIED_FILTERS_VAR) or "").split(","))
        if name and (title := look_up_title(name)) is not None
    ]
