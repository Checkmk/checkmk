#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import lxml.html
from pydantic import ValidationError

from .error import WerkError
from .markup import markdown_to_html
from .models import Werk
from .parse import WerkV2ParseResult


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
