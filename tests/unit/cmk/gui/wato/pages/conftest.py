#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterator

import pytest

import cmk.utils.paths
from cmk.gui.htmllib.html import _load_vue_manifest


@pytest.fixture(name="frontend_vue_manifest")
def fixture_frontend_vue_manifest() -> Iterator[None]:
    base = cmk.utils.paths.web_dir / "htdocs/cmk-frontend-vue"
    base.mkdir(parents=True, exist_ok=True)
    (base / ".manifest.json").write_text(
        json.dumps(
            {
                "src/main.ts": {"file": "main.js"},
                "src/nav_sidebar.ts": {"file": "nav_sidebar.js"},
                "src/stage1.ts": {"file": "stage1.js"},
            }
        )
    )
    _load_vue_manifest.cache_clear()
    yield
    _load_vue_manifest.cache_clear()
