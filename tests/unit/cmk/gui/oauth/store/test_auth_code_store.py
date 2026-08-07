#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from fakeredis import FakeRedis

from cmk.gui.oauth.store._auth_code_store import AuthCodeRecord, AuthCodeStore


def _make_store() -> tuple[AuthCodeStore, FakeRedis]:
    fake = FakeRedis(decode_responses=True)
    return AuthCodeStore(fake), fake


def _make_record() -> AuthCodeRecord:
    return AuthCodeRecord(
        user_id="cmkadmin",
        client_id="test-client",
        redirect_uri="https://client.example/callback",
        scope="read",
        resource="https://host/mysite/check_mk/mcp",
        code_challenge="E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
    )


def test_store_writes_the_record_under_the_namespaced_code_key() -> None:
    store, fake = _make_store()
    record = _make_record()

    store.store("some-code", record)

    assert fake.keys() == ["mcp_auth_codes:some-code"]
    value = fake.get("mcp_auth_codes:some-code")
    assert value is not None
    assert AuthCodeRecord.model_validate_json(value) == record


def test_resource_is_optional() -> None:
    store, fake = _make_store()
    record = AuthCodeRecord(
        user_id="cmkadmin",
        client_id="test-client",
        redirect_uri="https://client.example/callback",
        scope="read",
        resource=None,
        code_challenge="E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
    )

    store.store("some-code", record)

    value = fake.get("mcp_auth_codes:some-code")
    assert value is not None
    assert AuthCodeRecord.model_validate_json(value) == record


def test_stored_codes_expire_after_ten_minutes() -> None:
    store, fake = _make_store()

    store.store("some-code", _make_record())

    assert fake.ttl("mcp_auth_codes:some-code") == 600


def test_consume_returns_the_stored_record() -> None:
    store, _fake = _make_store()
    record = _make_record()

    store.store("some-code", record)

    assert store.consume("some-code") == record


def test_consume_of_an_unknown_code_returns_none() -> None:
    store, _fake = _make_store()

    assert store.consume("never-issued") is None


def test_a_code_is_single_use() -> None:
    store, _fake = _make_store()
    store.store("some-code", _make_record())

    assert store.consume("some-code") is not None
    assert store.consume("some-code") is None
