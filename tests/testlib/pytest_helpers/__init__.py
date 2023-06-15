#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
from dataclasses import dataclass

from tests.testlib.utils import is_containerized
from tests.testlib.version import version_from_env


@dataclass
class SkipIf:
    condition: bool
    reason: str


not_containerized = SkipIf(
    not (is_containerized() or os.environ.get("OVERRIDE_UNCONTAINERIZED_SKIP") == "1"),
    "Skipping test; intended for containerized runs only"
    " (use OVERRIDE_UNCONTAINERIZED_SKIP=1 at your own risk!)",
)
not_cloud_edition = SkipIf(
    not version_from_env().is_cloud_edition(), "Skipping test; intended for cloud edition only"
)
is_raw_edition = SkipIf(
    version_from_env().is_raw_edition(), "Skipping test; not intended for raw edition"
)
is_saas_edition = SkipIf(
    version_from_env().is_saas_edition(), "Skipping test; not intended for SaaS edition"
)
