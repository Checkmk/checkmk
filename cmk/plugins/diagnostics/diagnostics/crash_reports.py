#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import tarfile
from collections.abc import Iterable
from pathlib import PurePosixPath

from cmk.crash import make_crash_report_base_path
from cmk.diagnostics.internal import (
    CollectContext,
    DiagnosticsPlugin,
    DumpItem,
    GeneratedContent,
    Help,
    Sensitivity,
)
from cmk.plugins.diagnostics.lib.topics import TOPIC_CRASH_REPORTS


def _collect_latest_crash_reports(context: CollectContext) -> Iterable[DumpItem]:
    crashes_path = make_crash_report_base_path(context.omd_root)
    arcbase = PurePosixPath(crashes_path.relative_to(context.omd_root))
    for category in crashes_path.glob("*"):
        sorted_dumps = sorted(
            (p for p in category.glob("*") if p.is_dir()),
            key=lambda path: int(path.stat().st_mtime),
        )
        if not sorted_dumps:
            continue

        # Determine the latest dump of that category and pack it into a
        # .tar.gz, so it can easily be uploaded to https://crash.checkmk.com/
        dumpfile_path = sorted_dumps[-1]
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            for file in dumpfile_path.iterdir():
                tar.add(file, arcname=str(file.relative_to(dumpfile_path)))

        yield DumpItem(
            arcbase / category.name / f"{dumpfile_path.name}.tar.gz",
            GeneratedContent(buffer.getvalue()),
        )


diagnostics_plugin_latest_crash_reports = DiagnosticsPlugin(
    name="latest_crash_reports",
    description=Help("The latest crash dumps of each type as found in var/check_mk/crashes"),
    sensitivity=Sensitivity.MEDIUM,
    topic=TOPIC_CRASH_REPORTS,
    handler=_collect_latest_crash_reports,
)
