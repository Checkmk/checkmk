#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Iterator

from .markup import nowiki_to_markdown
from .parse import parse_werk_v1


def _table_entry(key: str, value: str) -> str:
    return f"{key} | {value}"


def werkv1_metadata_to_markdown_werk_metadata(metadata: dict[str, str]) -> dict[str, str]:
    metadata = metadata.copy()
    metadata.pop("knowledge", None)  # removed field
    metadata.pop("state", None)  # removed field
    metadata.pop("targetversion", None)  # removed field

    match metadata.get("compatible"):
        case None:
            pass
        case "compat":
            metadata["compatible"] = "yes"
        case "incomp":
            metadata["compatible"] = "no"
        case value:
            raise ValueError(
                f"compatible of werkv1 has to be either 'compat' or 'incomp', got {value!r}"
            )

    if (date := metadata.get("date")) is not None:
        metadata["date"] = datetime.datetime.fromtimestamp(float(date), tz=datetime.UTC).isoformat()

    return metadata


def werkv1_to_werkv2(werkv1_content: str, werk_id: int) -> tuple[str, int]:
    # try to keep errors in place, so the validation of werkv2 will show errors in werkv1
    parsed = parse_werk_v1(werkv1_content, werk_id)
    metadata = werkv1_metadata_to_markdown_werk_metadata(parsed.metadata)
    metadata.pop("id", None)  # is the filename

    def generator() -> Iterator[str]:
        yield "[//]: # (werk v2)"
        if (title := metadata.pop("title", None)) is not None:
            yield f"# {title}"
        yield ""
        yield _table_entry("key", "value")
        yield _table_entry("---", "---")
        if (compatible := metadata.pop("compatible", None)) is not None:
            yield _table_entry("compatible", compatible)
        if (version := metadata.pop("version", None)) is not None:
            yield _table_entry("version", version)
        if (date := metadata.pop("date", None)) is not None:
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
