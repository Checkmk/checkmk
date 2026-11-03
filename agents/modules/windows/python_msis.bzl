# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The python.org per-feature MSIs the Windows agent's Python is built from."""

# In extraction order. Each names the @python_msi_<feature> repo that
# //bazel/extensions:python_cab_repositories.bzl declares and pins.
PYTHON_MSI_FEATURES = ["ucrt", "core", "exe", "lib", "pip"]
