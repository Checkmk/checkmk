#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

import cmk.utils.paths
from cmk.ccc import store
from cmk.update_config.internal import ExpiryVersion
from cmk.update_config.plugins.actions.verify_unseeded_base_config import (
    VerifyUnseededBaseConfig,
)

_ACTION = VerifyUnseededBaseConfig(
    name="verify_unseeded_base_config",
    title="Verifying the configuration files load without predefined variables",
    sort_index=997,
    expiry_version=ExpiryVersion.CMK_310,
    continue_on_failure=True,
)


@pytest.fixture(name="config_dir")
def config_dir_fixture() -> Iterator[Path]:
    # Both are removed afterwards, along with anything the test wrote.
    wato_dir = cmk.utils.paths.check_mk_config_dir / "wato"
    assert not cmk.utils.paths.main_config_file.exists()
    assert not wato_dir.exists()
    cmk.utils.paths.main_config_file.parent.mkdir(parents=True, exist_ok=True)
    cmk.utils.paths.main_config_file.write_text("")
    wato_dir.mkdir(parents=True)
    yield wato_dir
    shutil.rmtree(wato_dir)
    cmk.utils.paths.main_config_file.unlink()


_WS = re.compile(r"\s+")


def _warnings(caplog: pytest.LogCaptureFixture) -> tuple[str, ...]:
    return tuple(
        _WS.sub(" ", r.getMessage()) for r in caplog.records if r.levelno == logging.WARNING
    )


def test_self_bootstrapping_files_pass_silently(
    config_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    store.save_to_mk_file(config_dir / "groups.mk", key="define_hostgroups", value={"a": "A"})
    (config_dir / "rules.mk").write_text(
        "agent_ports = locals().setdefault('agent_ports', [])\n"
        "agent_ports = [{'id': '1', 'condition': {'host_folder': '/%s/' % FOLDER_PATH}, "
        "'value': 1}] + agent_ports\n"
    )

    _ACTION(logging.getLogger(__name__))

    assert not _warnings(caplog)


def test_a_legacy_file_is_named_with_its_error(
    config_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (config_dir / "groups.mk").write_text("define_hostgroups.update({'a': 'A'})\n")
    store.save_to_mk_file(
        config_dir / "tags.mk", key="tag_config", value={"tag_groups": [], "aux_tags": []}
    )

    _ACTION(logging.getLogger(__name__))

    warnings = _warnings(caplog)

    assert len(warnings) == 2
    assert "Checkmk 3.1 will not" in warnings[0]
    assert "locals().setdefault('x', {})" in warnings[0]
    assert warnings[1].strip() == (
        f"{config_dir / 'groups.mk'}: name 'define_hostgroups' is not defined"
    )


def test_every_failing_file_is_named(config_dir: Path, caplog: pytest.LogCaptureFixture) -> None:
    cmk.utils.paths.main_config_file.write_text("extra_nagios_conf += 'define command {}'\n")
    (config_dir / "groups.mk").write_text("define_hostgroups.update({'a': 'A'})\n")

    _ACTION(logging.getLogger(__name__))

    assert [w.strip().split(":")[0] for w in _warnings(caplog)[1:]] == [
        str(cmk.utils.paths.main_config_file),
        str(config_dir / "groups.mk"),
    ]


def test_a_file_relying_on_an_earlier_one_is_named(
    config_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    cmk.utils.paths.main_config_file.write_text("define_hostgroups = {}\n")
    (config_dir / "groups.mk").write_text("define_hostgroups.update({'a': 'A'})\n")

    _ACTION(logging.getLogger(__name__))

    assert [w.strip().split(":")[0] for w in _warnings(caplog)[1:]] == [
        str(config_dir / "groups.mk")
    ]


def test_extending_a_non_empty_default_is_named_with_the_variable(
    config_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (config_dir / "alerts.mk").write_text(
        "alert_handler_event_types = locals().setdefault('alert_handler_event_types', [])\n"
        "alert_handler_event_types += ['checkresult']\n"
    )

    _ACTION(logging.getLogger(__name__))

    warnings = _warnings(caplog)

    assert len(warnings) == 2
    assert "alert_handler_event_types = ['statechange', 'checkresult']" in warnings[0]
    assert warnings[1].strip() == f"{config_dir / 'alerts.mk'}: alert_handler_event_types"


def test_setting_a_key_of_a_non_empty_default_is_named(
    config_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (config_dir / "cmc.mk").write_text(
        "cmc_log_levels = locals().setdefault('cmc_log_levels', {})\n"
        "cmc_log_levels['cmk.alert'] = 7\n"
    )

    _ACTION(logging.getLogger(__name__))

    assert [w.strip() for w in _warnings(caplog)[1:]] == [
        f"{config_dir / 'cmc.mk'}: cmc_log_levels"
    ]


def test_assigning_a_non_empty_default_passes_silently(
    config_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (config_dir / "global.mk").write_text("alert_handler_event_types = ['checkresult']\n")

    _ACTION(logging.getLogger(__name__))

    assert not _warnings(caplog)


def test_a_file_failing_to_load_is_not_named_for_its_defaults(
    config_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (config_dir / "alerts.mk").write_text("alert_handler_event_types += ['checkresult']\n")

    _ACTION(logging.getLogger(__name__))

    warnings = _warnings(caplog)

    assert len(warnings) == 2
    assert "fail to load" in warnings[0]
    assert warnings[1].strip() == (
        f"{config_dir / 'alerts.mk'}: name 'alert_handler_event_types' is not defined"
    )
