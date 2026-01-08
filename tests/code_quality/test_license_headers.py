#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import logging
import os
import re
from collections.abc import Sequence

from tests.testlib.common.repo import repo_path

LOGGER = logging.getLogger()

GPL = r"""# Copyright \(C\) \d{4} Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk \(https://checkmk.com\). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package."""

ENTERPRISE = r"""# Copyright \(C\) \d{4} Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk \(https://checkmk.com\). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package."""

ENTERPRISE_HEADER = re.compile(rf"#!/usr/bin/env python3\n{ENTERPRISE}")
ENTERPRISE_HEADER_NO_SHEBANG = re.compile(rf"{ENTERPRISE}")
ENTERPRISE_HEADER_CODING = re.compile(
    rf"""#!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
{ENTERPRISE}"""
)

ENTERPRISE_HEADER_ALERT_HANDLERS = re.compile(
    rf"""#!/usr/bin/env python3
# .+

{ENTERPRISE}"""
)


OMD_HEADER = re.compile(rf"#!/omd/versions/###OMD_VERSION###/bin/python3\n{GPL}")

GPL_HEADER = re.compile(rf"#!/usr/bin/env (python3|-S python3 -P)\n{GPL}")
GPL_HEADER_NO_SHEBANG = re.compile(rf"{GPL}")

GPL_HEADER_NOTIFICATION = re.compile(
    rf"""#!/usr/bin/env python3
# .+(\n# Bulk: (yes|no))?

{GPL}
"""
)


ignored_files = [
    "cmk/notification_plugins/ilert.py",
    "cmk/notification_plugins/signl4.py",
    "notifications/ilert",
    "notifications/signl4",
    "omd/packages/Python/pip",
    "tests/integration_redfish/mockup-server/redfishMockupServer.py",
    "tests/integration_redfish/mockup-server/rfSsdpServer.py",
]

# Similar logic to our partial GitHub sync approach. Both select enterprise files or directories
# based on their name.
enterprise_names = [
    "non-free",
    "nonfree",
    "pro",
    "ultimate",
    "ultimatemt",
    "cloud",
]


def needs_enterprise_license(path: str) -> bool:
    parts = path.split("/")
    if any(p for p in enterprise_names if p in parts):
        return True

    return False


def get_file_header(path: str, length: int = 30) -> str:
    with open(path) as file:
        head = [file.readline() for x in range(length)]
        return "".join(head)


def check_for_license_header_violation(rel_path, abs_path):
    if rel_path.startswith("non-free/packages/cmk-update-agent/cmk_update_agent.py"):
        if not ENTERPRISE_HEADER_CODING.match(get_file_header(abs_path, length=5)):
            yield "enterprise header with coding not matching", rel_path
    elif rel_path.startswith("omd/non-free/packages/alert-handling/alert_handlers/"):
        if not ENTERPRISE_HEADER_ALERT_HANDLERS.match(get_file_header(abs_path, length=8)):
            yield "enterprise header with alert handler not matching", rel_path
    elif needs_enterprise_license(rel_path):
        header = get_file_header(abs_path, length=4)
        if not (ENTERPRISE_HEADER.match(header) or ENTERPRISE_HEADER_NO_SHEBANG.match(header)):
            yield "enterprise header not matching", rel_path
    elif rel_path == "omd/packages/omd/omd.bin":
        if not OMD_HEADER.match(get_file_header(abs_path, length=23)):
            yield "omd gpl license header not matching", rel_path
    elif rel_path.startswith("notifications/"):
        if not GPL_HEADER_NOTIFICATION.match(get_file_header(abs_path, length=10)):
            yield "gpl header with notification not matching", rel_path
    else:
        header = get_file_header(abs_path, length=4)
        if not (GPL_HEADER.match(header) or GPL_HEADER_NO_SHEBANG.match(header)):
            yield "gpl header not matching", rel_path


def test_license_headers(python_files: Sequence[str]) -> None:
    files_checked = []
    files_ignored = []

    def generator():
        for path in python_files:
            abs_path = os.path.realpath(path)
            rel_path = os.path.relpath(abs_path, repo_path())

            if rel_path in ignored_files:
                files_ignored.append(rel_path)
                continue

            files_checked.append(rel_path)
            yield from check_for_license_header_violation(rel_path, abs_path)

    LOGGER.info("Scanning %d files", len(python_files))
    violations = sorted(list(generator()))
    violations_formatted = "\n".join(f"{ident}: {path}" for (ident, path) in violations)

    LOGGER.info("ignored: %d", len(files_ignored))
    LOGGER.info("checked: %d", len(files_checked))

    assert not violations, (
        f"The following license header violations were detected:\n{violations_formatted}"
    )
