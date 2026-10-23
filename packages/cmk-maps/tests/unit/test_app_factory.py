#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The daemon's OpenAPI schema has to be buildable outside a site.

The SPA's daemon types are generated from ``create_app().openapi()`` in a build
action, which runs with no OMD site around it and must produce the same bytes on
every machine. These tests pin that, and pin that the schema the typegen sees is
the one the daemon actually serves.
"""

import json
import os
import subprocess
import sys

from cmk.maps.backend.app import create_app
from cmk.maps.backend.main import app

# Run in a fresh interpreter: the assertions are about what importing the module
# does, which the test process has already done by the time a test body runs.
_DUMP_SCHEMA = """
import json
import logging
import sys

from cmk.maps.backend.app import create_app

assert not logging.getLogger().handlers, "importing the factory configured the root logger"
assert "cmk.maps.backend.main" not in sys.modules, "the factory pulled in the runtime module"

print(json.dumps(create_app().openapi(), sort_keys=True))
"""


def _schema_from_subprocess(**env_overrides: str) -> object:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"OMD_ROOT", "OMD_SITE", "CHECKMK_OMD_ROOT"}
    }
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    env.update(env_overrides)

    completed = subprocess.run(
        [sys.executable, "-c", _DUMP_SCHEMA],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_schema_builds_without_a_site_environment() -> None:
    schema = _schema_from_subprocess()
    assert isinstance(schema, dict)
    assert schema["paths"], "the dumped schema has no routes"


def test_schema_is_independent_of_the_environment() -> None:
    # Operational tunables are read from the environment at import time; none of
    # them may reach the schema, or the generated types would differ per site.
    assert _schema_from_subprocess() == _schema_from_subprocess(
        OMD_ROOT="/omd/sites/pinned",
        OMD_SITE="pinned",
        MAPS_LOG_LEVEL="DEBUG",
        MAPS_STATE_REFRESH_INTERVAL="99",
        MAPS_FOLDER_SEARCH_MAX_SERVICES="1",
    )


def test_generated_schema_matches_the_served_application() -> None:
    # ``main.app`` is what a worker serves; the generated types must describe
    # that application, not a stripped-down variant of it.
    assert app.openapi() == create_app().openapi()
