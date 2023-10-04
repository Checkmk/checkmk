#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys

repo_path = os.path.dirname(os.path.dirname(__file__))


def add_cmk_metrics_package() -> None:
    cmk_metrics_package = os.path.join(repo_path, "cmk_metrics")
    sys.path.insert(0, cmk_metrics_package)


add_cmk_metrics_package()
