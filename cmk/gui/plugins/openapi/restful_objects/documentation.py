#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import functools
import re
from typing import List

import jinja2

from cmk.utils.livestatus_helpers import tables

TEMPLATES = {
    "table": """## {{ table.__tablename__.title() }} Table

### Columns:

| Column name | Type | Description |
| - | - | - |
{%- for column in columns %}
| {{- column.name }} | {{ column.type }} | {{ column.__doc__ | defaults_bold }} |
{%- endfor %}

{%- if adjacent_columns %}

### Adjacent columns:

| Column name | Type | Description |
| - | - | - |
{%- for column in adjacent_columns %}
| {{- column.name }} | {{ column.type }} | {{ column.__doc__ | defaults_bold }} |
{%- endfor %}
{%- endif %}

""",
}

PAREN_RE = re.compile(r"(\([^)]+\))")


def defaults_bold(text: str) -> str:
    """

    >>> defaults_bold("Text with (0-9) parenthesis.")
    'Text with **(0-9)** parenthesis.'

    Args:
        text:

    Returns:

    """
    return PAREN_RE.sub(r"**\1**", text)


@functools.lru_cache
def _jinja_env():
    env = jinja2.Environment(  # nosec
        extensions=["jinja2.ext.loopcontrols"],
        autoescape=False,  # because copy-paste we don't want HTML entities in our code examples.
        loader=jinja2.DictLoader(TEMPLATES),
    )
    env.filters.update(
        defaults_bold=defaults_bold,
    )
    env.globals.update(
        repr=repr,
        getattr=getattr,
    )
    return env


HOST_COLUMNS = tables.Hosts.__columns__()
SERVICE_COLUMNS = tables.Services.__columns__()


def is_adjacent_column(column) -> bool:
    return (column.name.startswith("host_") and column.name[5:] in HOST_COLUMNS) or (
        column.name.startswith("service_") and column.name[8:] in SERVICE_COLUMNS
    )


def table_definitions() -> List[str]:
    result = []
    table_tmpl = _jinja_env().get_template("table")
    for table_name in tables.__all__:
        table = getattr(tables, table_name)
        columns = []
        adjacent_columns = []
        for column_name in table.__columns__():
            column = getattr(table, column_name)
            if is_adjacent_column(column):
                adjacent_columns.append(column)
            else:
                columns.append(column)
        result.append(
            table_tmpl.render(
                table=table,
                columns=columns,
                adjacent_columns=adjacent_columns,
            )
        )
    return result
