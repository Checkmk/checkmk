#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from pathlib import Path
from typing import TypedDict

import pytest
from pytest_mock import MockerFixture

from livestatus import SiteId

from cmk.utils.store import load_text_from_file

from cmk.gui.watolib.config_domains import ConfigDomainCACertificates

remote1_newer = (
    "-----BEGIN CERTIFICATE-----\n"
    "MIIDJzCCAg+gAwIBAgIUZdMlfmyW9c/sQmsj2JvQGcETY6swDQYJKoZIhvcNAQEL\n"
    "BQAwKTEnMCUGA1UEAwweU2l0ZSAnaGV1dGVfcmVtb3RlXzEnIGxvY2FsIENBMCAX\n"
    "DTIyMTAyMTE5NTY0OVoYDzMwMjEwMjIxMTk1NjQ5WjApMScwJQYDVQQDDB5TaXRl\n"
    "ICdoZXV0ZV9yZW1vdGVfMScgbG9jYWwgQ0EwggEiMA0GCSqGSIb3DQEBAQUAA4IB\n"
    "DwAwggEKAoIBAQDIFNGAu9upENKMjtyjwWBSpNzCizY8x7GWcdCVmQtIMxnmPu7d\n"
    "+/zvKdSraVVRiL14BH3entj852YYbPxhUWWyamzUZULZMPykADsiT+ZDqGnqlvbr\n"
    "N2tDos2r6TG17ttLbSxEa+q7nbJbW606yxNuTzBpD1ab5SoRZDH8wqv52ZRl7e2t\n"
    "PQEgjE6ZP549BNCei80cNpUXmBxsOZ9nkR0/1iTlKweOYZ2rFOkQ4QnDhWYW3luK\n"
    "npkjFPuFnYkf6LoTo5Bb/LNUynHWAU+C6ODt5X1wB2G2pM9VZeQX98j262wY73DZ\n"
    "9zKp97y5OWbjG9YqPGFbnXM9jMydbsugYQllAgMBAAGjRTBDMB0GA1UdDgQWBBS8\n"
    "wu/OK33wfinksRH8PZAryiA+sDASBgNVHRMBAf8ECDAGAQH/AgEAMA4GA1UdDwEB\n"
    "/wQEAwIBBjANBgkqhkiG9w0BAQsFAAOCAQEAThknEL61UjfmPSmnxzTPIWyva/L0\n"
    "txxzrxEYDG0hfS/qKvDo/FLMOLzf6EUH+XAYJyCuZYmUl0Xiw89q4eZ2835v/vUq\n"
    "4VAukxMPZA2cDXHeTfXOOf5VtZ243T/EcFfKjYnXHFUFJSczFV0D0vVDpLt/kSsu\n"
    "kuTuk3AqVUemMu7hZcT3JisfiXIT+qXRpgYWeDBSLm1vVHRHkBAokwNu+tBpLlRA\n"
    "A1ibM7hmJZTxbJgFHh6FSLDG+pTEl1Ou6fa4EBTLYl150Z7apkxyOzsDRFPyIbln\n"
    "lfkHm8yFtG6XWfPWVd2KhVvAd41qpa/jwPQbyXo6rqfR4MfhbAgGtxI+gA==\n"
    "-----END CERTIFICATE-----\n"
)

remote1_older = (
    "-----BEGIN CERTIFICATE-----\n"
    "MIIDJzCCAg+gAwIBAgIUBVdtL+6iblAgxPDPO8nOB5AbHpMwDQYJKoZIhvcNAQEL\n"
    "BQAwKTEnMCUGA1UEAwweU2l0ZSAnaGV1dGVfcmVtb3RlXzEnIGxvY2FsIENBMCAX\n"
    "DTIyMTAyMTE3MDAwMloYDzMwMjEwMjIxMTcwMDAyWjApMScwJQYDVQQDDB5TaXRl\n"
    "ICdoZXV0ZV9yZW1vdGVfMScgbG9jYWwgQ0EwggEiMA0GCSqGSIb3DQEBAQUAA4IB\n"
    "DwAwggEKAoIBAQCsmMtnXPI3IUvZu8RSAJfjbP9PAwqFbkYpUboj7x8P8jBtiYyK\n"
    "sWNTZeSTs0HmvHSdc4VCVfc7ggM7Rv8KI/mz7Kn3UKVMl2d8vKqnt8oP7YVALSKu\n"
    "6Uig9z48Pou2sB/p/cKdhB/6IyJ5sKVhSmr+iYfHfCS0lV8fXWi/D6zPPeASCiP6\n"
    "n1QxXyDng3my7RbQCO3cOMrWLt6YD17+5I461hyNJ2i1li8pXB9MGgJwbndTRUGX\n"
    "ik0hPqKmi7zZqUU5jErav9lrBbohIb+divAFiybaJH5kQoP23PpE4PY0ZJ0qA5T3\n"
    "ei+3OrweY9uU3oBgHp8t9xsMwZA1LoGuDKRXAgMBAAGjRTBDMB0GA1UdDgQWBBTS\n"
    "d2DLOFC7vrew6kJkDLKt6/QQwTASBgNVHRMBAf8ECDAGAQH/AgEAMA4GA1UdDwEB\n"
    "/wQEAwIBBjANBgkqhkiG9w0BAQsFAAOCAQEAEyIin6GaEW65bqDiEkss0X3xucCK\n"
    "QGhJkx7ph11xGFkGAdiC2erD1eiBDI/JBx/nZ6zUmA45/FLeyVCquzEMh9WOd62b\n"
    "R1XhUSRNkcLjmWEkCmenA/oJHOuKonM+J4ZRZ2WsWXZ6QyoiMoDu4VfdGAKXyvy/\n"
    "qZNBeaG3tOpV4y0qvfLraYCUfIrXASw5zWXdBbX0pqpZwSdwRxui1L1/0YkTqaD+\n"
    "8uwsKs+yMDtqgJbGIU/DpjmFf9yuiCbHpQb5r/cZNeY0xwv59M3IrhTHjoYapcyZ\n"
    "olHRFjl7JNqsLM39olnSpi85GFL0f2w7CEua1tStZKvW+YxBP6bYkFk3+A==\n"
    "-----END CERTIFICATE-----\n"
)

remote2 = (
    "-----BEGIN CERTIFICATE-----\n"
    "MIIDJzCCAg+gAwIBAgIUCJ8Xnhabxz14Gilh1SIRJTvSIAMwDQYJKoZIhvcNAQEL\n"
    "BQAwKTEnMCUGA1UEAwweU2l0ZSAnaGV1dGVfcmVtb3RlXzInIGxvY2FsIENBMCAX\n"
    "DTIyMTAyMTE3MDAxMloYDzMwMjEwMjIxMTcwMDEyWjApMScwJQYDVQQDDB5TaXRl\n"
    "ICdoZXV0ZV9yZW1vdGVfMicgbG9jYWwgQ0EwggEiMA0GCSqGSIb3DQEBAQUAA4IB\n"
    "DwAwggEKAoIBAQDTdYUhP2ojcyR54fGh2uFh29ea6u5CnhVlMYyvhSm+vjRefFRF\n"
    "7x+ngc58xbUk3fOwBfAW3lsuC/VaA+YUVIjQpw4KHGa7dpjMb3mEXnl8svJUg9RA\n"
    "GQVW+7yMcqFHm6Dqujt2HUgKY9VABmgbFBbdZRSR6pfGBjgb71wvxd6yh3DXDh9D\n"
    "gX4M4UhSYaZtjQt/HEmbEWAY/bNTR8eUhaFZfDRTnaXuPdHiI/TallXR2n0ZL8vT\n"
    "2sBoGdUlmjb1Lpu/qlxWdQhYL6tENP/YmRv7WsG9wLtiFdQCjOnQ2zeZaeJbmj8e\n"
    "kaeMCUtj2MIJm+bNR0sQRJv2oGePcC6kXYE9AgMBAAGjRTBDMB0GA1UdDgQWBBQ9\n"
    "MQ9DMZkgTRzAraIXSiP3sjpDdzASBgNVHRMBAf8ECDAGAQH/AgEAMA4GA1UdDwEB\n"
    "/wQEAwIBBjANBgkqhkiG9w0BAQsFAAOCAQEAgaIB2PGzO7QaHTQpWIFsxnrbS4eq\n"
    "+qVwu+F8ieM1D8NKmKh862Ze6MJxiVZSJHwzWQypllxuHJ/+8rjaCmdGFYe8cb2g\n"
    "OTT9wNp/sw3v0KFoMKALHG/dC/uanWUCFMeMg2dGRN1G76wXayFUFaH9EkbUqyuS\n"
    "DUm9Fq4RMdgypLMxFGEl6yeSTMV7McOeiZLy1aERS7/eQfjKcjrLDOqBQY/I/3iI\n"
    "RNsIlDCWtpQU7Hb3CnhYsbXPRH8wBlQes01JwcNpIiUgDLMRdbYoMM7Di7oBkgPN\n"
    "41LjJMPbVwJ4qavwFT5SX2suUO0dSniNSrIsRZob2xSqtGU4em+umCSt1w==\n"
    "-----END CERTIFICATE-----\n"
)


class _CASettings(TypedDict):
    use_system_wide_cas: bool
    trusted_cas: list[str]


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
                ["system_cert_2", "system_cert_1"],
                [],
            ),
        )
        mocker.patch.object(
            ca_config,
            "update_remote_sites_cas",
            lambda _trusted_cas: None,
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
                "",
                id="empty",
            ),
            pytest.param(
                {
                    "use_system_wide_cas": True,
                    "trusted_cas": [],
                },
                "system_cert_1\nsystem_cert_2",
                id="system cas only",
            ),
            pytest.param(
                {
                    "use_system_wide_cas": False,
                    "trusted_cas": ["custom_cert_2", "custom_cert_1"],
                },
                "custom_cert_1\ncustom_cert_2",
                id="custom cas only",
            ),
            pytest.param(
                {
                    "use_system_wide_cas": True,
                    "trusted_cas": ["custom_cert_1", "custom_cert_2"],
                },
                "custom_cert_1\ncustom_cert_2\nsystem_cert_1\nsystem_cert_2",
                id="system and custom cas",
            ),
        ],
    )
    def test_save_empty(
        self,
        mocked_ca_config: ConfigDomainCACertificates,
        ca_settings: _CASettings,
        expected_file_content: str,
    ) -> None:
        mocked_ca_config.save(
            {
                "trusted_certificate_authorities": ca_settings,
            }
        )
        assert load_text_from_file(mocked_ca_config.trusted_cas_file) == expected_file_content

    def test_remote_sites_cas(self) -> None:
        longest_validity = datetime(3021, 2, 21, 19, 56, 49)

        remote_cas = ConfigDomainCACertificates()._remote_sites_cas(
            [remote1_newer, remote1_older, remote2]
        )
        assert list(remote_cas) == [SiteId("heute_remote_1"), SiteId("heute_remote_2")]

        assert remote_cas[SiteId("heute_remote_1")].not_valid_after == longest_validity
        # also test changed order:
        remote_cas = ConfigDomainCACertificates()._remote_sites_cas([remote1_older, remote1_newer])
        assert remote_cas[SiteId("heute_remote_1")].not_valid_after == longest_validity
