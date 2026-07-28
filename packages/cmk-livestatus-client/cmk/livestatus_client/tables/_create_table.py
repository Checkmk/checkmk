#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.livestatus_client.types import Column, {% if dynamic_columns %}DynamicColumn, {% endif %}Table

# fmt: off


class {{ table_name.title() }}(Table):
    __tablename__ = '{{ table_name }}'
    {%- for col in columns %}{% set column_name = col.name %}

    {{ column_name }} = Column(
        '{{ col.name }}',{% if col.name != column_name %}  # sic{% endif %}
        col_type='{{ col.type }}',
        description='{{ col.description | replace("'", "\\\\'") }}',
    )
    """{{ col.description }}"""{% endfor %}
    {%- if dynamic_columns %}

    # Dynamic columns are registered in the core via addDynamicColumn and are
    # not listed in livestatus' "columns" table. They are maintained manually
    # in DYNAMIC_COLUMNS in _create_table.py.
    {%- for col in dynamic_columns %}

    {{ col.name }} = DynamicColumn(
        '{{ col.name }}',
        col_type='{{ col.type }}',
        description='{{ col.description | replace("'", "\\\\'") }}',
    )
    """{{ col.description }}"""{% endfor %}
    {%- endif %}

'''

_RRDDATA_DESCRIPTION: Final = (
    "RRD metrics data of this object. This is a column with parameters: "
    "rrddata:COLUMN_TITLE:VARNAME:FROM_TIME:UNTIL_TIME:RESOLUTION"
)

# Dynamic columns (see addDynamicColumn in packages/livestatus) do not show up
# in livestatus' "columns" table, so they cannot be generated from the CSV
# input and are maintained here manually.
DYNAMIC_COLUMNS: Final = {
    "crashreports": [
        {
            "name": "file",
            "type": "blob",
            "description": "Files related to the crash report (crash.info, etc.)",
        },
    ],
    "hosts": [
        {
            "name": "mk_logwatch_file",
            "type": "blob",
            "description": "This contents of a logfile fetched via mk_logwatch",
        },
        {
            "name": "rrddata",
            "type": "list",
            "description": _RRDDATA_DESCRIPTION,
        },
    ],
    "services": [
        {
            "name": "prediction_file",
            "type": "blob",
            "description": "Fetch prediction data",
        },
        {
            "name": "rrddata",
            "type": "list",
            "description": _RRDDATA_DESCRIPTION,
        },
    ],
}


def transform_csv(table_name: str) -> None:
    """Take a CSV-Input and convert it into a table definition file.

    Args:
        table_name:
            The name of the LiveStatus table.

    Returns:
        Nothing.
    """
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)  # nosec B701 # BNS:bbfc92
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

        sys.stdout.write(
            str(
                template.render(
                    table_name=table_name,
                    columns=column_entries,
                    dynamic_columns=DYNAMIC_COLUMNS.get(table_name, []),
                )
            )
        )
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
