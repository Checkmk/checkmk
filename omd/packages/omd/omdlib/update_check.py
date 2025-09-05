#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import sys
from pathlib import Path

from omdlib.dialog import dialog_menu, dialog_yesno
from omdlib.site_paths import SitePaths
from omdlib.system_apache import is_apache_hook_up_to_date
from omdlib.utils import exec_other_omd
from omdlib.version import omd_versions

from cmk.ccc.version import Version, versions_compatible, VersionsIncompatible


def _omd_to_check_mk_version(omd_version: str) -> Version:
    """
    >>> f = _omd_to_check_mk_version
    >>> f("2.0.0p3.cee")
    Version(_BaseVersion(major=2, minor=0, sub=0), _Release(release_type=ReleaseType.p, value=3), _ReleaseCandidate(value=None), _ReleaseMeta(value=None))
    >>> f("1.6.0p3.cee.demo")
    Version(_BaseVersion(major=1, minor=6, sub=0), _Release(release_type=ReleaseType.p, value=3), _ReleaseCandidate(value=None), _ReleaseMeta(value=None))
    >>> f("2.0.0p3.cee")
    Version(_BaseVersion(major=2, minor=0, sub=0), _Release(release_type=ReleaseType.p, value=3), _ReleaseCandidate(value=None), _ReleaseMeta(value=None))
    >>> f("2021.12.13.cee")
    Version(None, _Release(release_type=ReleaseType.daily, value=BuildDate(year=2021, month=12, day=13)), _ReleaseCandidate(value=None), _ReleaseMeta(value=None))
    """
    parts = omd_version.split(".")

    # Before we had the free edition, we had versions like ".cee.demo". Since we deal with old
    # versions, we need to care about this.
    if parts[-1] == "demo":
        del parts[-1]

    # Strip the edition suffix away
    del parts[-1]

    return Version.from_str(".".join(parts))


def check_update_possible(
    from_edition: str,
    to_edition: str,
    from_version: str,
    to_version: str,
    site_name: str,
    force: bool,
    versions_path: Path = Path("/omd/versions/"),
) -> None:
    # source and target are identical if 'omd update' is called
    # from within a site. In that case we make the user choose
    # the target version explicitely and the re-exec the bin/omd
    # of the target version he has choosen.
    if from_version == to_version:
        possible_versions = [v for v in omd_versions(versions_path) if v != from_version]
        possible_versions.sort(reverse=True)
        if len(possible_versions) == 0:
            sys.exit("There is no other OMD version to update to.")
        elif len(possible_versions) == 1:
            to_version = possible_versions[0]
        else:
            success, to_version = dialog_menu(
                "Choose target version",
                "Please choose the version this site should be updated to",
                [(v, "Version %s" % v) for v in possible_versions],
                possible_versions[0],
                "Update now",
                "Cancel",
            )
            if not success:
                sys.exit("Aborted.")
        exec_other_omd(to_version)

    cmk_from_version = _omd_to_check_mk_version(from_version)
    cmk_to_version = _omd_to_check_mk_version(to_version)
    if (
        isinstance(
            compatibility := versions_compatible(cmk_from_version, cmk_to_version),
            VersionsIncompatible,
        )
        and not force
    ):
        sys.exit(
            f"ERROR: You are trying to update from {from_version} to {to_version} which is not "
            f"supported. Reason: {compatibility}\n\n"
            "* Major downgrades are not supported\n"
            "* Major version updates need to be done step by step.\n\n"
            "If you are really sure about what you are doing, you can still do the "
            "update with '-f'.\n"
            "You can execute the command in the following way:\n"
            "'omd -f update' or 'omd --force update'"
            "But you will be on your own from there."
        )

    # This line is reached, if the version of the OMD binary (the target)
    # is different from the current version of the site.
    if not force and not dialog_yesno(
        "You are going to update the site %s from version %s to version %s. "
        "This will include updating all of your configuration files and merging "
        "changes in the default files with changes made by you. In case of conflicts "
        "your help will be needed." % (site_name, from_version, to_version),
        "Update!",
        "Abort",
    ):
        sys.exit("Aborted.")

    # In case the user changes the installed Checkmk Edition during update let the
    # user confirm this step.
    if from_edition == "managed" and to_edition != "managed" and not force:
        sys.exit(f"ERROR: Updating from {from_edition} to {to_edition} is not possible. Aborted.")

    if (
        from_edition != to_edition
        and not force
        and not dialog_yesno(
            text=f"You are updating from {from_edition.title()} Edition to {to_edition.title()} Edition. Is this intended?",
            default_no=True,
        )
    ):
        sys.exit("Aborted.")

    try:
        hook_up_to_date = is_apache_hook_up_to_date(SitePaths.from_site_name(site_name).apache_conf)
    except PermissionError:
        # In case the hook can not be read, assume the hook needs to be updated
        hook_up_to_date = False

    if (
        not hook_up_to_date
        and not force
        and not dialog_yesno(
            "This update requires additional actions: The system apache configuration has changed "
            "with the new version and needs to be updated.\n\n"
            f"You will have to execute 'omd update-apache-config {site_name}' as root user.\n\n"
            "Please do it right after 'omd update' to prevent inconsistencies. Have a look at "
            "#14281 for further information.\n\n"
            "Do you want to proceed?"
        )
    ):
        sys.exit("Aborted.")
