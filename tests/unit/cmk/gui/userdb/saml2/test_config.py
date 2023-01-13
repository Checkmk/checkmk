#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.gui.userdb.saml2.config import valuespec_to_config
from cmk.gui.valuespec import DictionaryModel
from cmk.gui.wato.pages.saml2 import saml2_connection_valuespec


def _default_options(raw_config: DictionaryModel) -> DictionaryModel:
    def _replace_http_scheme(potential_url: str) -> str:
        # HTTP is prevented by the valuespec but we use it in the test data
        if not potential_url.startswith("http"):
            return potential_url
        url = potential_url.replace("http", "https")
        return url

    return {
        **{k: v for k, v in raw_config.items() if not isinstance(v, str)},
        **{k: _replace_http_scheme(v) for k, v in raw_config.items() if isinstance(v, str)},
    }


def test_minimal_options_are_valid_valuespec_options(raw_config: DictionaryModel) -> None:
    valuespec = saml2_connection_valuespec()

    valuespec.validate_datatype(_default_options(raw_config), "_not_relevant")


def test_valuespec_to_config_default_options(
    monkeypatch: pytest.MonkeyPatch, raw_config: DictionaryModel
) -> None:
    assert valuespec_to_config(raw_config)


def _options_with_custom_signature_certificate(
    raw_config: DictionaryModel, private_key_path: Path, cert_path: Path
) -> DictionaryModel:
    return {
        **_default_options(raw_config),
        **{
            "signature_certificate": (
                "custom",
                (private_key_path.read_text(), cert_path.read_text()),
            )
        },
    }


def test_signature_option_is_valid_valuespec_option(
    raw_config: DictionaryModel, signature_certificate_paths: tuple[Path, Path]
) -> None:
    valuespec = saml2_connection_valuespec()
    private_key_path, cert_path = signature_certificate_paths

    valuespec.validate_datatype(
        _options_with_custom_signature_certificate(raw_config, private_key_path, cert_path),
        "_not_relevant",
    )


def test_valuespec_to_config_signature_certificate_option(
    monkeypatch: pytest.MonkeyPatch,
    raw_config: DictionaryModel,
    signature_certificate_paths: tuple[Path, Path],
) -> None:
    monkeypatch.setattr("pathlib.Path.write_text", lambda s, t: None)
    private_key_path, cert_path = signature_certificate_paths

    assert valuespec_to_config(
        _options_with_custom_signature_certificate(raw_config, private_key_path, cert_path)
    )
