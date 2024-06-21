#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import xml.etree.ElementTree as ET
from collections.abc import Iterator

import markdown


def nowiki_to_markdown(description: list[str]) -> str:
    # "inspired" by render_nowiki_werk_description
    # why don't we generate html at this stage?
    # because we can use this function to actually convert werkv1 to werkv2 in
    # the .werks folder.
    def generator() -> Iterator[str]:
        for line in description:
            if line.startswith("LI: "):
                yield "* " + line.removeprefix("LI:").lstrip()
            elif line.startswith("NL:"):
                yield "1. " + line.removeprefix("NL:").lstrip()
            elif line.startswith("H2:"):
                yield "## " + line.removeprefix("H2:").lstrip()
            elif line.startswith("C+:"):
                yield "```"
            elif line.startswith("F+:"):
                filename = line.removeprefix("F+:").lstrip()
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


def _render_children(element: ET.Element) -> str:
    tail = element.tail
    if tail == "\n" or tail is None:
        tail = ""
    return "".join(
        (
            element.text or "",
            *(_render_element(e) for e in element),
            tail,
        )
    )


def _render_element(element: ET.Element) -> str:
    result: str = ET.tostring(element, encoding="utf-8", method="html").decode("utf-8")
    return result


def markdown_to_nowiki(content: str) -> str:
    # we do have html/xml fragments in content,
    # but the xml parser needs a single root element, so we wrap it in root.

    # nowiki / werkv1 supports html, so we convert markdown to html, and
    # replace the most common html elements to nowiki syntax.

    content_html = markdown.markdown(
        content,
        extensions=["tables", "fenced_code"],
        output_format="html",
    )

    root = ET.fromstringlist(["<root>", content_html, "</root>"])

    def generator() -> Iterator[str]:
        for element in root:
            if element.tag == "p":
                if element.text is not None or element:
                    yield _render_children(element)
                    yield ""
                elif element[0].tag == "code":
                    yield "C+:"
                    yield _render_children(element[0])
                    yield "\n----\nC-:\n"
                else:
                    raise NotImplementedError()
            elif element.tag == "ul":
                for li in element:
                    yield f"LI: {_render_children(li)}"
                yield ""
            elif element.tag == "h2":
                yield f"H2: {_render_children(element)}"
                yield ""
            elif element.tag == "pre":
                yield "C+:"
                # text already contains closing \n
                yield f"{_render_children(element[0])}C-:"
                yield ""
            else:
                yield _render_element(element)

    return "\n".join(generator())


def markdown_to_html(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["tables", "fenced_code"],
        output_format="html",
    )
