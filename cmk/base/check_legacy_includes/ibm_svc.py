#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# tyxpe: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
# pylint: disable=no-else-continue


def parse_ibm_svc_with_header(info, dflt_header):
    parsed: dict = {}
    header = dflt_header
    for line in info:
        if " command not found" in line:
            continue
        elif line[0] in ["id", "node_id", "mdisk_id", "enclosure_id"]:
            # newer agent output provides a header line
            header = line
        else:
            parsed.setdefault(line[0], []).append(dict(zip(header[1:], line[1:])))
    return parsed
