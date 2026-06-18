#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.multisite import write_multisite_authorisation, write_multisite_cookie_auth

_APACHE = "etc/apache/conf.d/cookie_auth.conf"
_COOKIE_NAGVIS = "etc/nagvis/conf.d/cookie_auth.ini.php"
_AUTH_NAGVIS = "etc/nagvis/conf.d/authorisation.ini.php"
_PNP = "etc/pnp4nagios/config.d/authorisation.php"


def test_cookie_auth_on_with_nagvis_dir(tmp_path: Path) -> None:
    (tmp_path / "etc/apache/conf.d").mkdir(parents=True)
    (tmp_path / "etc/nagvis/conf.d").mkdir(parents=True)
    write_multisite_cookie_auth("mysite", tmp_path, {"MULTISITE_COOKIE_AUTH": "on"})
    apache = (tmp_path / _APACHE).read_text()
    assert (
        apache
        == """\
<LocationMatch ^/mysite/(nagvis|check_mk)>
    Order allow,deny
    Allow from all
    Satisfy any
</LocationMatch>
"""
    )
    nagvis = (tmp_path / _COOKIE_NAGVIS).read_text()
    assert 'logon_multisite_htpasswd="/omd/sites/mysite/etc/htpasswd"' in nagvis
    assert nagvis.endswith("logon_multisite_cookie_version=1\n")


def test_cookie_auth_on_without_nagvis_dir_writes_apache_only(tmp_path: Path) -> None:
    (tmp_path / "etc/apache/conf.d").mkdir(parents=True)
    write_multisite_cookie_auth("mysite", tmp_path, {"MULTISITE_COOKIE_AUTH": "on"})
    assert (tmp_path / _APACHE).is_file()
    assert not (tmp_path / _COOKIE_NAGVIS).exists()


def test_cookie_auth_off_removes_both(tmp_path: Path) -> None:
    (tmp_path / "etc/apache/conf.d").mkdir(parents=True)
    (tmp_path / "etc/nagvis/conf.d").mkdir(parents=True)
    write_multisite_cookie_auth("mysite", tmp_path, {"MULTISITE_COOKIE_AUTH": "on"})
    write_multisite_cookie_auth("mysite", tmp_path, {"MULTISITE_COOKIE_AUTH": "off"})
    assert not (tmp_path / _APACHE).exists()
    assert not (tmp_path / _COOKIE_NAGVIS).exists()


def test_authorisation_on_creates_dirs_and_files(tmp_path: Path) -> None:
    (tmp_path / "etc/pnp4nagios").mkdir(parents=True)
    write_multisite_authorisation("_", tmp_path, {"MULTISITE_AUTHORISATION": "on"})
    nagvis = (tmp_path / _AUTH_NAGVIS).read_text()
    assert 'authorisationmodule="CoreAuthorisationModMultisite"' in nagvis
    assert f'authorisation_multisite_file="{tmp_path}/var/check_mk/wato/auth/auth.php"' in nagvis
    pnp = (tmp_path / _PNP).read_text()
    assert pnp.startswith("<?php\n")
    assert "$conf['allowed_for_all_services']" in pnp


def test_authorisation_on_without_pnp_parent_skips_pnp(tmp_path: Path) -> None:
    write_multisite_authorisation("_", tmp_path, {"MULTISITE_AUTHORISATION": "on"})
    assert (tmp_path / _AUTH_NAGVIS).is_file()
    assert not (tmp_path / _PNP).exists()


def test_authorisation_off_removes_both(tmp_path: Path) -> None:
    (tmp_path / "etc/pnp4nagios").mkdir(parents=True)
    write_multisite_authorisation("_", tmp_path, {"MULTISITE_AUTHORISATION": "on"})
    write_multisite_authorisation("_", tmp_path, {"MULTISITE_AUTHORISATION": "off"})
    assert not (tmp_path / _AUTH_NAGVIS).exists()
    assert not (tmp_path / _PNP).exists()
