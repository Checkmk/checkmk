#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.mkp_tool import PackageOperationCallbacks, PackagePart

from .rule_packs import (
    install_packaged_rule_packs,
    release_packaged_rule_packs,
    uninstall_packaged_rule_packs,
)


def mkp_callbacks() -> Mapping[PackagePart, PackageOperationCallbacks]:
    return {
        PackagePart.EC_RULE_PACKS: PackageOperationCallbacks(
            install=install_packaged_rule_packs,
            uninstall=uninstall_packaged_rule_packs,
            release=release_packaged_rule_packs,
        ),
    }
