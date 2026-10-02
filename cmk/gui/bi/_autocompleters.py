#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.gui.type_defs import Choices

from ._packs import aggregation_group_choices


def aggregation_group_autocompleter(value: str, params: dict[str, object]) -> Choices:
    return matching_aggregation_groups(
        aggregation_group_choices(), value, strict=bool(params.get("strict"))
    )


def matching_aggregation_groups(
    groups: Sequence[tuple[str, str]], value: str, *, strict: bool
) -> Choices:
    matches: Choices = [
        (ident, title) for ident, title in groups if value.lower() in f"{ident} {title}".lower()
    ]
    # Groups unknown to this site (deleted, other site/customer) must stay enterable
    return (
        [(value, value)] if value and not strict and (value, value) not in matches else []
    ) + matches
