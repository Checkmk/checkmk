#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import io
import tarfile
from pathlib import Path

import pytest

from cmk.utils.crash_reporting import crash_report_registry, CrashReportStore

from cmk.gui.crash_handler import GUICrashReport
from cmk.gui.crash_reporting import pages


def test_gui_crash_report_registry() -> None:
    assert crash_report_registry["gui"] == GUICrashReport


@pytest.mark.usefixtures("request_context")
def test_gui_crash_report_get_packed() -> None:
    store = CrashReportStore()
    try:
        crash_dir = Path()
        raise ValueError("DINGELING")
    except Exception:
        crash = GUICrashReport.from_exception()
        store.save(crash)
        crash_dir = crash.crash_dir()

    tgz = pages._pack_crash_report(store.load_serialized_from_directory(crash_dir))
    buf = io.BytesIO(tgz)
    with tarfile.open(mode="r:gz", fileobj=buf) as tar:
        assert tar.getnames() == ["crash.info"]
