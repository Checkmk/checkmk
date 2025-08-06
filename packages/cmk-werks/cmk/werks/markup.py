#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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


def markdown_to_html(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["tables", "fenced_code"],
        output_format="html",
    )
