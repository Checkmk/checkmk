#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from collections.abc import Iterable, Sequence
from pathlib import PurePosixPath

from cmk.diagnostics.internal import (
    CollectContext,
    CollectInfo,
    DiagnosticsPlugin,
    DumpItem,
    GeneratedContent,
    Help,
    Sensitivity,
)
from cmk.plugins.diagnostics.lib.topics import TOPIC_EXTENSIONS


def _mkp_output(context: CollectContext, command: Sequence[str]) -> str:
    try:
        return subprocess.check_output(list(command), text=True)
    except subprocess.CalledProcessError as e:
        # CollectLogger has no .exception(); the plugin reports the failed
        # command at error level in the dump's console log.
        context.log.error(str(e.stderr))  # noqa: TRY400
        return "{}"


def _collect_mkp_inventory(context: CollectContext) -> Iterable[DumpItem]:
    empty = True
    for filename, command in (
        ("mkp_find_all.json", ["mkp", "find", "--all", "--json"]),
        ("mkp_show_all.json", ["mkp", "show-all", "--json"]),
        ("mkp_list.json", ["mkp", "list", "--json"]),
    ):
        if contents := _mkp_output(context, command):
            empty = False
            yield DumpItem(PurePosixPath(filename), GeneratedContent(contents.encode()))
    if empty:
        raise CollectInfo("No data")


diagnostics_plugin_mkp_inventory = DiagnosticsPlugin(
    name="mkp_inventory",
    description=Help(
        "Information about installed MKPs and unpackaged files below the site's local hierarchy"
    ),
    sensitivity=Sensitivity.LOW,
    topic=TOPIC_EXTENSIONS,
    handler=_collect_mkp_inventory,
)
