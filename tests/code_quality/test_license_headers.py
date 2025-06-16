#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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

GPL_HEADER_CODING = re.compile(
    rf"""#\!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
{GPL}
"""
)

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
    "cloud",
    "enterprise",
    "managed",
    "saas",
    "cee",
    "cme",
    "cce",
    "cse",
    "cmc",
    "cee.py",
    "cme.py",
    "cce.py",
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
    if rel_path.startswith("non-free/packages/cmk-update-agent/"):
        if not ENTERPRISE_HEADER_CODING.match(get_file_header(abs_path, length=5)):
            yield "enterprise header with coding not matching", rel_path
    elif rel_path.startswith("omd/packages/enterprise/alert_handlers/"):
        if not ENTERPRISE_HEADER_ALERT_HANDLERS.match(get_file_header(abs_path, length=8)):
            yield "enterprise header with alert handler not matching", rel_path
    elif needs_enterprise_license(rel_path):
        if not ENTERPRISE_HEADER.match(get_file_header(abs_path, length=4)):
            yield "enterprise header not matching", rel_path
    elif rel_path == "omd/packages/omd/omd.bin":
        if not OMD_HEADER.match(get_file_header(abs_path, length=23)):
            yield "omd gpl license header not matching", rel_path
    elif rel_path.startswith("tests/agent-plugin-unit/") or rel_path.startswith("agents/plugins/"):
        if not GPL_HEADER_CODING.match(get_file_header(abs_path, length=5)):
            yield "gpl header with coding not matching", rel_path
    elif rel_path.startswith("notifications/"):
        if not GPL_HEADER_NOTIFICATION.match(get_file_header(abs_path, length=10)):
            yield "gpl header with notification not matching", rel_path
    elif not GPL_HEADER.match(get_file_header(abs_path, length=4)):
        yield "gpl header not matching", rel_path


def test_license_headers(python_files: Sequence[str]) -> None:
    def generator():
        for path in python_files:
            abs_path = os.path.realpath(path)
            rel_path = os.path.relpath(abs_path, repo_path())

            if rel_path in ignored_files:
                continue

            yield from check_for_license_header_violation(rel_path, abs_path)

    violations = sorted(list(generator()))
    violations_formatted = "\n".join(f"{ident}: {path}" for (ident, path) in violations)

    assert not violations, (
        f"The following license header violations were detected:\n{violations_formatted}"
    )
