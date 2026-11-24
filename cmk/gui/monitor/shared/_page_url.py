#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pydantic import TypeAdapter


def encode_filter_node[N](adapter: TypeAdapter[N], filter_node: N | None) -> list[tuple[str, str]]:
    """Encode ``filter_node`` as the URL variable a monitoring page reads its filter tree from.
    Return no variables if there is no filter tree.

    Raises:
        pydantic.ValidationError: if the filter tree does not validate against ``adapter``.
    """
    if filter_node is None:
        return []
    filter_json = adapter.dump_json(filter_node).decode()
    # The nodes are plain dataclasses, only reading them back runs the model's validators.
    adapter.validate_json(filter_json)
    return [("filter", filter_json)]
