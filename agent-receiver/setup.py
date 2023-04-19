#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from setuptools import find_packages, setup

setup(
    name="agent-receiver",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["fastapi==0.79.0", "python-multipart==0.0.*"],
)
