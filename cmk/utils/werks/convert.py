#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import xml.etree.ElementTree as ET

from .werk import Compatibility, NoWiki
from .werkv1 import load_werk_v1
from .werkv2 import load_werk_v2


def nowiki_to_markdown(description: NoWiki) -> str:
    # "inspired" by render_nowiki_werk_description
    def generator():
        for line in description.value:
            if line.startswith("LI:"):
                yield "* " + line.removeprefix("LI:")
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


def werkv1_to_werkv2(werkv1_content: str, werk_id: int) -> tuple[str, int]:
    werk = load_werk_v1(werkv1_content, werk_id).to_werk()

    def generator():
        yield "[//]: # (werk v2)"
        yield f"# {werk.title}"
        yield ""
        yield _table_entry("key", "value")
        yield _table_entry("---", "---")
        yield _table_entry("compatible", werk.compatible.value)
        yield _table_entry("version", werk.version)
        yield _table_entry("date", werk.date.isoformat())
        yield _table_entry("level", str(werk.level.value))
        yield _table_entry("class", werk.class_.value)
        yield _table_entry("component", werk.component)
        yield _table_entry("edition", werk.edition.value)
        yield ""
        if not isinstance(werk.description, NoWiki):
            raise Exception("expected nowiki werk description")
        yield nowiki_to_markdown(werk.description)

    return "\n".join(generator()), werk_id


def werkv2_to_werkv1(werkv2_content: str, werk_id: int) -> tuple[str, int]:
    werkv2 = load_werk_v2(werkv2_content, str(werk_id))
    werk = werkv2.to_werk()

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
