#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cmk.utils.store import load_bytes_from_file

from cmk.gui.watolib.config_domains import ConfigDomainCACertificates


class TestConfigDomainCACertificates:
    @pytest.fixture(name="mocked_ca_config")
    def fixture_mocked_ca_config(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> ConfigDomainCACertificates:
        ca_config = ConfigDomainCACertificates()
        mocker.patch.object(
            ca_config,
            "trusted_cas_file",
            tmp_path / "ca-test-file",
        )
        mocker.patch.object(
            ca_config,
            "_get_system_wide_trusted_ca_certificates",
            lambda: (
                [b"system_cert_2", b"system_cert_1"],
                [],
            ),
        )
        return ca_config

    @pytest.mark.parametrize(
        ["ca_settings", "expected_file_content"],
        [
            pytest.param(
                {
                    "use_system_wide_cas": False,
                    "trusted_cas": [],
                },
                b"",
                id="empty",
            ),
            pytest.param(
                {
                    "use_system_wide_cas": True,
                    "trusted_cas": [],
                },
                b"system_cert_1\nsystem_cert_2",
                id="system cas only",
            ),
            pytest.param(
                {
                    "use_system_wide_cas": False,
                    "trusted_cas": [b"custom_cert_2", b"custom_cert_1"],
                },
                b"custom_cert_1\ncustom_cert_2",
                id="custom cas only",
            ),
            pytest.param(
                {
                    "use_system_wide_cas": True,
                    "trusted_cas": [b"custom_cert_1", b"custom_cert_2"],
                },
                b"custom_cert_1\ncustom_cert_2\nsystem_cert_1\nsystem_cert_2",
                id="system and custom cas",
            ),
        ],
    )
    def test_save_empty(
        self,
        mocked_ca_config: ConfigDomainCACertificates,
        ca_settings,
        expected_file_content: bytes,
    ) -> None:
        mocked_ca_config.save({
            "trusted_certificate_authorities": ca_settings,
        })
        assert load_bytes_from_file(mocked_ca_config.trusted_cas_file) == expected_file_content
