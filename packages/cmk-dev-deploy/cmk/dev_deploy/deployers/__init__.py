# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Deployer modules for cmk-dev-deploy.

This subpackage groups all deployer implementations:

- ``wheel_deployer``: wheel deployment (direct copy + .dist-info + edition filter + targeted deploy)
- ``config_deployer``: config/data file deployment (agents, notifications, etc.)
- ``bazel_builder``: Bazel build + artifact installation (C++, Rust, Vue)
"""
