#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Restore a cmk site backup, update to a new version, activate changes, and create a new backup.

Usage (run as a module from the repo root so that tests.testlib is importable):
    python -m tests.update.update_backups <backup_path> <output_path> <version_edition>

    backup_path:     Path of the backup to restore.
    output_path:     Path of the new backup to save.
    version_edition: Version and edition for the update, e.g. '2.5.0.ultimate'.

Example:
    python -m tests.update.update_backups \\
        /backups/mysite.tar.gz /backups/mysite_new.tar.gz 2.5.0.ultimate
"""

import argparse
import logging
import tarfile
from pathlib import Path

from tests.testlib.site import SiteFactory
from tests.testlib.version import (
    CMKEdition,
    CMKPackageInfo,
    CMKVersion,
    get_min_version,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _get_site_and_omd_version_from_backup(backup_path: Path) -> tuple[str, str]:
    """Extract site name and omd version directory from a backup archive.

    Searches for the '<site-name>/version' symlink entry anywhere in the archive.
    Returns (site_name, omd_version), e.g. ('mysite', '2.5.0.ultimate').
    """
    with tarfile.open(backup_path) as tar:
        for entry in tar:
            file_path = Path(entry.name)
            if file_path.name == "version" and entry.linkname:
                sitename = file_path.parent
                return str(sitename), str(Path(entry.linkname).name)
    raise RuntimeError(f"Could not find '<site>/version' symlink in backup: {backup_path}")


def _make_cmk_package_info(omd_version: str) -> CMKPackageInfo:
    """Build a CMKPackageInfo from an omd version directory name.

    Directory-name structure: '<version>.<edition>'."""
    version_str, edition_str = omd_version.rsplit(".", 1)
    return CMKPackageInfo(
        CMKVersion(version_str),
        CMKEdition.edition_from_text(edition_str),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Restore a Checkmk backup, update the site to a new version, "
            "activate changes, and create a new backup."
        )
    )
    parser.add_argument(
        "backup_path",
        type=Path,
        help="Full path of the backup to restore. e.g.: '/backups/mysite.tar.gz'.",
    )
    parser.add_argument(
        "output_path",
        type=Path,
        help="Full path of the new backup to save. e.g.: '/backups/mysite_new.tar.gz'.",
    )
    parser.add_argument(
        "to_version_edition",
        help="Version and edition of the updated site and new backup in the format "
        "'<version>.<edition>'.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    backup_path: Path = args.backup_path
    output_path: Path = args.output_path
    to_version_edition: str = args.to_version_edition

    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    site_name, base_omd_version = _get_site_and_omd_version_from_backup(backup_path)
    logger.info("Detected site '%s' (version: %s)", site_name, base_omd_version)

    base_package = _make_cmk_package_info(base_omd_version)
    target_package = _make_cmk_package_info(to_version_edition)

    # Restore the site from backup using the SiteFactory helper
    base_site_factory = SiteFactory(package=base_package)
    base_site = base_site_factory.restore_site_from_backup(backup_path, site_name)

    # Update to the target version using the SiteFactory helper.
    # start_site_after_update=False so that we activate changes explicitly below.
    target_site_factory = SiteFactory(package=target_package)
    target_site = target_site_factory.update_as_site_user(
        base_site,
        target_package,
        min_version=get_min_version(),
        start_site_after_update=False,
    )

    # Activate changes via the site's openapi session
    target_site.openapi.changes.activate_and_wait_for_completion()

    target_site_factory.backup_site(target_site.id, output_path, no_past=True)
    logger.info("Done.")


if __name__ == "__main__":
    main()
