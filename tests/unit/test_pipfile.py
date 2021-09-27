#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pipfile import Pipfile  # type: ignore[import]

from tests.testlib import repo_path


def test_all_deployment_packages_pinned():

    parsed_pipfile = Pipfile.load(filename=repo_path() + "/Pipfile")
    unpinned_packages = [f"'{n}'" for n, v in parsed_pipfile.data["default"].items() if v == "*"]
    assert not unpinned_packages, (
        "The following packages are not pinned: %s. "
        "For the sake of reproducibility, all deployment packages must be pinned to a version!"
    ) % " ,".join(unpinned_packages)
