#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import argparse

import pytest

from cmk.password_store.v1_unstable import (
    _convenience as mocktarget,
)
from cmk.password_store.v1_unstable import (
    parser_add_secret_option,
    resolve_secret_option,
    Secret,
)


def test_secret_parser_mandatory() -> None:
    parser = argparse.ArgumentParser()
    parser_add_secret_option(
        parser,
        short="-s",
        long="--secret",
        help="A secret",
    )

    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_secret_parser_optional() -> None:
    parser = argparse.ArgumentParser()
    parser_add_secret_option(
        parser,
        short="-s",
        long="--secret",
        help="A secret",
        required=False,
    )
    # this is ok
    args = parser.parse_args([])
    # but this raises:
    with pytest.raises(TypeError):
        resolve_secret_option(args, "secret")


def test_secret_parser_resolve_explicit() -> None:
    parser = argparse.ArgumentParser()
    parser_add_secret_option(
        parser,
        short="-s",
        long="--secret",
        help="A secret",
    )
    args = parser.parse_args(["--secret", "mysecret"])
    secret = resolve_secret_option(args, "secret")
    assert isinstance(secret, Secret)
    assert secret.reveal() == "mysecret"


def test_secret_parser_resolve_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    option = "hurray:/path/to/secret"
    monkeypatch.setattr(
        mocktarget, "dereference_secret", {option: Secret("mystoredsecret")}.__getitem__
    )

    parser = argparse.ArgumentParser()
    parser_add_secret_option(
        parser,
        short="-s",
        long="--secret",
        help="A secret",
    )
    args = parser.parse_args(["--secret-id", "hurray:/path/to/secret"])
    secret = resolve_secret_option(args, "secret")
    assert isinstance(secret, Secret)
    assert secret.reveal() == "mystoredsecret"
