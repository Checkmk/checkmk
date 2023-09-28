#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import tests.testlib as testlib


def test_check_plugin_header() -> None:
    for plugin in (
        p
        for p in (testlib.repo_path() / "cmk/base/legacy_checks").iterdir()
        if p.name != "__pycache__"
    ):
        with plugin.open() as handle:
            shebang = handle.readline().strip()

        assert shebang == "#!/usr/bin/env python3", (
            f"Plugin '{plugin.name}' has wrong shebang '{shebang}'",
        )
