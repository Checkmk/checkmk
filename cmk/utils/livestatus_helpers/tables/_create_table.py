#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Script to create livestatus table definition files.

In this directory, use it like this:

    $ make hosts.py

You can call this script on it's own as well, for this to work you need to feed it
a CSV from a livestatus response of the query:

    GET columns
    Columns: description name table type

The "Columns:" header is mandatory, because livestatus then skips the column header, with
we don't want to deal with.

Then you can just call it like this.

    lq "$QUERY" > tables.csv
    ./_create_table.py hosts < tables.csv

"""

import argparse
import csv
import itertools
import operator
import sys
from typing import Final

import jinja2

TABLE_FILE_TEMPLATE: Final = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.utils.livestatus_helpers.types import Column, Table

# yapf: disable


class {{ table_name.title() }}(Table):
    __tablename__ = '{{ table_name }}'
    {%- for col in columns %}{% set column_name = col.name %}

    {{ column_name }} = Column(
        '{{ col.name }}',{% if col.name != column_name %}  # sic{% endif %}
        col_type='{{ col.type }}',
        description='{{ col.description | replace("'", "\\\\'") }}',
    )
    """{{ col.description }}"""{% endfor %}

'''


def transform_csv(table_name: str) -> None:
    """Take a CSV-Input and convert it into a table definition file.

    Args:
        table_name:
            The name of the LiveStatus table.

    Returns:
        Nothing.
    """
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)  # nosec
    template = env.from_string(TABLE_FILE_TEMPLATE)
    columns = ["description", "name", "table", "type"]

    reader = csv.DictReader(sys.stdin, delimiter=";", fieldnames=columns)

    for _table_name, group in itertools.groupby(
        sorted(reader, key=operator.itemgetter("table", "name")),
        key=operator.itemgetter("table"),
    ):
        # If multiple tables should be in the CSV, we only take the one we care about.
        if _table_name != table_name:
            continue

        column_entries = list(group)  # consume the generator
        for entry in column_entries:
            assert not any(entry[column] is None for column in columns)

        sys.stdout.write(str(template.render(table_name=table_name, columns=column_entries)))
        break


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("table_name", metavar="TABLE")

    # Show help in case of no parameters.
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    transform_csv(args.table_name)


if __name__ == "__main__":
    main()
