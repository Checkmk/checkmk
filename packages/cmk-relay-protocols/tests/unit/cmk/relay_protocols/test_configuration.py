#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.relay_protocols.configuration import EngineConfig, LogLevel, UserEngineConfig


class TestEngingeConfig:
    def test_from_user_engine_config(self) -> None:
        uec = UserEngineConfig(num_fetchers=0, hosts=(), log_level=LogLevel.ERROR)
        _ = EngineConfig.model_validate_json(uec.model_dump_json())

    def test_site_version_trigger_interval_default(self) -> None:
        config = EngineConfig(num_fetchers=0, hosts=(), log_level=LogLevel.ERROR)
        assert config.site_version_trigger_interval == 60

    def test_checkhelper_defaults(self) -> None:
        config = EngineConfig(num_fetchers=0, hosts=(), log_level=LogLevel.ERROR)
        assert config.bin_checkhelper == Path("/opt/check-mk-relay/lib/cmc/checkhelper")
        assert config.num_checkhelpers == 5
        assert config.num_adhoc_checkhelpers == 5

    def test_load_config_written_without_num_checkhelpers(self, tmp_path: Path) -> None:
        """A config on a relay's disk may predate the field and must still load.

        A relay re-reads the last config the site pushed when it starts; right after
        an engine update that file lacks the fields added since. Rejecting it would
        make the engine fall back to its defaults and drop every host.
        """
        path = tmp_path / "config.json"
        _ = path.write_text('{"num_fetchers": 3, "hosts": [], "log_level": "ERROR"}')

        config = EngineConfig.load(path)

        assert config.num_checkhelpers == 5
        assert config.num_fetchers == 3

    def test_num_checkhelpers_is_user_configurable(self) -> None:
        # num_checkhelpers is part of the user-provided config so the site can set it.
        config = UserEngineConfig(
            num_fetchers=0, num_checkhelpers=10, hosts=(), log_level=LogLevel.ERROR
        )
        assert config.num_checkhelpers == 10
