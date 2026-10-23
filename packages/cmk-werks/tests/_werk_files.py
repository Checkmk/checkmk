#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def werk_text(
    *,
    title: str = "A werk title",
    version: str | None = "2.5.0",
    edition: str = "community",
    component: str = "core",
    compatible: str = "yes",
    werk_class: str = "fix",
) -> str:
    version_row = "" if version is None else f"version | {version}\n"
    return f"""[//]: # (werk v3)
# {title}

key | value
--- | ---
date | 2026-01-01T00:00:00+00:00
{version_row}class | {werk_class}
edition | {edition}
component | {component}
level | 1
compatible | {compatible}

A description.
"""
