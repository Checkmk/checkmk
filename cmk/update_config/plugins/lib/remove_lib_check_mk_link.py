#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path

from cmk.mkp_tool import Installer, PackagePart


def convert_manifests(manifests_path: Path, logger: Logger, *, dry_run: bool) -> None:
    installer = Installer(manifests_path)
    manifests = [m for m in installer.get_installed_manifests() if m.files.get(PackagePart.LIB)]

    if dry_run:
        # At least we could read them.
        return

    for manifest in manifests:
        # rewrite the manifest to ensure that files in lib/check_mk are
        # re-represented as files in lib/python3/cmk
        try:
            installer.add_installed_manifest(manifest)
        except Exception:
            logger.warning(
                "[%s %s] failed to rewrite manifest of installed package"
                % (manifest.name, manifest.version)
            )
