#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from flask.testing import FlaskClient

from cmk.werk_ids_server._db import init_db, reserve
from cmk.werk_ids_server.server import app

_SECRET = "top-secret-token"
_START = 22_222


@pytest.fixture(name="db")
def fixture_db(tmp_path: Path) -> Path:
    db = tmp_path / "werk_ids.db"
    init_db(db, _START)
    return db


@pytest.fixture(name="secret_file")
def fixture_secret_file(tmp_path: Path) -> Path:
    secret_file = tmp_path / "secret"
    secret_file.write_text(_SECRET, encoding="utf-8")
    return secret_file


@pytest.fixture(name="client")
def fixture_client(db: Path, secret_file: Path) -> Iterator[FlaskClient]:
    app.config.update(db=db, secret_file=secret_file, TESTING=True)
    with app.test_client() as client:
        yield client


def _auth(secret: str = _SECRET) -> dict[str, str]:
    return {"Authorization": f"Bearer {secret}"}


# ---------------------------------------------------------------------------
# Health / connectivity
# ---------------------------------------------------------------------------


def test_health_needs_no_auth(client: FlaskClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_connect_with_valid_secret(client: FlaskClient) -> None:
    response = client.get("/v1/connect", headers=_auth())
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_connect_without_auth_returns_json_401(client: FlaskClient) -> None:
    response = client.get("/v1/connect")
    assert response.status_code == 401
    assert response.is_json
    assert response.get_json() == {"error": "Invalid or missing authorization."}


def test_connect_with_wrong_secret_returns_json_401(client: FlaskClient) -> None:
    response = client.get("/v1/connect", headers=_auth("wrong"))
    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid or missing authorization."}


# ---------------------------------------------------------------------------
# Reserve
# ---------------------------------------------------------------------------


def test_reserve_tops_up_to_the_maximum(client: FlaskClient) -> None:
    # With 3 IDs held locally, the server hands out the remaining 10 - 3 = 7,
    # starting right after the seeded counter value.
    response = client.post("/v1/reserve", headers=_auth(), json={"local_werk_ids_count": 3})
    assert response.status_code == 200
    reserved = response.get_json()["reserved_werk_ids"]
    assert reserved == list(range(_START + 1, _START + 8))
    assert len(reserved) == 7


def test_reserve_when_already_at_max_returns_empty(client: FlaskClient) -> None:
    response = client.post("/v1/reserve", headers=_auth(), json={"local_werk_ids_count": 10})
    assert response.status_code == 200
    assert response.get_json() == {"reserved_werk_ids": []}


def test_reserve_when_above_max_returns_empty(client: FlaskClient) -> None:
    response = client.post("/v1/reserve", headers=_auth(), json={"local_werk_ids_count": 25})
    assert response.status_code == 200
    assert response.get_json() == {"reserved_werk_ids": []}


def test_reserve_does_not_consume_when_returning_empty(client: FlaskClient) -> None:
    # A no-op top-up must not advance the counter: the next real reservation
    # still starts right after the seeded value.
    client.post("/v1/reserve", headers=_auth(), json={"local_werk_ids_count": 10})
    response = client.post("/v1/reserve", headers=_auth(), json={"local_werk_ids_count": 0})
    assert response.get_json()["reserved_werk_ids"][0] == _START + 1


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="missing-field"),
        pytest.param({"local_werk_ids_count": -1}, id="negative"),
        pytest.param({"local_werk_ids_count": "5"}, id="non-int"),
        pytest.param({"local_werk_ids_count": 1.5}, id="float"),
        pytest.param({"local_werk_ids_count": None}, id="null"),
    ],
)
def test_reserve_rejects_bad_input_with_json_400(
    client: FlaskClient, payload: dict[str, object]
) -> None:
    response = client.post("/v1/reserve", headers=_auth(), json=payload)
    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Field 'local_werk_ids_count' must be a non-negative integer."
    }


def test_reserve_without_auth_returns_json_401(client: FlaskClient) -> None:
    response = client.post("/v1/reserve", json={"local_werk_ids_count": 0})
    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid or missing authorization."}


def test_reserve_ids_are_monotonic_across_requests(client: FlaskClient) -> None:
    first = client.post(
        "/v1/reserve", headers=_auth(), json={"local_werk_ids_count": 0}
    ).get_json()["reserved_werk_ids"]
    second = client.post(
        "/v1/reserve", headers=_auth(), json={"local_werk_ids_count": 0}
    ).get_json()["reserved_werk_ids"]
    assert first and second
    # No overlap, strictly increasing, contiguous across the boundary.
    assert max(first) < min(second)
    assert second[0] == first[-1] + 1


def test_secret_rotation_takes_effect_immediately(client: FlaskClient, secret_file: Path) -> None:
    assert client.get("/v1/connect", headers=_auth()).status_code == 200
    secret_file.write_text("rotated", encoding="utf-8")
    # The old secret is now rejected and the new one accepted without restart.
    assert client.get("/v1/connect", headers=_auth()).status_code == 401
    assert client.get("/v1/connect", headers=_auth("rotated")).status_code == 200


def test_reserve_logs_client_and_ids(client: FlaskClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="cmk.werk_ids_server.server"):
        client.post("/v1/reserve", headers=_auth(), json={"local_werk_ids_count": 0})
    assert any("reserved IDs" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# Database layer (direct, real SQLite)
# ---------------------------------------------------------------------------


def test_db_reserve_returns_contiguous_block(db: Path) -> None:
    assert list(reserve(db, 5)) == list(range(_START + 1, _START + 6))


def test_db_reserve_advances_counter(db: Path) -> None:
    first = list(reserve(db, 3))
    second = list(reserve(db, 3))
    assert first == list(range(_START + 1, _START + 4))
    assert second == list(range(_START + 4, _START + 7))


def test_init_db_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "werk_ids.db"
    init_db(db, _START)
    reserve(db, 5)  # advance the counter
    # Re-initialising must not reset the counter back to the start value.
    init_db(db, _START)
    assert list(reserve(db, 1)) == [_START + 6]


def test_init_db_seeds_start_value(tmp_path: Path) -> None:
    db = tmp_path / "werk_ids.db"
    init_db(db, 5_000)
    assert list(reserve(db, 1)) == [5_001]
