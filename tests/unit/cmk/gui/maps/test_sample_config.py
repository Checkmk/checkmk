#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the Maps sample-config generator.

The regression guarded here: ``save_global_settings_raw`` writes every enabled
domain's file, so seeding ``maps_connections`` with a *partial* settings dict
would blank out settings other generators already wrote (e.g. the site-CA trust
from the basic-WATO generator, which runs earlier). The generator must load the
current settings and merge.
"""

import pytest

from cmk.ccc.site import omd_site
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.maps.gui import _sample_config
from cmk.maps.gui._config_domain import CONFIG_VAR_CONNECTIONS, ConfigDomainMaps
from cmk.maps.gui._config_variables import ConfigVariableMapsConnections
from cmk.maps.gui._sample_config import SampleConfigGeneratorMapsConnections
from cmk.maps.gui._settings import connection_choices


def test_ident_and_runs_after_basic_wato() -> None:
    assert SampleConfigGeneratorMapsConnections.ident() == "maps_connections"
    # Must run after the basic WATO config (sort_index 11), whose settings it merges.
    assert SampleConfigGeneratorMapsConnections.sort_index() > 11


@pytest.mark.usefixtures("request_context")
def test_generate_merges_and_preserves_foreign_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    existing = {"trusted_certificate_authorities": {"use_system_wide_cas": True}}
    saved: dict[str, object] = {}

    monkeypatch.setattr(_sample_config, "omd_site", lambda: "heute")
    monkeypatch.setattr(_sample_config, "load_configuration_settings", lambda: dict(existing))
    monkeypatch.setattr(
        _sample_config, "save_global_settings_raw", lambda settings, **_kw: saved.update(settings)
    )

    SampleConfigGeneratorMapsConnections().generate(folder_tree())

    # The foreign setting an earlier generator wrote must survive...
    assert saved["trusted_certificate_authorities"] == existing["trusted_certificate_authorities"]
    # ...and the local-site connection is seeded alongside it.
    connections = saved[CONFIG_VAR_CONNECTIONS]
    assert isinstance(connections, list)
    assert connections[0]["id"] == "cmk_heute"


def test_generated_connection_lands_in_the_maps_domain_and_is_read_back(
    request_context: None,  # noqa: ARG001
) -> None:
    """The seeded connection must reach the file the *daemon* reads.

    ``save_global_settings_raw`` routes each variable to its ``ConfigVariable``'s
    ``primary_domain`` — ``ConfigDomainMaps`` for all Maps globals — so the
    connections land in ``maps.d/wato/global.mk``, the directory the
    ReplicationPath ships, and not in the GUI's ``multisite.d``. Runs the real
    generator through the real save, so the routing is exercised rather than
    assumed.
    """
    assert isinstance(ConfigVariableMapsConnections.primary_domain(), ConfigDomainMaps)
    SampleConfigGeneratorMapsConnections().generate(folder_tree())

    global_mk = ConfigDomainMaps().config_dir() / "global.mk"
    assert global_mk.exists(), "the Maps domain file was not written"
    assert CONFIG_VAR_CONNECTIONS in global_mk.read_text()
    # ...and the GUI reads exactly that back through its one accessor.
    assert connection_choices()[0][0] == f"cmk_{omd_site()}"


@pytest.mark.usefixtures("request_context")
def test_generate_does_not_mutate_loaded_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    # The generator copies before assigning, so the object returned by
    # load_configuration_settings must not gain the connections key.
    source = {"trusted_certificate_authorities": {"use_system_wide_cas": True}}
    monkeypatch.setattr(_sample_config, "omd_site", lambda: "heute")
    monkeypatch.setattr(_sample_config, "load_configuration_settings", lambda: source)
    monkeypatch.setattr(_sample_config, "save_global_settings_raw", lambda *_a, **_kw: None)

    SampleConfigGeneratorMapsConnections().generate(folder_tree())

    assert CONFIG_VAR_CONNECTIONS not in source
