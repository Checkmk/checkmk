#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.type_defs import Choices

from ._metrics import registered_metrics
from ._valuespecs import metrics_of_query


def metrics_autocompleter(value: str, params: dict) -> Choices:
    context = params.get("context", {})
    host = context.get("host", {}).get("host", "")
    service = context.get("service", {}).get("service", "")
    if not params.get("show_independent_of_context") and not all((host, service)):
        return []

    if context:
        metrics = set(metrics_of_query(context))
    else:
        metrics = set(registered_metrics())

    return sorted(
        (v for v in metrics if _matches_id_or_title(value, v)),
        key=lambda a: a[1].lower(),
    )


def _matches_id_or_title(ident: str, choice: tuple[str | None, str]) -> bool:
    return ident.lower() in (choice[0] or "").lower() or ident.lower() in choice[1].lower()
