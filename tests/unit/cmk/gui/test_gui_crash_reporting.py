#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import tarfile
from pathlib import Path

import cmk.utils.crash_reporting

import cmk.gui.crash_handler as crash_handler
import cmk.gui.crash_reporting as crash_reporting


def test_gui_crash_report_registry() -> None:
    assert cmk.utils.crash_reporting.crash_report_registry["gui"] == crash_handler.GUICrashReport


def test_gui_crash_report_get_packed(request_context) -> None:
    store = crash_handler.CrashReportStore()
    try:
        crash_dir = Path()
        raise ValueError("DINGELING")
    except Exception:
        crash = crash_handler.GUICrashReport.from_exception()
        store.save(crash)
        crash_dir = crash.crash_dir()

    tgz = crash_reporting._pack_crash_report(store.load_serialized_from_directory(crash_dir))
    buf = io.BytesIO(tgz)
    with tarfile.open(mode="r:gz", fileobj=buf) as tar:
        assert tar.getnames() == ["crash.info"]
