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
                if element.text is not None:
                    yield element.text
                    yield ""
                else:
                    if (
                        len(element) == 1
                        and element[0].tag == "code"
                        and element[0].text is not None
                    ):
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


def markdown_to_html(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["tables", "fenced_code"],
        output_format="html",
    )
