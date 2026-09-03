#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator

import pytest

from cmk.gui.form_specs.unstable.legacy_converter import (
    formspec_to_password_id,
    is_formspec_password,
    password_id_to_formspec,
)
from cmk.utils import password_store


@pytest.mark.parametrize(
    "value, expected",
    [
        (("cmk_postprocessed", "explicit_password", ("uuid", "secret")), ("password", "secret")),
        (("cmk_postprocessed", "stored_password", ("store-id", "")), ("store", "store-id")),
        (("password", "secret"), ("password", "secret")),
        (("store", "store-id"), ("store", "store-id")),
        ("store-id", "store-id"),
    ],
)
def test_formspec_to_password_id(value: object, expected: object) -> None:
    assert formspec_to_password_id(value) == expected


def test_formspec_to_password_id_rejects_unknown_shape() -> None:
    with pytest.raises(ValueError):
        formspec_to_password_id(("totally", "unknown", "shape"))


def test_password_id_to_formspec_stored() -> None:
    assert password_id_to_formspec(("store", "store-id")) == (
        "cmk_postprocessed",
        "stored_password",
        ("store-id", ""),
    )


def test_password_id_to_formspec_explicit_mints_id() -> None:
    kind, variant, (password_id, secret) = password_id_to_formspec(("password", "s3cr3t"))
    assert (kind, variant, secret) == ("cmk_postprocessed", "explicit_password", "s3cr3t")
    assert password_id  # an ad-hoc id is generated for the form


def test_password_id_to_formspec_passes_formspec_through() -> None:
    formspec = ("cmk_postprocessed", "stored_password", ("store-id", ""))
    assert password_id_to_formspec(formspec) == formspec


def test_password_id_to_formspec_rejects_unknown_shape() -> None:
    with pytest.raises(ValueError):
        password_id_to_formspec(("totally", "unknown", "shape"))


@pytest.mark.parametrize(
    "value, expected",
    [
        (("cmk_postprocessed", "explicit_password", ("u", "s")), True),
        (("cmk_postprocessed", "stored_password", ("id", "")), True),
        (("store", "id"), False),
        (("password", "s"), False),
        ("id", False),
    ],
)
def test_is_formspec_password(value: object, expected: bool) -> None:
    assert is_formspec_password(value) is expected


@pytest.mark.parametrize("password_id", [("password", "s3cr3t"), ("store", "my-id")])
def test_load_then_save_roundtrips(password_id: object) -> None:
    # on-disk PasswordId -> form (load) -> on-disk (save) is identity
    assert formspec_to_password_id(password_id_to_formspec(password_id)) == password_id


def test_save_then_load_stored_roundtrips() -> None:
    formspec = ("cmk_postprocessed", "stored_password", ("id", ""))
    assert password_id_to_formspec(formspec_to_password_id(formspec)) == formspec


@pytest.fixture(name="clean_password_store")
def fixture_clean_password_store() -> Iterator[None]:
    """Make sure the globally patched store file doesn't leak into other tests"""
    yield
    password_store.pending_secrets_path_site().unlink(missing_ok=True)


@pytest.mark.usefixtures("clean_password_store")
def test_extract_reads_the_converted_explicit_password() -> None:
    formspec = ("cmk_postprocessed", "explicit_password", ("uuid", "s3cr3t"))
    assert password_store.extract(formspec_to_password_id(formspec)) == "s3cr3t"


@pytest.mark.usefixtures("clean_password_store")
def test_extract_reads_the_converted_stored_password() -> None:
    password_store.save({"my-id": "s3cr3t"}, password_store.pending_secrets_path_site())
    formspec = ("cmk_postprocessed", "stored_password", ("my-id", ""))
    assert password_store.extract(formspec_to_password_id(formspec)) == "s3cr3t"
