#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from types import ModuleType
from typing import Final

import pytest

from cmk.ccc import version as checkmk_version

from cmk.discover_plugins import family_libexec_dir
from cmk.plugins.checkmk.active_check import check_bi_aggr
from cmk.plugins.elasticsearch.active_check import check_elasticsearch_query
from cmk.plugins.form_submit.active_check import check_form_submit
from cmk.plugins.sftp.active_check import check_sftp
from cmk.plugins.traceroute.active_check import check_traceroute
from cmk.plugins.uniserv.active_check import check_uniserv
from cmk.server_side_calls_backend import load_active_checks

TESTED_AC_MODULES: Final[Mapping[str, ModuleType | None]] = {
    "bi_aggr": check_bi_aggr,
    "by_ssh": None,  # TODO
    "cert": None,  # rust
    "cmk_inv": None,  # TODO
    "disk_smb": None,  # TODO
    "dns": None,  # TODO
    "elasticsearch_query": check_elasticsearch_query,
    "form_submit": check_form_submit,
    "ftp": None,  # TODO
    "http": None,  # TODO
    "httpv2": None,  # rust
    "icmp": None,  # TODO
    "ldap": None,  # TODO
    "mail": None,  # TODO
    "mail_loop": None,  # TODO
    "mailboxes": None,  # TODO
    "mkevents": None,  # C
    "notify_count": None,  # FIXME: import currently has too many side effects
    "sftp": check_sftp,
    "smtp": None,  # TODO
    "sql": None,  # TODO
    "ssh": None,  # TODO
    "tcp": None,  # TODO
    "traceroute": check_traceroute,
    "uniserv": check_uniserv,
}


def test_all_checks_considered() -> None:
    """Make sure our test cases are up to date

    Compare the hard coded checks map `TESTED_AC_MODULES` to the
    set of checks configurable via WATO, and make sure we cover them.
    """
    configurable_active_checks = {
        plugin.name for plugin in load_active_checks(raise_errors=True).values()
    }
    assert set(TESTED_AC_MODULES) == configurable_active_checks


def test_all_checks_versions() -> None:
    """Ensure the agents `__version__` is up to date, if present."""
    version_mismatch = {
        module.__name__
        for module in TESTED_AC_MODULES.values()
        # not having the __version__ is ok, but if present it must match
        if module
        and hasattr(module, "__version__")
        and module.__version__ != checkmk_version.__version__
    }
    assert not version_mismatch


def test_active_checks_location() -> None:
    """Make sure all executables are where we expect them"""
    # TODO: Turn into this:
    # assert all(
    #    (family_libexec_dir(location.module) / f"check_{plugin.name}").exists()
    #    for location, plugin in load_active_checks(raise_errors=True).items()
    # )
    offenders = {
        plugin.name
        for location, plugin in load_active_checks(raise_errors=True).items()
        if not (family_libexec_dir(location.module) / f"check_{plugin.name}").exists()
    }
    assert offenders == {
        "by_ssh",
        "cert",
        "dns",
        "ftp",
        "http",
        "httpv2",
        "icmp",
        "ldap",
        "mkevents",
        "smtp",
        "ssh",
        "tcp",
    }


@pytest.mark.parametrize(
    "module",
    [m for m in TESTED_AC_MODULES.values() if m is not None],
)
def test_user_agent_string(module: ModuleType) -> None:
    try:
        user_agent = module.USER_AGENT
    except AttributeError:
        return
    assert user_agent.startswith("checkmk-active-")
    assert user_agent.endswith(f"-{checkmk_version.__version__}")
