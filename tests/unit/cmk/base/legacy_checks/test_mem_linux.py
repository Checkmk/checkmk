#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.mem_linux import check_mem_linux


def test_check_mem_linux_without_linux_memory_fields() -> None:
    # Crash group 4589: after discovery the agent delivered a memory section
    # without the Linux specific fields (only totals and free values).
    section = {
        "MemFree": 2363887616,
        "MemTotal": 8588939264,
        "PageFree": 2578345984,
        "PageTotal": 9931116544,
        "SwapFree": 214458368,
        "SwapTotal": 1342177280,
    }

    assert list(check_mem_linux(None, {}, section)) == [
        (3, "Memory information is missing: Buffers, Cached, Dirty"),
    ]
