#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

"""The GUI↔daemon site-specs contract, pinned end to end.

The GUI (:mod:`cmk.maps.gui._sites`) writes the prepared Livestatus site
specs to ``maps.d/sitespecs.mk`` on every site save; the daemon
(:mod:`cmk.maps.backend.integrations.checkmk_sites`) reads them back for its
``MultiSiteConnection`` fan-out. This test writes with the *real* GUI hook
and reads with the *real* daemon loader, so drift in the file location,
variable name or spec shape fails CI.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest

from cmk.ccc.site import SiteId
from cmk.gui.config import Config
from cmk.livestatus_client import (
    LocalSocketInfo,
    NetworkSocketDetails,
    NetworkSocketInfo,
    SiteConfiguration,
    SiteConfigurations,
)
from cmk.maps.backend.core.config import settings as daemon_settings
from cmk.maps.backend.integrations import checkmk_sites
from cmk.maps.gui import _sites
from tests.testlib.gui.web_test_app import SetConfig


@pytest.fixture(name="shared_omd_root")
def fixture_shared_omd_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point the GUI writer and the daemon reader at the same OMD root."""
    monkeypatch.setattr(
        _sites,
        "site_specs_path",
        lambda: tmp_path / "etc" / "check_mk" / "maps.d" / "sitespecs.mk",
    )
    monkeypatch.setattr(daemon_settings, "checkmk_omd_root", str(tmp_path))
    yield tmp_path


def _site(site_id: str, *, disabled: bool = False, local: bool = False) -> SiteConfiguration:
    socket: LocalSocketInfo | NetworkSocketInfo
    if local:
        socket = ("local", None)
    else:
        socket = ("tcp", NetworkSocketDetails(address=("10.1.1.2", 6557), tls=("plain_text", {})))
    return SiteConfiguration(
        alias=site_id,
        disable_wato=True,
        disabled=disabled,
        id=SiteId(site_id),
        insecure=False,
        multisiteurl="",
        persist=False,
        proxy=None,
        replicate_ec=False,
        replicate_mkps=False,
        replication=None if local else "slave",
        message_broker_port=5672,
        status_host=None,
        timeout=10,
        url_prefix=f"/{site_id}/",
        user_login=True,
        is_trusted=False,
        socket=socket,
    )


def _sites_config(**sites: SiteConfiguration) -> SiteConfigurations:
    return SiteConfigurations({SiteId(site_id): spec for site_id, spec in sites.items()})


def test_distributed_specs_round_trip(shared_omd_root: Path) -> None:
    sites = _sites_config(
        central=_site("central", local=True),
        remote1=_site("remote1"),
        off=_site("off", disabled=True),
    )

    _sites._on_sites_saved(sites)  # noqa: SLF001
    loaded = checkmk_sites.load_sites()

    assert loaded is not None
    assert set(loaded) == {"central", "remote1"}  # disabled sites are dropped
    # Sockets arrive pre-encoded for MultiSiteConnection; the daemon does no
    # normalisation of its own.
    assert loaded["remote1"]["socket"] == "tcp:10.1.1.2:6557"
    assert loaded["remote1"]["tls"] == ("plain_text", {})
    assert str(loaded["central"]["socket"]).startswith("unix:")


def test_single_local_site_means_fast_path(shared_omd_root: Path) -> None:
    _sites._on_sites_saved(_sites_config(central=_site("central", local=True)))  # noqa: SLF001

    assert _sites.site_specs_path().exists()  # written (empty), not skipped
    assert checkmk_sites.load_sites() is None


def test_missing_specs_file_means_fast_path(shared_omd_root: Path) -> None:
    assert checkmk_sites.load_sites() is None


def test_pre_activate_regenerates_from_active_config(
    shared_omd_root: Path, load_config: Config, set_config: SetConfig
) -> None:
    """Every activation regenerates the specs from the running sites config, even
    without a preceding sites-save.

    This is what makes the fan-out appear for a distributed setup that predates
    Maps — or one configured outside the WATO save flow — where the
    ``sites-saved`` hook never fired for Maps.
    """
    sites = _sites_config(central=_site("central", local=True), remote1=_site("remote1"))
    assert not _sites.site_specs_path().exists()

    with set_config(sites=sites):
        _sites._on_pre_activate_changes()  # noqa: SLF001

    loaded = checkmk_sites.load_sites()
    assert loaded is not None
    assert set(loaded) == {"central", "remote1"}


def test_shrinking_back_to_single_site_clears_the_fan_out(shared_omd_root: Path) -> None:
    _sites._on_sites_saved(  # noqa: SLF001
        _sites_config(central=_site("central", local=True), remote1=_site("remote1"))
    )
    assert checkmk_sites.load_sites() is not None

    _sites._on_sites_saved(_sites_config(central=_site("central", local=True)))  # noqa: SLF001
    assert checkmk_sites.load_sites() is None
