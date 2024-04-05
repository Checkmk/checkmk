#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import re
from collections.abc import Sequence

from tests.testlib import repo_path

LOGGER = logging.getLogger()

ENTERPRISE_HEADER = re.compile(
    r"""#!/usr/bin/env python3
# Copyright \(C\) \d{4} Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk \(https://checkmk.com\). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package."""
)
ENTERPRISE_HEADER_CODING = re.compile(
    r"""#!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
# Copyright \(C\) \d{4} Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk \(https://checkmk.com\). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package."""
)

ENTERPRISE_HEADER_ALERT_HANDLERS = re.compile(
    r"""#!/usr/bin/env python3
# .+

# Copyright \(C\) \d{4} Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk \(https://checkmk.com\). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package."""
)


OMD_HEADER = re.compile(
    r"""(#!/usr/bin/env python3|!/omd/versions/###OMD_VERSION###/bin/python3)(\n# vim:.+)?
#
#       U  ___ u  __  __   ____
#        \/"_ \/U|' \/ '|u|  _"\
#        | | | |\| |\/| |/| | | |
#    .-,_| |_| | | |  | |U| |_| |\
#     \_\)-\___/  |_|  |_| |____/ u
#          \\   <<,-,,-.   |||_
#         \(__\)   \(./  \.\) \(__\)_\)
#
# This file is part of OMD - The Open Monitoring Distribution.
# The official homepage is at <http://omdistro.org>.
#
# OMD  is  free software;  you  can  redistribute it  and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the  Free Software  Foundation  in  version 2.  OMD  is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
""",
    re.MULTILINE,
)

GPL_HEADER = re.compile(
    r"""#!/usr/bin/env python3
# Copyright \(C\) \d{4} Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk \(https://checkmk.com\). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
""",
    re.MULTILINE,
)

GPL_HEADER_CODING = re.compile(
    r"""#\!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
# Copyright \(C\) \d{4} Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk \(https://checkmk.com\). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
""",
    re.MULTILINE,
)

GPL_HEADER_NOTIFICATION = re.compile(
    r"""#!/usr/bin/env python3
# .+(\n# Bulk: (yes|no))?

# Copyright \(C\) \d{4} Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk \(https://checkmk.com\). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
""",
    re.MULTILINE,
)


ignored_files = [
    "cmk/notification_plugins/ilert.py",
    "notifications/ilert",
    "cmk/notification_plugins/signl4.py",
    "notifications/signl4",
    "omd/packages/maintenance/merge-crontabs",
    "omd/packages/Python/pip",
]

# Similar logic to our partial GitHub sync approach. Both select enterprise files or directories
# based on their name.
enterprise_names = [
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


def check_for_license_header_violation(rel_path, abs_path):  # pylint: disable=too-many-branches
    if rel_path.startswith("non-free/cmk-update-agent/"):
        if not ENTERPRISE_HEADER_CODING.match(get_file_header(abs_path, length=5)):
            yield "enterpsie header with coding not matching", rel_path
    elif rel_path.startswith("omd/packages/enterprise/alert_handlers/"):
        if not ENTERPRISE_HEADER_ALERT_HANDLERS.match(get_file_header(abs_path, length=8)):
            yield "enterpsie header with coding not matching", rel_path
    elif needs_enterprise_license(rel_path):
        if not ENTERPRISE_HEADER.match(get_file_header(abs_path, length=4)):
            yield "enterprise header not matching", rel_path
    elif rel_path.startswith("omd/packages/omd/"):
        if not OMD_HEADER.match(get_file_header(abs_path, length=23)):
            yield "omd gpl license header not matching", rel_path
    elif rel_path.startswith("tests/agent-plugin-unit/") or rel_path.startswith("agents/plugins/"):
        if not GPL_HEADER_CODING.match(get_file_header(abs_path, length=5)):
            yield "gpl header with coding not matching", rel_path
    elif rel_path.startswith("notifications/"):
        if not GPL_HEADER_NOTIFICATION.match(get_file_header(abs_path, length=10)):
            yield "gpl header with notification not matching", rel_path
    else:
        if not GPL_HEADER.match(get_file_header(abs_path, length=4)):
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

    assert (
        not violations
    ), f"The following license header violations were detected:\n{violations_formatted}"
