#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the module-near curated Maps settings modes (the DCD pattern).

Pins the two curated WATO modes: that both are admin-gated on ``maps.configure``,
that both persist to the *one* ``maps.d`` ``global.mk`` (all Maps settings live in
the feature's own domain), that saving one form preserves the other form's keys —
the merge-on-save that lets both forms share the single file — and that a
submitted value is validated against the form's own spec before it is stored.
"""

from pathlib import Path

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.version import Edition
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.pages import PageContext
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.watolib.mode import ModeRegistry
from cmk.maps.gui import _settings_modes
from cmk.maps.gui._config_domain import (
    CONFIG_VAR_CONNECTIONS,
    CONFIG_VAR_LOG_LEVEL,
    CONFIG_VAR_STATE_REFRESH_INTERVAL,
    ConfigDomainMaps,
)
from cmk.maps.gui._settings_modes import (
    MapsConfigFile,
    ModeMapsAuthoringSettings,
    ModeMapsDaemonSettings,
)


def test_registers_both_curated_modes() -> None:
    mode_registry = ModeRegistry()
    _settings_modes.register(mode_registry)
    assert set(mode_registry) == {"maps_authoring_settings", "maps_daemon_settings"}


def test_both_modes_require_configure_permission() -> None:
    assert ModeMapsAuthoringSettings.static_permissions() == ["maps.configure"]
    assert ModeMapsDaemonSettings.static_permissions() == ["maps.configure"]


def test_config_file_targets_the_feature_domain_global_mk() -> None:
    # Both curated forms share this one file (all Maps settings live in maps.d).
    assert MapsConfigFile()._config_file_path == ConfigDomainMaps().config_dir() / "global.mk"  # noqa: SLF001


def test_forms_share_one_file_without_clobbering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ConfigDomainMaps, "config_dir", lambda self: tmp_path)  # noqa: ARG005
    # The daemon form saves its keys...
    MapsConfigFile().validate_and_save({"maps_log_level": "DEBUG"}, pprint_value=True)
    # ...then the authoring form saves its keys, merged over the current content —
    # the exact pattern _ABCMapsSettingsMode.action uses. Without the merge this
    # would drop maps_log_level.
    merged = dict(MapsConfigFile().load_for_reading())
    merged.update({"maps_map_defaults": {"default_backend_id": "cmk_x"}})
    MapsConfigFile().validate_and_save(merged, pprint_value=True)

    stored = MapsConfigFile().load_for_reading()
    assert stored["maps_log_level"] == "DEBUG"
    assert stored["maps_map_defaults"] == {"default_backend_id": "cmk_x"}


def test_curated_form_and_wato_global_settings_do_not_clobber_each_other(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The one ``global.mk`` has two writers; both must survive the other.

    Setup → Global settings writes through ``ABCConfigDomain.save``, the curated
    form through ``WatoMultiConfigFile`` — different code paths onto the same file,
    so the serialization has to be mutually readable and each writer has to carry
    the other's keys over.
    """
    monkeypatch.setattr(ConfigDomainMaps, "config_dir", lambda self: tmp_path)  # noqa: ARG005
    domain = ConfigDomainMaps()

    # 1) The curated form writes the authoring defaults.
    MapsConfigFile().validate_and_save(
        {"maps_map_defaults": {"default_backend_id": "cmk_x"}}, pprint_value=True
    )
    # 2) A WATO global-settings save round-trips the domain (load, change, save) —
    #    exactly what ModeEditGlobalSetting.action does.
    settings = dict(domain.load())
    assert settings["maps_map_defaults"] == {"default_backend_id": "cmk_x"}, "not readable by WATO"
    settings["maps_log_level"] = "DEBUG"
    domain.save(settings)

    # 3) Both keys are there, and the curated form can still read the file.
    assert domain.load()["maps_map_defaults"] == {"default_backend_id": "cmk_x"}
    stored = MapsConfigFile().load_for_reading()
    assert stored["maps_log_level"] == "DEBUG"
    assert stored["maps_map_defaults"] == {"default_backend_id": "cmk_x"}


@pytest.mark.parametrize("interval", [0, 99999], ids=["below-minimum", "above-maximum"])
def test_daemon_form_rejects_an_out_of_range_refresh_interval(
    request_context: None,  # noqa: ARG001
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    interval: int,
) -> None:
    """``action`` validates the submitted value against the form's spec before saving.

    The range is declared on the FormSpec (``NumberInRange``) and has to survive
    the conversion into the legacy spec this form renders: nothing downstream
    would catch it, since ``validate_and_save`` only checks the config file's
    TypedDict shape, and the value is replicated to the daemon.
    """
    monkeypatch.setattr(ConfigDomainMaps, "config_dir", lambda self: tmp_path)  # noqa: ARG005
    mode = ModeMapsDaemonSettings(
        Edition.COMMUNITY, PageContext(config=Config(), request=request, transactions=transactions)
    )

    with pytest.raises((MKUserError, MKGeneralException)):
        mode._valuespec().validate_value(  # noqa: SLF001
            {
                CONFIG_VAR_CONNECTIONS: [],
                CONFIG_VAR_LOG_LEVEL: "INFO",
                CONFIG_VAR_STATE_REFRESH_INTERVAL: interval,
            },
            "maps_daemon_settings",
        )


def test_daemon_form_accepts_a_valid_refresh_interval(
    request_context: None,  # noqa: ARG001
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ConfigDomainMaps, "config_dir", lambda self: tmp_path)  # noqa: ARG005
    mode = ModeMapsDaemonSettings(
        Edition.COMMUNITY, PageContext(config=Config(), request=request, transactions=transactions)
    )

    mode._valuespec().validate_value(  # noqa: SLF001
        {
            CONFIG_VAR_CONNECTIONS: [],
            CONFIG_VAR_LOG_LEVEL: "INFO",
            CONFIG_VAR_STATE_REFRESH_INTERVAL: 5,
        },
        "maps_daemon_settings",
    )
