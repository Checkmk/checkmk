#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import html

import lxml.html
from pydantic import ValidationError

from .error import WerkError
from .markup import markdown_to_html
from .models import Werk, WerkV3
from .parse import WerkV2ParseResult, WerkV3ParseResult

VALID_TAGS = {
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


def load_werk_v3(parsed: WerkV3ParseResult) -> WerkV3:
    # TODO: c&p from v2
    werk = parsed.metadata
    werk["__version__"] = "3"
    werk["description"] = markdown_to_html(parsed.description)
    _check_html(werk["description"])

    try:
        result = WerkV3.model_validate(werk)
        result.title = _format_title(result.title)
    except (ValidationError, WerkError) as e:
        raise WerkError(f"Error validating werk:\n{werk}\nerror:\n{e}") from e

    return result


def load_werk_v2(parsed: WerkV2ParseResult) -> Werk:
    werk = parsed.metadata
    werk["__version__"] = "2"

    werk["description"] = markdown_to_html(parsed.description)
    _check_html(werk["description"])

    try:
        result = Werk.model_validate(werk)
        result.title = _format_title(result.title)
    except (ValidationError, WerkError) as e:
        raise WerkError(f"Error validating werk:\n{werk}\nerror:\n{e}") from e

    return result


def _format_title(string: str) -> str:
    # if string contains any html tags throw an error, but allow and remove markdown escaping

    # this stuff seems funny, but we have to balance two things here:
    # * on the one hand we want to be able to handle valid markdown input
    #   formatting of werks should be without surprises. as the title is written in markdown, we
    #   have to behave like markdown, which means we can not automatically escape html tags or
    #   "surprise" markdown formatting
    # * on the other hand we don't want formatting in the title
    #   checkmk werks browser does not support html formatting in title, the search both on the
    #   website and the built in werks browser would have to be adapted to exclude html tags, so we
    #   want to handle it as a plain string without any special html formatting syntax.
    markdown_converted = markdown_to_html(string)
    markdown_converted = markdown_converted.removeprefix("<p>").removesuffix("</p>")
    try:
        _check_html(markdown_converted, tags_allowed=set())
    except WerkError as e:
        raise WerkError("Werk title contains formatting, this is not allowed") from e
    except Exception as e:
        raise WerkError(f"Can not parse title '{string}'") from e

    markdown_converted = html.unescape(markdown_converted)
    return markdown_converted


def _check_html(string: str, tags_allowed: set[str] | None = None) -> None:
    if tags_allowed is None:
        tags_allowed = VALID_TAGS

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
