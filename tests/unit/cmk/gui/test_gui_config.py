#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

import cmk.gui.config
import cmk.utils.paths
from cmk.gui.config import active_config, Config


def test_raw_config_stored_by_make_config_object() -> None:
    raw = cmk.gui.config.get_default_config()
    config = cmk.gui.config.make_config_object(raw)
    assert config.raw is raw


def test_raw_config_returns_mapping() -> None:
    raw = cmk.gui.config.get_default_config()
    config = cmk.gui.config.make_config_object(raw)
    assert config.raw["quicksearch_dropdown_limit"] == raw["quicksearch_dropdown_limit"]


def test_raw_config_default_is_empty_dict() -> None:
    config = Config()
    assert config.raw == {}


def test_raw_config_with_custom_keys() -> None:
    raw = cmk.gui.config.get_default_config()
    raw["my_custom_plugin_var"] = "hello"
    config = cmk.gui.config.make_config_object(raw)
    assert config.raw is raw
    assert config.raw["my_custom_plugin_var"] == "hello"


def test_feature_config_defaults_appear_in_default_config() -> None:
    cmk.gui.config.register_feature_config_defaults({"_test_feature_var": 42})
    try:
        default_config = cmk.gui.config.get_default_config()
        assert default_config["_test_feature_var"] == 42

        config = cmk.gui.config.make_config_object(default_config)
        assert config.raw["_test_feature_var"] == 42
    finally:
        cmk.gui.config._feature_config_defaults.pop("_test_feature_var", None)  # noqa: SLF001


def test_feature_config_defaults_not_mutated_by_config_loading() -> None:
    """Verify that get_default_config() deep-copies mutable values from _feature_config_defaults.

    Without deep-copying, exec-based config loading (e.g. agent_signature_keys.update({...}))
    mutates the module-level defaults, causing stale data to persist across requests (CMK-33375).
    """
    cmk.gui.config.register_feature_config_defaults({"_test_mutable_var": {}})
    try:
        default_config = cmk.gui.config.get_default_config()
        default_config["_test_mutable_var"]["injected_key"] = "injected_value"

        assert cmk.gui.config._feature_config_defaults["_test_mutable_var"] == {}  # noqa: SLF001

        default_config_2 = cmk.gui.config.get_default_config()
        assert default_config_2["_test_mutable_var"] == {}
    finally:
        cmk.gui.config._feature_config_defaults.pop("_test_mutable_var", None)  # noqa: SLF001


@pytest.mark.usefixtures("request_context")
def test_load_config() -> None:
    config_path = cmk.utils.paths.default_config_dir / "multisite.mk"
    config_path.unlink(missing_ok=True)

    config = cmk.gui.config.load_config()
    assert config.quicksearch_dropdown_limit == 80
    assert active_config.quicksearch_dropdown_limit == 80

    with config_path.open("w") as f:
        f.write("quicksearch_dropdown_limit = 1337\n")
    config = cmk.gui.config.load_config()
    assert config.quicksearch_dropdown_limit == 1337

    # load_config must not modify the active_config
    assert active_config.quicksearch_dropdown_limit == 80


@pytest.fixture()
def local_config_plugin() -> None:
    config_plugin = cmk.utils.paths.local_web_dir / "plugins" / "config" / "test.py"
    config_plugin.parent.mkdir(parents=True)
    with config_plugin.open("w") as f:
        f.write("ding = 'dong'\n")


@pytest.mark.usefixtures("local_config_plugin", "request_context")
def test_load_config_respects_local_plugin() -> None:
    config = cmk.gui.config.load_config()
    assert config.ding == "dong"  # type: ignore[attr-defined, unused-ignore]


@pytest.mark.usefixtures("local_config_plugin", "request_context")
def test_load_config_allows_local_plugin_setting() -> None:
    with (cmk.utils.paths.default_config_dir / "multisite.mk").open("w") as f:
        f.write("ding = 'ding'\n")
    config = cmk.gui.config.load_config()
    assert config.ding == "ding"  # type: ignore[attr-defined, unused-ignore]


def test_default_tags(load_config: Config) -> None:
    groups = {
        "snmp_ds": [
            "no-snmp",
            "snmp-v1",
            "snmp-v2",
        ],
        "address_family": [
            "ip-v4-only",
            "ip-v4v6",
            "ip-v6-only",
            "no-ip",
        ],
        "piggyback": [
            "auto-piggyback",
            "piggyback",
            "no-piggyback",
        ],
        "agent": [
            "all-agents",
            "cmk-agent",
            "no-agent",
            "special-agents",
        ],
    }

    assert sorted(dict(load_config.tags.get_tag_group_choices()).keys()) == sorted(groups.keys())

    for tag_group in load_config.tags.tag_groups:
        assert sorted(tag_group.get_tag_ids(), key=lambda s: s or "") == sorted(
            groups[tag_group.id]
        )


def test_default_aux_tags(load_config: Config) -> None:
    assert sorted(load_config.tags.aux_tag_list.get_tag_ids()) == sorted(
        [
            "checkmk-agent",
            "ip-v4",
            "ip-v6",
            "ping",
            "snmp",
            "tcp",
        ]
    )


@pytest.mark.usefixtures("request_context")
def test_config_initialize_updates_active_config() -> None:
    config_path = cmk.utils.paths.default_config_dir / "multisite.mk"

    assert active_config.quicksearch_dropdown_limit == 80

    config_path.write_text("quicksearch_dropdown_limit = 1337\n")
    config = cmk.gui.config.initialize()
    assert config.quicksearch_dropdown_limit == 1337
    assert active_config.quicksearch_dropdown_limit == 1337
