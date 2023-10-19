#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple

import lxml.html
import markdown

from .error import WerkError


class WerkV2ParseResult(NamedTuple):
    metadata: dict[str, str]
    description: str


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
            "First element after the header needs to be the title as a h1 headline. The line has to start with '#'."
        )
    metadata["title"] = title.removeprefix("#").strip()

    metadata_html = markdown.markdown(
        md_table,
        extensions=["tables"],
        output_format="html",
    )

    parser = lxml.html.HTMLParser(recover=False)
    table_element = lxml.html.fromstring(metadata_html, parser=parser)
    # TODO: maybe assert len of table_element?!
    if table_element.tag != "table":
        raise WerkError(f"Expected a table after the title, found '{table_element.tag}'")
    tbody = table_element.findall("./tbody/")
    for table_tr in tbody:
        key, value = table_tr.findall("./td")
        if key.text is None or value.text is None:
            continue
        metadata[key.text] = value.text

    return WerkV2ParseResult(metadata, md_description)


class WerkV1ParseResult(NamedTuple):
    metadata: dict[str, str]
    description: list[str]


def parse_werk_v1(content: str, werk_id: int) -> WerkV1ParseResult:
    """
    parse werk v1 but do not validate, or transform description
    """
    werk: dict[str, str] = {
        "compatible": "compat",
        "edition": "cre",
        "id": str(werk_id),
    }
    description = []
    in_header = True
    for line in content.split("\n"):
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

    while description and description[-1] == "":
        description.pop()

    return WerkV1ParseResult(werk, description)
