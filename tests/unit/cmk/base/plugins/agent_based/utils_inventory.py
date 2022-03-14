#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, Sequence, Union

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, TableRow


def sort_inventory_result(
    result: Iterable[Union[Attributes, TableRow]]
) -> Sequence[Union[Attributes, TableRow]]:
    return sorted(
        result,
        key=lambda r: (
            sorted(r.key_columns.items()),
            sorted(r.inventory_columns.items()),
            sorted(r.status_columns.items()),
        )
        if isinstance(r, TableRow)
        else (
            sorted(r.inventory_attributes.items()),
            sorted(r.status_attributes.items()),
        ),
    )
