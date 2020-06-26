#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import socket
import shutil
import logging
from pathlib import Path

import pytest  # type: ignore[import]

import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.version as cmk_version

from testlib import is_managed_repo, is_enterprise_repo
from testlib.debug_utils import cmk_debug_enabled

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def fixture_umask(autouse=True):
    """Ensure the unit tests always use the same umask"""
    with cmk.utils.misc.umask(0o0007):
        yield


@pytest.fixture(name="edition_short", params=["cre", "cee", "cme"])
def fixture_edition_short(monkeypatch, request):
    edition_short = request.param
    if edition_short == "cme" and not is_managed_repo():
        pytest.skip("Needed files are not available")

    if edition_short == "cee" and not is_enterprise_repo():
        pytest.skip("Needed files are not available")

    monkeypatch.setattr(cmk_version, "edition_short", lambda: edition_short)
    yield edition_short


@pytest.fixture(autouse=True, scope="function")
def patch_omd_site(monkeypatch):
    monkeypatch.setenv("OMD_SITE", "NO_SITE")
    monkeypatch.setattr(cmk_version, "omd_site", lambda: "NO_SITE")

    _touch(cmk.utils.paths.htpasswd_file)
    store.makedirs(cmk.utils.paths.var_dir + '/web')
    store.makedirs(cmk.utils.paths.var_dir + '/php-api')
    store.makedirs(cmk.utils.paths.var_dir + '/wato/php-api')
    store.makedirs(cmk.utils.paths.var_dir + "/wato/auth")
    store.makedirs(cmk.utils.paths.omd_root + '/var/log')
    store.makedirs(cmk.utils.paths.omd_root + '/tmp/check_mk')
    store.makedirs(cmk.utils.paths.default_config_dir + '/conf.d/wato')
    store.makedirs(cmk.utils.paths.default_config_dir + '/multisite.d/wato')
    store.makedirs(cmk.utils.paths.default_config_dir + '/mkeventd.d/wato')
    _touch(cmk.utils.paths.default_config_dir + '/mkeventd.mk')
    _touch(cmk.utils.paths.default_config_dir + '/multisite.mk')


def _touch(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).touch()


@pytest.fixture(autouse=True, scope="function")
def cleanup_after_test():
    yield

    # Ensure there is no file left over in the unit test fake site
    # to prevent tests involving eachother
    for entry in Path(cmk.utils.paths.omd_root).iterdir():
        # This randomly fails for some unclear reasons. Looks like a race condition, but I
        # currently have no idea which triggers this since the tests are not executed in
        # parallel at the moment. This is meant as quick hack, trying to reduce flaky results.
        try:
            if entry.is_dir():
                shutil.rmtree(str(entry))
            else:
                entry.unlink()
        except OSError as e:
            logger.debug("Failed to cleanup %s after test: %s. Keep going anyway", entry, e)


# Unit tests should not be executed in site.
# -> Disabled site fixture for them
@pytest.fixture(scope="session")
def site(request):
    pass


# TODO: This fixes our unit tests when executing the tests while the local
# resolver uses a search domain which uses wildcard resolution. e.g. in a
# network where mathias-kettner.de is in the domain search list and
# [anything].mathias-kettner.de resolves to an IP address.
# Clean this up once we don't have this situation anymore e.g. via VPN.
@pytest.fixture()
def fixup_ip_lookup(monkeypatch):
    # Fix IP lookup when
    def _getaddrinfo(host, port, family=None, socktype=None, proto=None, flags=None):
        if family == socket.AF_INET:
            # TODO: This is broken. It should return (family, type, proto, canonname, sockaddr)
            return "0.0.0.0"
        raise NotImplementedError()

    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo)


@pytest.fixture(scope="session", autouse=True)
def config_load_all_checks():
    # this is needed in cmk/base *and* checks/ :-(
    import cmk.base.config as config  # pylint: disable=bad-option-value,import-outside-toplevel
    import cmk.base.check_api as check_api  # pylint: disable=bad-option-value,import-outside-toplevel

    config._initialize_data_structures()
    assert config.check_info == {}

    with cmk_debug_enabled():  # fail if a plugin can't be loaded
        config.load_all_checks(check_api.get_check_api_context)

    assert len(config.check_info) > 1000  # sanitiy check


@pytest.fixture(scope="session", autouse=True)
def config_check_info(config_load_all_checks):
    import cmk.base.config as config  # pylint: disable=bad-option-value,import-outside-toplevel
    return copy.deepcopy(config.check_info)


@pytest.fixture(scope="session", autouse=True)
def config_active_check_info(config_load_all_checks):
    import cmk.base.config as config  # pylint: disable=bad-option-value,import-outside-toplevel
    return copy.deepcopy(config.active_check_info)


@pytest.fixture(scope="session", autouse=True)
def config_snmp_scan_functions(config_load_all_checks):
    import cmk.base.config as config  # pylint: disable=bad-option-value,import-outside-toplevel
    assert len(config.snmp_scan_functions) > 400  # sanity check
    return copy.deepcopy(config.snmp_scan_functions)
