#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Exercise the graph file cleanup through the real ``cmk-update-config``.

Unlike the unit test, this covers that the action is registered and that it may
unlink files owned by the site user.
"""

from collections.abc import Iterator

import pytest

from tests.testlib.site import ADMIN_USER, Site, SiteFactory

_ADMIN_PROFILE = f"var/check_mk/web/{ADMIN_USER}"
# Every profile has to be swept, not only the admin's.
_ABANDONED_PROFILE = "var/check_mk/web/user_removed_after_resizing"

# The former renderer wrote these through save_user_file(), i.e. repr() of the value.
_GRAPH_SIZE = "(84, 20)\n"
_GRAPH_RANGES = (
    "{'time_range': (1755000000, 1755003600), 'step': 60, 'vertical_range': (0.0, 42.5)}\n"
)
_GRAPH_PIN = "1755001800\n"

# cmk-update-config prints the title of every action it runs.
_ACTION_TITLE = "Remove orphaned per-user graph files"


@pytest.fixture(name="update_config_site", scope="module")
def fixture_update_config_site(site_factory: SiteFactory) -> Iterator[Site]:
    """A dedicated, throw-away site: the update the test runs would poison a shared one."""
    with site_factory.get_test_site_ctx(name="upcfg", auto_restart_httpd=True) as site:
        yield site


def _run_update_config(site: Site) -> str:
    """``--conflict=force`` answers all prompts, ``--site-may-run`` allows a running site."""
    result = site.run(["cmk-update-config", "--conflict=force", "--site-may-run"], check=False)
    assert result.returncode == 0, (
        f"cmk-update-config failed (rc={result.returncode})\n{result.stdout}\n{result.stderr}"
    )
    return f"{result.stdout}\n{result.stderr}"


@pytest.mark.skip_if_edition("cloud")
def test_orphaned_graph_files_are_removed(update_config_site: Site) -> None:
    for profile in (_ADMIN_PROFILE, _ABANDONED_PROFILE):
        update_config_site.makedirs(profile)
        update_config_site.write_file(f"{profile}/graph_size.mk", _GRAPH_SIZE)
        update_config_site.write_file(f"{profile}/graph_range_test_graph.mk", _GRAPH_RANGES)
    update_config_site.write_file(f"{_ADMIN_PROFILE}/graph_pin.mk", _GRAPH_PIN)

    output = _run_update_config(update_config_site)

    assert _ACTION_TITLE in output, (
        f"{_ACTION_TITLE!r} did not run - the site version predates the action"
    )
    for profile in (_ADMIN_PROFILE, _ABANDONED_PROFILE):
        assert not update_config_site.file_exists(f"{profile}/graph_size.mk")
        assert not update_config_site.file_exists(f"{profile}/graph_range_test_graph.mk")
    assert update_config_site.read_file(f"{_ADMIN_PROFILE}/graph_pin.mk") == _GRAPH_PIN
