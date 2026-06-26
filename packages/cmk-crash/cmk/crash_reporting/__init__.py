#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Full crash-reporting library: packaging, payload construction, and (Epic 2) upload.

Houses the tar packaging helper and submit-payload construction extracted from
``cmk/gui/crash_reporting/pages.py`` so future consumers (Epic 2's CLI, any
other flow) can reuse it. The batch upload loop and CLI entrypoint
(``cmk-upload-crashes``) land in Epic 2.
"""

from ._packaging import crash_report_submit_payload, pack_crash_report

__all__ = [
    "crash_report_submit_payload",
    "pack_crash_report",
]
