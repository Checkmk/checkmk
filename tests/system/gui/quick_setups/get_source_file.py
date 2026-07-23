#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path
from types import ModuleType

from tests.testlib.site import Site


def get_source_file(test_site: Site, module: ModuleType) -> Path:
    return Path(
        test_site.check_output(
            ["python3", "-c", f"import {module.__name__} as m; print(m.__file__)"]
        ).strip()
    )
