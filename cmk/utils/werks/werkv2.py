#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple

import lxml.html
import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from pydantic import ValidationError

from .werk import Werk, WerkError


class WerkV2ParseResult(NamedTuple):
    metadata: dict[str, str]
    description: str


def parse_werk_v2(content: str, werk_id: str) -> WerkV2ParseResult:
    """
    parse werk v2 but do not validate
    """
    # no need to parse the werk version here. markdown version and werk version
    # could potentially be different: a markdown version 3 could be parsed to a
    # werk version 2. let's hope we will keep v2 for a long time :-)
    if not content.startswith("[//]: # (werk v2)"):
        raise WerkError("Markdown formatted werks need to start with '[//]: # (werk v2)'")

    class WerkExtractor(Treeprocessor):
        def __init__(self, werk):
            super().__init__()
            self._werk = werk

        def run(self, root):
            headline = root[0]
            if headline.tag != "h1":
                raise WerkError(
                    "First element after the header needs to be the title as a h1 headline. The line has to start with '#'."
                )

            self._werk["title"] = headline.text
            root.remove(headline)

            # we removed the headline so we can access element 0 again with a
            # different result.
            table = root[0]
            if table.tag != "table":
                raise WerkError(f"Expected a table after the title, found '{table.tag}'")
            tbody = table.findall("./tbody/")
            for table_tr in tbody:
                key, value = table_tr.findall("./td")
                self._werk[key.text] = value.text
            root.remove(root.findall("./table")[0])

    class WerkExtractorExtension(Extension):
        def __init__(self, werk):
            super().__init__()
            self._werk = werk

        def extendMarkdown(self, md):
            md.treeprocessors.register(WerkExtractor(self._werk), "werk", 100)

    metadata: dict[str, str] = {
        "id": werk_id,
    }
    description = markdown.markdown(
        content,
        extensions=["tables", "fenced_code", WerkExtractorExtension(metadata)],
        output_format="html",
    )
    # metadata was passed by reference into WerkExtractorExtension which got passed
    # to WerkExtractor which wrote all the fields.

    return WerkV2ParseResult(metadata, description)


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

    raise_if_contains_unknown_tags(parsed.description)

    werk["description"] = parsed.description

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


def raise_if_contains_unknown_tags(string: str) -> None:
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
