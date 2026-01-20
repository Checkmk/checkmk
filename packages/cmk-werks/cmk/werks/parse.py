#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import NamedTuple

from .error import WerkError


class WerkV2ParseResult(NamedTuple):
    metadata: dict[str, str]
    description: str


class WerkV3ParseResult(NamedTuple):
    metadata: dict[str, str]
    description: str


def markdown_table_to_dict(markdown_table: str) -> dict[str, str]:
    """
    Convert a Markdown table to dictionary.
    """

    elements = []
    for line in markdown_table.strip().split("\n"):
        columns = tuple(c.strip() for c in line.split("|"))
        if len(columns) not in {2, 4}:
            raise WerkError(f"Table should have exactly two columns, found {line!r} instead")
        if len(columns) == 4:
            columns = columns[1:-1]
        elements.append((columns[0], columns[1]))

    if len(elements) < 2:
        raise WerkError("Table needs to contain at least header and separator")

    header = elements.pop(0)
    if header != ("key", "value"):
        raise WerkError(
            f"Table should have a header with columns 'key' and 'value', found {header}"
        )

    separator = elements.pop(0)
    if not all(re.match(":?[-]{3,}:?", s) for s in separator):
        raise WerkError("Second row in markdown table should be a separator line")

    return dict(elements)


def parse_werk_v3(content: str, werk_id: str) -> WerkV3ParseResult:
    metadata: dict[str, str] = {
        "id": werk_id,
    }
    if not content.startswith("[//]: # (werk v3)\n"):
        raise WerkError(
            "V3 Markdown formatted werks need to start with header: '[//]: # (werk v3)\\n'"
        )

    sections = content.split("\n\n", 2)
    if len(sections) == 2:
        md_title, md_table = sections
        md_description = ""
    elif len(sections) == 3:
        md_title, md_table, md_description = sections
    else:
        raise WerkError(
            "Structure of markdown werk could not be detected. Format has to be:"
            "header, headline, empty line, table and optionally empty line, description"
        )

    title = md_title.removeprefix("[//]: # (werk v3)\n")

    # TODO: check if it really is a h1 headline?!
    if not title.startswith("#"):
        raise WerkError(
            "First element after the header needs to be the title as a h1 headline. "
            "The line has to start with '#'."
        )
    metadata["title"] = title.removeprefix("#").strip()

    # we parse the table on our own, converting it to html and parsing the html is quite slow
    metadata.update(markdown_table_to_dict(md_table))

    return WerkV3ParseResult(metadata, md_description)


def parse_werk_v2(content: str, werk_id: str) -> WerkV2ParseResult:
    """
    parse werk v2 but do not validate
    """
    metadata: dict[str, str] = {
        "id": werk_id,
    }
    # no need to parse the werk version here. markdown version and werk version
    # could potentially be different: a markdown version 3 could be parsed to a
    # werk version 2. let's hope we will keep v2 for a long time :-)
    if not content.startswith("[//]: # (werk v2)\n"):
        raise WerkError(
            "Markdown formatted werks need to start with header: '[//]: # (werk v2)\\n'"
        )

    sections = content.split("\n\n", 2)
    if len(sections) == 2:
        md_title, md_table = sections
        md_description = ""
    elif len(sections) == 3:
        md_title, md_table, md_description = sections
    else:
        raise WerkError(
            "Structure of markdown werk could not be detected. Format has to be:"
            "header, headline, empty line, table and optionally empty line, description"
        )

    title = md_title.removeprefix("[//]: # (werk v2)\n")

    # TODO: check if it really is a h1 headline?!
    if not title.startswith("#"):
        raise WerkError(
            "First element after the header needs to be the title as a h1 headline. "
            "The line has to start with '#'."
        )
    metadata["title"] = title.removeprefix("#").strip()

    # we parse the table on our own, converting it to html and parsing the html is quite slow
    metadata.update(markdown_table_to_dict(md_table))

    return WerkV2ParseResult(metadata, md_description)


class WerkV1ParseResult(NamedTuple):
    metadata: dict[str, str]
    description: list[str]


def parse_werk_v1(content: str, werk_id: int) -> WerkV1ParseResult:
    """
    parse werk v1 but do not validate, or transform description
    """
    werk: dict[str, str] = {
        # older werks don't specify compatible or edition
        "compatible": "compat",
        "edition": "cre",
        "id": str(werk_id),
    }
    description = []
    in_header = True
    for line in content.split("\n"):
        try:
            if in_header and not line.strip():
                in_header = False
            elif in_header:
                key, text = line.split(":", 1)
                try:
                    value = str(int(text.strip()))
                except ValueError:
                    value = text.strip()
                field = key.lower()
                werk[field] = value
            else:
                description.append(line)
        except Exception as e:
            raise RuntimeError(f"Can not parse line {line!r} of werk {werk_id}") from e

    while description and description[-1] == "":
        description.pop()

    return WerkV1ParseResult(werk, description)
