#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple

import lxml.html
import markdown
from pydantic import ValidationError

from .werk import Werk, WerkError


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

    try:
        md_title, md_table, md_description = content.split("\n\n", 2)
    except ValueError as e:
        raise WerkError(
            "Structure of markdown werk could not be detected. Format has to be:"
            "header, headline, empty line, table, empty line, description"
        ) from e

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


def markdown_to_html(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["tables", "fenced_code"],
        output_format="html",
    )


def load_werk_v2(parsed: WerkV2ParseResult) -> Werk:
    werk = parsed.metadata
    werk["__version__"] = "2"

    # see CMK-14546
    # try:
    #     # the treeprocessor that extracted the title runs before the inline processor, so no inline
    #     # markdown (links, bold, italic,..) has been replaced. this is
    #     # basically okay, because we don't want any formatting in the
    #     # headline. but we want to give some hint to the user that no
    #     # formatting is allowed.
    #     _raise_if_contains_markdown_formatting(werk["title"])
    # except WerkError as e:
    #     raise WerkError(
    #         "Markdown formatting in title detected, this is not allowed."
    #     ) from e

    werk["description"] = markdown_to_html(parsed.description)
    _check_html(werk["description"])

    try:
        return Werk.model_validate(werk)
    except ValidationError as e:
        raise WerkError(f"Error validating werk:\n{werk}\nerror:\n{e}") from e


# see CMK-14546
# def _raise_if_contains_markdown_formatting(string: str) -> None:
#     markdown_converted = markdown.markdown(string)
#     # if markdown_converted contains any html tags, then string contained markdown formatting
#     try:
#         number_of_tags = len(etree.fromstring(markdown_converted))
#     except Exception as e:
#         if '<<<' in string and '>>>' in string:
#             # this is a hack, ignore if someone describes an agent section
#             # title needs to be rendered without html interpretation anyway, we just want to give a
#             # hint to the developer writing the werk, if they use formatting in the title.
#             return
#         raise WerkError(f"Can not parse title '{string}' to check if it contains html") from e
#     if number_of_tags:
#         raise WerkError(
#             f"string contained markdown formatting:\nstring: {string}\nformatted string: {markdown_converted}"
#         )


def _check_html(string: str) -> None:
    tags_allowed = {
        "code",
        "em",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "li",
        "ol",
        "p",
        "pre",
        "strong",
        "table",
        "td",
        "thead",
        "tr",
        "ul",
        "a",
        "b",
        "blockquote",
        "br",
        "i",
        "th",
        "tt",
        "hr",
    }
    parser = lxml.html.HTMLParser(recover=False)
    tree = lxml.html.fromstring(f"<html><body>{string}</body></html>", parser=parser)
    tags_found = {e.tag for e in tree.xpath("./body//*")}
    tags_unknown = tags_found.difference(tags_allowed)
    if tags_unknown:
        tag_list = ", ".join(f"<{tag}>" for tag in tags_unknown)
        raise WerkError(f"Found tag {tag_list} which is not in the list of allowed tags.")

    li_parents_found = {e.getparent().tag for e in tree.xpath("./body//li")}
    li_illegal_parents = li_parents_found.difference({"ul", "ol"})
    if li_illegal_parents:
        raise WerkError("Found li tags which are not inside <ul> or <ol>. This breaks the html.")
