#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Packaging and submit-payload construction for crash reports.

Shared by the GUI manual-submit flow and (Epic 2) the automatic uploader, so the
tar.gz layout and the submit field structure live in one place instead of being
inlined in the GUI."""

import base64
import io
import tarfile
from collections.abc import Mapping


def pack_crash_report(serialized_crash_report: Mapping[str, bytes | None]) -> bytes:
    """Returns a byte string representing the crash report in tar archive format"""
    buf = io.BytesIO()
    with tarfile.open(mode="w:gz", fileobj=buf) as tar:
        for key, content in serialized_crash_report.items():
            if content is None:
                continue

            tar_info = tarfile.TarInfo(name="crash.info" if key == "crash_info" else key)
            tar_info.size = len(content)

            tar.addfile(tar_info, io.BytesIO(content))

    return buf.getvalue()


def crash_report_submit_payload(
    *,
    name: str,
    mail: str,
    serialized_crash_report: Mapping[str, bytes | None],
) -> list[tuple[str, int | str | None]]:
    """Build the field list for a crash-report submit POST.

    The crash report is packed into a tar.gz and base64-encoded as the
    ``crashdump`` field. Callers encode this list for their transport (the GUI
    url-encodes it; the uploader posts it). The value type matches the HTTP
    form-variable shape so the result can be passed straight to url-encoders."""
    return [
        ("name", name),
        ("mail", mail),
        (
            "crashdump",
            base64.b64encode(pack_crash_report(serialized_crash_report)).decode("ascii"),
        ),
    ]
