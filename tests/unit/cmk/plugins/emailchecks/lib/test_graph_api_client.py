#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.password_store.v1 import Secret
from cmk.plugins.emailchecks.lib.graph_api_client import (
    AuthorityURLs,
    GraphApiClient,
)
from cmk.server_side_programs.v1 import ObfuscatedStorage, Storage

_IDENT = "graph_api_emailchecks"
_HOST = "my_host"


class _ReversingObfuscator:
    def obfuscate(self, value: Secret[str], /) -> bytes:
        return value.reveal().encode()[::-1]

    def deobfuscate(self, raw: bytes, /) -> Secret[str]:
        return Secret(raw[::-1].decode())


@pytest.fixture(name="secrets")
def fixture_secrets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> ObfuscatedStorage[Secret[str]]:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path / "storage"))
    return ObfuscatedStorage(_IDENT, _HOST, _ReversingObfuscator())


def _client(secrets: ObfuscatedStorage[Secret[str]]) -> GraphApiClient:
    return GraphApiClient(
        tenant="tenant",
        client="client",
        secret="secret",
        authority_urls=AuthorityURLs("login", "resource", "base"),
        secrets=secrets,
        storage=Storage(_IDENT, _HOST),
        initial_access_token="initial access",
        initial_refresh_token="initial refresh",
    )


def test_client_uses_initial_tokens(secrets: ObfuscatedStorage[Secret[str]]) -> None:
    client = _client(secrets)
    assert (client.access_token, client.refresh_token) == ("initial access", "initial refresh")


def test_client_persists_tokens(secrets: ObfuscatedStorage[Secret[str]]) -> None:
    client = _client(secrets)
    client.access_token = Secret("new access")
    client.refresh_token = Secret("new refresh")

    client = _client(secrets)
    assert (client.access_token, client.refresh_token) == ("new access", "new refresh")
