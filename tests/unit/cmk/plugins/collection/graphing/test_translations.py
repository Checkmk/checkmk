#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import translations
from cmk.plugins.collection.graphing.translations import translation_apc_symmetra


def test_apc_symmetra_runtime_translation_is_not_scaled() -> None:
    """The apc_symmetra check plug-in records its runtime metric in seconds."""
    assert translation_apc_symmetra.translations["runtime"] == translations.RenameTo(
        "lifetime_remaining"
    )
