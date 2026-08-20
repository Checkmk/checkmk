#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Validate that edition-scoped plugin packages are present or absent as expected.

Each test covers one plugin family and asserts:
  - presence in the editions that carry the corresponding license feature
  - absence in editions that do not
"""

from dataclasses import dataclass
from pathlib import Path
from typing import override

import pytest

from tests.testlib.common.repo import repo_path
from tests.testlib.common.utils2 import check_output
from tests.testlib.version import TypeCMKEdition

_ULTIMATE_AND_HIGHER = frozenset(
    {
        TypeCMKEdition.CLOUD.long,
        TypeCMKEdition.ULTIMATE.long,
        TypeCMKEdition.ULTIMATEMT.long,
    }
)
_PRO_AND_LOWER = frozenset(
    {
        TypeCMKEdition.COMMUNITY.long,
        TypeCMKEdition.PRO.long,
    }
)


@dataclass
class PluginDetails:
    name: str
    target: str

    @override
    def __str__(self) -> str:
        return self.name


_CMK_PLUGINS = [
    pytest.param(
        aze := PluginDetails(
            "azure_v2_extended", "//non-free/packages/cmk-plugins-nonfree:pkg_tar-azure_v2_extended"
        ),
        id=aze.name,
    )
]


def _stdout_bazel_cquery(
    edition: str, plugin_target: str, dir_repo_path: Path = repo_path()
) -> str:
    dir_non_free_packages = dir_repo_path / "non-free" / "packages"
    if dir_non_free_packages.exists():
        return check_output(
            [
                "bazel",
                "cquery",
                "--ui_event_filters=-WARNING",
                "--noshow_progress",
                f"--cmk_edition={edition}",
                f"somepath(//omd:complete_install, {plugin_target})",
            ],
            cwd=dir_repo_path.as_posix(),
        )
    pytest.skip(f"'{dir_non_free_packages}' must exist to run 'bazel cquery' command.")


def _validate_plugin_in_package(plugin_details: PluginDetails, stdout: str) -> bool:
    """Validate presence of target name in 'bazel cquery' output.

    Sample output is as follows,
    ```
    //omd:complete_install (eda66ab)
    //omd:deps_install (eda66ab)
    //omd:deps_packages (eda66ab)
    //omd:deps_packages_base (eda66ab)
    //non-free/packages/cmk-plugins-nonfree:pkg_tar-<plugin_name> (eda66ab)
    ```
    """
    if stdout.strip():
        return any(plugin_details.target in line.strip() for line in stdout.splitlines())
    # plugin target not found
    return False


@pytest.mark.parametrize("plugin_details", _CMK_PLUGINS)
@pytest.mark.parametrize("edition", sorted(_ULTIMATE_AND_HIGHER))
def test_plugin_present(edition: str, plugin_details: PluginDetails) -> None:
    """Checkmk plugin wheels must be installed in 'cloud/ultimate/ultimatemt' packages."""
    stdout = _stdout_bazel_cquery(edition, plugin_details.target)
    assert _validate_plugin_in_package(plugin_details, stdout), (
        f"'{plugin_details}' is not part of the '{edition}' build!"
    )


@pytest.mark.parametrize("plugin_details", _CMK_PLUGINS)
@pytest.mark.parametrize("edition", sorted(_PRO_AND_LOWER))
def test_plugin_absent(edition: str, plugin_details: PluginDetails) -> None:
    """Checkmk plugin wheels must NOT be installed in 'community/pro' packages."""
    stdout = _stdout_bazel_cquery(edition, plugin_details.target)
    # 'bazel cquery' does not result in non-zero exit code.
    assert not _validate_plugin_in_package(plugin_details, stdout), (
        f"'{plugin_details}' is unexpectedly part of the '{edition}' build!"
    )
