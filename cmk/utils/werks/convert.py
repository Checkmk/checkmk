#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import xml.etree.ElementTree as ET

from .werk import Compatibility
from .werkv1 import parse_werk_v1
from .werkv2 import load_werk_v2, parse_werk_v2


def nowiki_to_markdown(description: list[str]) -> str:
    # "inspired" by render_nowiki_werk_description
    # why don't we generate html at this stage?
    # because we can use this function to actually convert werkv1 to werkv2 in
    # the .werks folder.
    def generator():
        for line in description:
            if line.startswith("LI:"):
                yield "* " + line.removeprefix("LI:")
            elif line.startswith("NL:"):
                yield "1. " + line.removeprefix("NL:")
            elif line.startswith("H2:"):
                yield "## " + line.removeprefix("H2:")
            elif line.startswith("C+:"):
                yield "```"
            elif line.startswith("F+:"):
                filename = line.removeprefix("F+:")
                if filename:
                    yield "`" + filename + "`"
                yield "```"
            elif line.startswith("C-:") or line.startswith("F-:"):
                yield "```"
            elif line.startswith("OM:"):
                yield "OMD[mysite]:~$ " + line.removeprefix("OM:")
            elif line.startswith("RP:"):
                yield "root@linux:~# " + line.removeprefix("RP:")
            else:
                yield line

    return "\n".join(generator())


def html_to_nowiki(content: str) -> str:
    # we do have html/xml fragments in content,
    # but the xml parser needs a single root element, so we wrap it in root.
    root = ET.fromstringlist(["<root>", content, "</root>"])

    def generator():
        for element in root:
            if element.tag == "p":
                if element.text is not None:
                    yield element.text
                    yield ""
                else:
                    if len(element) == 1 and element[0].tag == "code":
                        yield "C+:"
                        yield element[0].text
                        yield "C-:\n"
                    else:
                        raise NotImplementedError()
            elif element.tag == "ul":
                for li in element:
                    yield f"LI: {li.text}"
                yield ""
            elif element.tag == "h2":
                yield f"H2: {element.text}"
                yield ""
            elif element.tag == "pre":
                yield "C+:"
                # text already contains closing \n
                yield f"{element[0].text}C-:"
                yield ""
            else:
                raise NotImplementedError(f"can not handle tag {element.tag}")

    return "\n".join(generator())


def _table_entry(key: str, value: str) -> str:
    return f"{key} | {value}"


# CMK-14546
# def _escape_markdown(text: str) -> str:
#     """
#     >>> _escape_markdown("- one")
#     '\\\\- one'
#     >>> _escape_markdown("some_thing")
#     'some\\\\_thing'
#     >>> _escape_markdown("some[thing")
#     'some\\\\[thing'
#     """
#     return re.sub(r"([\`*_{}\[\]()#+-.!])", r"\\\1", text)


def werkv1_to_werkv2(werkv1_content: str, werk_id: int) -> tuple[str, int]:
    # try to keep errors in place, so the validation of werkv2 will show errors in werkv1
    parsed = parse_werk_v1(werkv1_content, werk_id)
    metadata = parsed.metadata
    metadata.pop("id", None)  # is the filename
    metadata.pop("knowledge", None)  # removed field
    metadata.pop("state", None)  # removed field
    metadata.pop("targetversion", None)  # removed field

    def generator():
        yield "[//]: # (werk v2)"
        if (title := metadata.pop("title", None)) is not None:
            # TODO: wait for CMK-14546: we might need to markdown escape the title
            # yield f"# {_escape_markdown(title)}"
            yield f"# {title}"
        yield ""
        yield _table_entry("key", "value")
        yield _table_entry("---", "---")
        if (compatible := metadata.pop("compatible", None)) is not None:
            compatible = "yes" if compatible == "compat" else "no"
            yield _table_entry("compatible", compatible)
        if (version := metadata.pop("version", None)) is not None:
            yield _table_entry("version", version)
        if (date := metadata.pop("date", None)) is not None:
            date = datetime.datetime.fromtimestamp(
                float(date), tz=datetime.timezone.utc
            ).isoformat()
            yield _table_entry("date", date)
        if (level := metadata.pop("level", None)) is not None:
            yield _table_entry("level", level)
        if (class_ := metadata.pop("class", None)) is not None:
            yield _table_entry("class", class_)
        if (component := metadata.pop("component", None)) is not None:
            yield _table_entry("component", component)
        if (edition := metadata.pop("edition", None)) is not None:
            yield _table_entry("edition", edition)
        for key, value in metadata.items():
            # this should never happen, but will give us a nice error message
            # when this is parsed as werkv2
            yield _table_entry(key, value)
        yield ""
        yield nowiki_to_markdown(parsed.description)

    return "\n".join(generator()), werk_id


def werkv2_to_werkv1(werkv2_content: str, werk_id: int) -> tuple[str, int]:
    werk = load_werk_v2(parse_werk_v2(werkv2_content, str(werk_id)))

    def generator():
        yield f"Title: {werk.title}"
        yield f"Class: {werk.class_.value}"
        if werk.compatible == Compatibility.COMPATIBLE:
            compatible = "compat"
        elif werk.compatible == Compatibility.NOT_COMPATIBLE:
            compatible = "incomp"
        else:
            raise NotImplementedError()
        yield f"Compatible: {compatible}"
        yield f"Component: {werk.component}"
        yield f"Date: {int(werk.date.timestamp())}"
        yield f"Edition: {werk.edition.value}"
        yield f"Level: {werk.level.value}"
        yield f"Version: {werk.version}"
        yield ""
        if not isinstance(werk.description, str):
            raise Exception("expected markdown werk description")
        yield html_to_nowiki(werk.description)

    return "\n".join(generator()), werk_id
