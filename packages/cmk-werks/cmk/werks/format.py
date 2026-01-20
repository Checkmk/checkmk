#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

from .load import load_werk_v2
from .markup import markdown_to_nowiki
from .models import Compatibility
from .parse import WerkV2ParseResult, WerkV3ParseResult


def format_as_werk_v1(parsed: WerkV2ParseResult) -> str:
    werk = load_werk_v2(parsed)

    def generator() -> Iterator[str]:
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
        yield markdown_to_nowiki(werk.description)

    return "\n".join(generator())


def format_as_werk_v2(werk: WerkV2ParseResult | WerkV3ParseResult) -> str:
    metadata = werk.metadata.copy()

    metadata.pop("id")
    title = metadata.pop("title")

    len_key = max(len(key) for key in metadata.keys())

    def _content() -> Iterator[str]:
        yield "[//]: # (werk v2)"
        yield f"# {title}"
        yield ""
        yield f"{'key': <{len_key}} | value"
        yield f"{'':-<{len_key}} | ---"
        for key, value in metadata.items():
            yield f"{key: <{len_key}} | {value}"
        yield ""
        yield werk.description

    return "\n".join(_content())
