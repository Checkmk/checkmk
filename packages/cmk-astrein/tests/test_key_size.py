#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path

from cmk.astrein.checker_key_size import KeySizeUnitTestChecker
from cmk.astrein.framework import CheckerError

_UNIT_TEST_PATH = Path("/repo/tests/unit/test_foo.py")
_REPO_ROOT = Path("/repo")
_NON_TEST_PATH = Path("/repo/cmk/some_module.py")


def _check(code: str, file_path: Path = _UNIT_TEST_PATH) -> list[CheckerError]:
    checker = KeySizeUnitTestChecker(file_path, _REPO_ROOT, code)
    return checker.check(ast.parse(code))


def test_ignores_non_unit_test_files() -> None:
    assert _check("PrivateKey.generate_rsa()", file_path=_NON_TEST_PATH) == []


def test_matches_unit_test_files() -> None:
    errors = _check("PrivateKey.generate_rsa()")
    assert len(errors) == 1


def test_matches_nested_unit_test_path() -> None:
    errors = _check(
        "PrivateKey.generate_rsa()",
        file_path=Path("/repo/non-free/packages/foo/tests/unit/test_bar.py"),
    )
    assert len(errors) == 1


def test_replace_builtin_signature_cert_without_key_size() -> None:
    errors = _check("replace_builtin_signature_cert(config)")
    assert len(errors) == 1


def test_replace_builtin_signature_cert_with_key_size() -> None:
    assert _check("replace_builtin_signature_cert(config, default_key_size=1024)") == []


def test_create_key_without_key_size() -> None:
    errors = _check("mode._create_key()")
    assert len(errors) == 1


def test_create_key_with_key_size() -> None:
    assert _check("mode._create_key(default_key_size=1024)") == []


def test_key_mgmt_generate_key_without_key_size() -> None:
    errors = _check("key_mgmt.generate_key()")
    assert len(errors) == 1


def test_key_mgmt_generate_key_with_key_size() -> None:
    assert _check("key_mgmt.generate_key(key_size=1024)") == []


def test_other_generate_key_ignored() -> None:
    assert _check("other.generate_key()") == []


def test_initialize_site_ca_without_key_size() -> None:
    errors = _check("mgr.initialize_site_ca()")
    assert len(errors) == 1


def test_initialize_site_ca_with_key_size() -> None:
    assert _check("mgr.initialize_site_ca(key_size=1024)") == []


def test_root_ca_load_or_create_without_key_size() -> None:
    errors = _check("RootCA.load_or_create(path)")
    assert len(errors) == 1


def test_root_ca_load_or_create_with_key_size() -> None:
    assert _check("RootCA.load_or_create(path, key_size=1024)") == []


def test_private_key_generate_rsa_without_key_size() -> None:
    errors = _check("PrivateKey.generate_rsa()")
    assert len(errors) == 1


def test_private_key_generate_rsa_with_key_size() -> None:
    assert _check("PrivateKey.generate_rsa(key_size=1024)") == []


def test_cert_generate_self_signed_without_key_size() -> None:
    errors = _check('CertificateWithPrivateKey.generate_self_signed(common_name="test")')
    assert len(errors) == 1


def test_cert_generate_self_signed_with_key_size() -> None:
    assert (
        _check('CertificateWithPrivateKey.generate_self_signed(common_name="test", key_size=1024)')
        == []
    )


def test_wrong_key_size_value() -> None:
    errors = _check("PrivateKey.generate_rsa(key_size=2048)")
    assert len(errors) == 1
