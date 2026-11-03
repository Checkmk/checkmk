#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path

import pytest

import cmk.utils.paths
from cmk.ccc.version import Edition
from cmk.gui.form_specs import get_visitor, RawDiskData, registration, VisitorOptions
from cmk.plugins.checkmk.rulesets import cmk_update_agent
from cmk.rulesets.v1.form_specs import DictGroup, Dictionary, SingleChoice


@pytest.fixture(name="config_dir")
def _config_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    config_dir = tmp_path / "conf.d"
    config_dir.mkdir()
    monkeypatch.setattr(cmk.utils.paths, "check_mk_config_dir", config_dir)
    return config_dir


def _set_edition(monkeypatch: pytest.MonkeyPatch, edition: Edition) -> None:
    monkeypatch.setattr(cmk_update_agent, "edition", lambda _omd_root: edition)


def test_returns_false_when_edition_is_not_ultimatemt(
    monkeypatch: pytest.MonkeyPatch, config_dir: Path
) -> None:
    _set_edition(monkeypatch, Edition.COMMUNITY)
    # Even with a remote-site marker present, a non-ULTIMATEMT edition short-circuits.
    (config_dir / "distributed_wato.mk").write_text("is_distributed_setup_remote_site = True\n")

    assert cmk_update_agent._is_ultimatemt_remote_site() is False  # noqa: SLF001


def test_returns_false_when_distributed_wato_file_is_missing(
    monkeypatch: pytest.MonkeyPatch, config_dir: Path
) -> None:
    _set_edition(monkeypatch, Edition.ULTIMATEMT)
    assert not (config_dir / "distributed_wato.mk").exists()

    assert cmk_update_agent._is_ultimatemt_remote_site() is False  # noqa: SLF001


def test_returns_false_when_distributed_wato_file_is_empty(
    monkeypatch: pytest.MonkeyPatch, config_dir: Path
) -> None:
    _set_edition(monkeypatch, Edition.ULTIMATEMT)
    (config_dir / "distributed_wato.mk").write_text("")

    assert cmk_update_agent._is_ultimatemt_remote_site() is False  # noqa: SLF001


def test_returns_true_when_is_distributed_setup_remote_site_flag_set(
    monkeypatch: pytest.MonkeyPatch, config_dir: Path
) -> None:
    _set_edition(monkeypatch, Edition.ULTIMATEMT)
    (config_dir / "distributed_wato.mk").write_text("is_distributed_setup_remote_site = True\n")

    assert cmk_update_agent._is_ultimatemt_remote_site() is True  # noqa: SLF001


def test_returns_false_when_remote_site_flag_is_false(
    monkeypatch: pytest.MonkeyPatch, config_dir: Path
) -> None:
    _set_edition(monkeypatch, Edition.ULTIMATEMT)
    (config_dir / "distributed_wato.mk").write_text("is_distributed_setup_remote_site = False\n")

    assert cmk_update_agent._is_ultimatemt_remote_site() is False  # noqa: SLF001


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(("bit32", None), "script", id="32bit-choice-with-empty-parameters"),
        pytest.param(
            "bit64",
            "bit64",
            id="already-migrated-binary",
        ),
        pytest.param("script", "script", id="already-migrated-script"),
        pytest.param(
            ("bit64", None),
            "bit64",
            id="choice-with-empty-parameters",
        ),
    ],
)
def test_migrate_edition(value: object, expected: str) -> None:
    assert cmk_update_agent._migrate_edition(value) == expected  # noqa: SLF001


@pytest.fixture(name="rule_form")
def _rule_form(monkeypatch: pytest.MonkeyPatch) -> Dictionary:
    # The rule prefills the site of the update server with the name of this site.
    monkeypatch.setenv("OMD_SITE", "NO_SITE")
    rule_form = cmk_update_agent.rule_spec_cmk_update_agent.parameter_form()
    assert isinstance(rule_form, Dictionary)
    return rule_form


@pytest.fixture
def _register_form_spec_visitors() -> None:
    registration.register()


@pytest.fixture(name="activation")
def _activation(rule_form: Dictionary) -> SingleChoice:
    activation = rule_form.elements["activated"].parameter_form
    assert isinstance(activation, SingleChoice)
    return activation


def _migrate(activation: SingleChoice, value: object) -> object:
    assert activation.migrate is not None
    return activation.migrate(value)


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param("enabled", "compatible", id="enabled"),
        pytest.param("disabled", "disabled", id="disabled"),
    ],
)
def test_migration_maps_the_activation_of_checkmk_2_5(
    activation: SingleChoice, value: object, expected: str
) -> None:
    assert _migrate(activation, value) == expected


def test_every_activation_entry_survives_the_migration(activation: SingleChoice) -> None:
    names = [element.name for element in activation.elements]

    assert [_migrate(activation, name) for name in names] == names


def test_migration_rejects_an_unknown_activation(activation: SingleChoice) -> None:
    with pytest.raises(ValueError):
        _migrate(activation, "unknown")


def _legacy_updater_group(rule_form: Dictionary) -> DictGroup:
    group = rule_form.elements["server_data"].group
    assert isinstance(group, DictGroup)
    return group


def test_the_legacy_updater_options_form_a_group_of_their_own(rule_form: Dictionary) -> None:
    """CMK-39506: the options only the legacy updater uses are shown in a group of their own."""
    group = _legacy_updater_group(rule_form)

    assert {name for name, element in rule_form.elements.items() if element.group == group} == {
        "server_data",
        "certificates",
        "proxy",
        "edition",
    }


@pytest.mark.parametrize("entry", ["compatible", "legacy"])
def test_the_legacy_updater_group_names_the_entries_that_use_it(
    rule_form: Dictionary, activation: SingleChoice, entry: str
) -> None:
    """CMK-39506: the help of the legacy updater group names the entries that deploy it."""
    help_text = _legacy_updater_group(rule_form).help_text
    assert help_text is not None
    title = next(element.title for element in activation.elements if element.name == entry)

    assert title.localize(lambda text: text) in help_text.localize(lambda text: text)


# Every option of the rule as Checkmk 2.5 stores it, except two that need a site: the signature
# keys validate against its key store, and a certificate is encrypted with its GUI session
# secret. The migration leaves both alone.
_RULE_OF_CHECKMK_2_5: Mapping[str, object] = {
    "interval": 3600.0,
    "updater_registration": "keep",
    "server_data": {
        "usage": "registration",
        "server": "checkmk.example.com",
        "site": "mysite",
        "protocol": "https",
    },
    "proxy": (
        "explicit_proxy",
        {"server": "proxy.example.com", "port": 3128, "proxy_protocol": "http"},
    ),
    "edition": "bit64",
}


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param({**_RULE_OF_CHECKMK_2_5, "activated": "enabled"}, id="enabled"),
        pytest.param({**_RULE_OF_CHECKMK_2_5, "activated": "disabled"}, id="disabled"),
        pytest.param(_RULE_OF_CHECKMK_2_5, id="without-activation"),
        pytest.param({}, id="empty"),
    ],
)
@pytest.mark.usefixtures("_register_form_spec_visitors")
def test_a_rule_of_checkmk_2_5_validates_after_the_update(
    rule_form: Dictionary, rule: Mapping[str, object]
) -> None:
    """CMK-39506: a rule saved by Checkmk 2.5 is valid after the update has migrated it."""
    # The update migrates and stores the rule, then validates what it stored.
    updated = get_visitor(
        rule_form, VisitorOptions(migrate_values=True, mask_values=False)
    ).to_disk(RawDiskData(rule))

    assert (
        get_visitor(rule_form, VisitorOptions(migrate_values=False, mask_values=True)).validate(
            RawDiskData(updated)
        )
        == []
    )


@pytest.mark.usefixtures("_register_form_spec_visitors")
def test_the_update_leaves_an_empty_rule_empty(rule_form: Dictionary) -> None:
    """An empty rule of Checkmk 2.5 sets no option after the update."""
    updated = get_visitor(
        rule_form, VisitorOptions(migrate_values=True, mask_values=False)
    ).to_disk(RawDiskData({}))

    assert updated == {}
