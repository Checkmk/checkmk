#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence


def parse_ibm_svc_with_header(
    info: Sequence[Sequence[str]], dflt_header: Sequence[str]
) -> Mapping[str, Sequence[Mapping[str, str]]]:
    parsed: dict[str, list[dict[str, str]]] = {}
    header = dflt_header
    for line in info:
        if " command not found" in line:
            continue
        if line[0] in ["id", "node_id", "mdisk_id", "enclosure_id"]:
            # newer agent output provides a header line
            header = line
        else:
            parsed.setdefault(line[0], []).append(dict(zip(header[1:], line[1:])))
    return parsed
