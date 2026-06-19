#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from pathlib import Path

from omdlib.config_api import Config, Hook


def write_admin_mail_forward(_site_name: str, site_home: Path, config: Config) -> None:
    forward = site_home / ".forward"
    value = config["ADMIN_MAIL"]
    if value:
        with open(forward, "w") as f:
            f.write(f"{value}\n")
    else:
        forward.unlink(missing_ok=True)


ADMIN_MAIL = Hook(
    name="ADMIN_MAIL",
    choices=re.compile(
        r"^([-a-zäöüÄÖÜA-Z0-9_.+%]+@[-a-zäöüÄÖÜA-Z0-9]+(\.[-a-zäöüÄÖÜA-Z0-9]+)*)?$$"
    ),
    default=lambda _edition: "",
    activation=write_admin_mail_forward,
)
