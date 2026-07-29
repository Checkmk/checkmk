#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for cmk.crash_reporting.upload.

Network calls are intercepted with the `responses` library — no OMD env, no real network.
"""

from __future__ import annotations

import base64
import io
import json
import tarfile
import uuid as _uuid
from pathlib import Path
from urllib.parse import parse_qs

import pytest
import requests
import responses

from cmk.crash_reporting.upload import run_batch

_FAKE_UUID_1 = "11111111-1111-1111-1111-111111111111"
_FAKE_UUID_2 = "22222222-2222-2222-2222-222222222222"
_CRASH_URL = "https://crash.checkmk.com"


def _make_crash_dir(base: Path, crash_type: str, crash_id: str) -> Path:
    crash_dir = base / crash_type / crash_id
    crash_dir.mkdir(parents=True)
    info = {
        "id": crash_id,
        "crash_type": crash_type,
        "time": {"first_seen": 1000.0, "last_seen": 1000.0, "count": 1},
    }
    (crash_dir / "crash.info").write_bytes(json.dumps(info).encode())
    return crash_dir


def _field(call: responses.Call, key: str) -> str:
    body = call.request.body
    assert isinstance(body, str)  # requests encodes dict[str, str] form data as a urlencoded str
    return parse_qs(body)[key][0]


def _unpack_crashdump(call: responses.Call) -> dict[str, bytes]:
    with tarfile.open(
        mode="r:gz", fileobj=io.BytesIO(base64.b64decode(_field(call, "crashdump")))
    ) as tar:
        return {
            member.name: tar.extractfile(member).read()  # type: ignore[union-attr]
            for member in tar.getmembers()
        }


@responses.activate
@pytest.mark.parametrize(
    "bad_url",
    [
        pytest.param("http://crash.checkmk.com", id="non-https-scheme"),
        pytest.param("https://", id="https-but-empty-host"),
    ],
)
def test_non_https_url_rejected(tmp_path: Path, bad_url: str) -> None:
    """Both a non-HTTPS scheme and an HTTPS URL with no host must be refused."""
    _make_crash_dir(tmp_path, "check", _FAKE_UUID_1)
    run_batch(
        crash_report_url=bad_url,
        base_path=tmp_path,
        name="pro mysite",
        mail="test@example.com",
    )
    assert len(responses.calls) == 0


@responses.activate
def test_empty_batch_returns_early(tmp_path: Path) -> None:
    run_batch(
        crash_report_url=_CRASH_URL,
        base_path=tmp_path,
        name="pro mysite",
        mail="test@example.com",
    )
    assert len(responses.calls) == 0


@responses.activate
def test_missing_base_path(tmp_path: Path) -> None:
    run_batch(
        crash_report_url=_CRASH_URL,
        base_path=tmp_path / "nonexistent",
        name="pro mysite",
        mail="test@example.com",
    )
    assert len(responses.calls) == 0


@responses.activate
def test_crash_dir_without_crash_info_skipped(tmp_path: Path) -> None:
    """A UUID dir with no crash.info is not a complete crash: the uploader skips it
    even though the enumeration mechanism yields it."""
    (tmp_path / "check" / _FAKE_UUID_1).mkdir(parents=True)
    responses.add(responses.POST, _CRASH_URL, body=b"OK", status=200)
    run_batch(
        crash_report_url=_CRASH_URL,
        base_path=tmp_path,
        name="pro mysite",
        mail="test@example.com",
    )
    assert len(responses.calls) == 0


@responses.activate
def test_200_ok_posts_correct_fields(tmp_path: Path) -> None:
    _make_crash_dir(tmp_path, "check", _FAKE_UUID_1)
    responses.add(responses.POST, _CRASH_URL, body=b"OK abc123", status=200)
    run_batch(
        crash_report_url=_CRASH_URL,
        base_path=tmp_path,
        name="pro mysite",
        mail="test@example.com",
    )
    assert len(responses.calls) == 1
    assert _field(responses.calls[0], "name") == "pro mysite"
    assert _field(responses.calls[0], "mail") == "test@example.com"
    assert len(_field(responses.calls[0], "crashdump")) > 0


@responses.activate
def test_crashdump_packs_all_files(tmp_path: Path) -> None:
    crash_dir = _make_crash_dir(tmp_path, "check", _FAKE_UUID_1)
    (crash_dir / "agent_output").write_bytes(b"hi")
    responses.add(responses.POST, _CRASH_URL, body=b"OK abc123", status=200)
    run_batch(
        crash_report_url=_CRASH_URL,
        base_path=tmp_path,
        name="pro mysite",
        mail="test@example.com",
    )
    unpacked = _unpack_crashdump(responses.calls[0])
    # On disk crash.info keeps its name — no crash_info remapping like the mapping path.
    assert unpacked["agent_output"] == b"hi"
    assert json.loads(unpacked["crash.info"])["id"] == _FAKE_UUID_1


@responses.activate
def test_crashdump_skips_dotfiles(tmp_path: Path) -> None:
    # Note: not the real ".uploaded" marker — that would make iter_crash_dirs skip
    # the whole crash dir before we even get to packing it.
    crash_dir = _make_crash_dir(tmp_path, "check", _FAKE_UUID_1)
    (crash_dir / ".hidden").write_bytes(b"secret")
    responses.add(responses.POST, _CRASH_URL, body=b"OK abc123", status=200)
    run_batch(
        crash_report_url=_CRASH_URL,
        base_path=tmp_path,
        name="pro mysite",
        mail="test@example.com",
    )
    assert set(_unpack_crashdump(responses.calls[0])) == {"crash.info"}


@responses.activate
@pytest.mark.parametrize(
    ("status", "body", "terminal"),
    [
        pytest.param(200, b"OK abc123", True, id="200-ok-success"),
        pytest.param(200, b"FAIL: duplicate", True, id="200-non-ok-rejected"),
        pytest.param(400, b"bad request", True, id="4xx-rejected"),
        pytest.param(413, b"too large", True, id="413-rejected"),
        pytest.param(500, b"internal error", False, id="5xx-transient"),
    ],
)
def test_response_classification_marks_only_terminal_outcomes(
    tmp_path: Path, status: int, body: bytes, terminal: bool
) -> None:
    """SUCCESS and REJECTED are terminal and get the `.uploaded` marker; a TRANSIENT
    (5xx) outcome stays unmarked so it is retried next tick. The crash dir itself is
    retained regardless — the uploader never deletes it."""
    crash_dir = _make_crash_dir(tmp_path, "check", _FAKE_UUID_1)
    responses.add(responses.POST, _CRASH_URL, body=body, status=status)
    run_batch(
        crash_report_url=_CRASH_URL,
        base_path=tmp_path,
        name="pro mysite",
        mail="test@example.com",
    )
    assert len(responses.calls) == 1
    assert crash_dir.exists()
    assert (crash_dir / ".uploaded").exists() is terminal


@responses.activate
def test_rate_limited_stops_batch_and_keeps_crashes_unmarked(tmp_path: Path) -> None:
    """429 means come back later: marking would drop the crash permanently, and sending
    the rest of the batch would walk into the same limit."""
    _make_crash_dir(tmp_path, "check", _FAKE_UUID_1)
    _make_crash_dir(tmp_path, "check", _FAKE_UUID_2)
    responses.add(responses.POST, _CRASH_URL, body=b"slow down", status=429)
    run_batch(
        crash_report_url=_CRASH_URL,
        base_path=tmp_path,
        name="pro mysite",
        mail="test@example.com",
    )
    assert len(responses.calls) == 1
    assert not (tmp_path / "check" / _FAKE_UUID_1 / ".uploaded").exists()
    assert not (tmp_path / "check" / _FAKE_UUID_2 / ".uploaded").exists()


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(requests.exceptions.ConnectionError("connection refused"), id="refused"),
        pytest.param(requests.exceptions.ReadTimeout("read timed out"), id="stalled"),
    ],
)
@responses.activate
def test_post_failure_stops_batch_early(tmp_path: Path, error: Exception) -> None:
    _make_crash_dir(tmp_path, "check", _FAKE_UUID_1)
    _make_crash_dir(tmp_path, "check", _FAKE_UUID_2)
    responses.add(responses.POST, _CRASH_URL, body=error)
    run_batch(
        crash_report_url=_CRASH_URL,
        base_path=tmp_path,
        name="pro mysite",
        mail="test@example.com",
    )
    assert len(responses.calls) == 1
    assert not (tmp_path / "check" / _FAKE_UUID_1 / ".uploaded").exists()
    assert not (tmp_path / "check" / _FAKE_UUID_2 / ".uploaded").exists()


def _make_10_crash_dirs(tmp_path: Path) -> list[str]:
    uuids = [str(_uuid.UUID(int=i)) for i in range(10)]
    for uid in uuids:
        _make_crash_dir(tmp_path, "check", uid)
    return uuids


@responses.activate
def test_two_runs_drain_10_dir_backlog(tmp_path: Path) -> None:
    """SUCCESS marks a crash uploaded, so a second run picks up the remainder —
    the queue drains instead of re-uploading the same 50 dirs forever."""
    uuids = _make_10_crash_dirs(tmp_path)
    for _ in range(60):
        responses.add(responses.POST, _CRASH_URL, body=b"OK x", status=200)

    run_batch(
        crash_report_url=_CRASH_URL,
        base_path=tmp_path,
        name="pro mysite",
        mail="test@example.com",
        max_crashes=5,
    )
    assert len(responses.calls) == 5

    run_batch(
        crash_report_url=_CRASH_URL,
        base_path=tmp_path,
        name="pro mysite",
        mail="test@example.com",
        max_crashes=5,
    )
    assert len(responses.calls) == 10  # the remaining 10 were processed, not a repeat

    marked = {uid for uid in uuids if (tmp_path / "check" / uid / ".uploaded").exists()}
    assert marked == set(uuids)


@responses.activate
def test_rejected_crash_not_retried(tmp_path: Path) -> None:
    """REJECTED is also terminal: retrying a permanent 4xx would starve the queue
    just like an unmarked SUCCESS would."""
    _make_crash_dir(tmp_path, "check", _FAKE_UUID_1)
    responses.add(responses.POST, _CRASH_URL, body=b"bad request", status=400)
    run_batch(
        crash_report_url=_CRASH_URL,
        base_path=tmp_path,
        name="pro mysite",
        mail="test@example.com",
    )
    assert len(responses.calls) == 1
    assert (tmp_path / "check" / _FAKE_UUID_1 / ".uploaded").exists()

    # Second run must not re-POST the already-rejected crash
    run_batch(
        crash_report_url=_CRASH_URL,
        base_path=tmp_path,
        name="pro mysite",
        mail="test@example.com",
    )
    assert len(responses.calls) == 1


@responses.activate
def test_transient_crash_is_retried(tmp_path: Path) -> None:
    """TRANSIENT (5xx) must NOT be marked, so it is retried next tick."""
    _make_crash_dir(tmp_path, "check", _FAKE_UUID_1)
    responses.add(responses.POST, _CRASH_URL, body=b"internal error", status=500)
    responses.add(responses.POST, _CRASH_URL, body=b"OK abc", status=200)
    run_batch(
        crash_report_url=_CRASH_URL,
        base_path=tmp_path,
        name="pro mysite",
        mail="test@example.com",
    )
    assert len(responses.calls) == 1
    assert not (tmp_path / "check" / _FAKE_UUID_1 / ".uploaded").exists()

    run_batch(
        crash_report_url=_CRASH_URL,
        base_path=tmp_path,
        name="pro mysite",
        mail="test@example.com",
    )
    assert len(responses.calls) == 2
    assert (tmp_path / "check" / _FAKE_UUID_1 / ".uploaded").exists()


@responses.activate
def test_dry_run_skips_post(tmp_path: Path) -> None:
    """A dry run must be a no-op: no POST, and no `.uploaded` marker — otherwise
    a later real run would silently skip crashes the dry run never uploaded."""
    crash_dir = _make_crash_dir(tmp_path, "check", _FAKE_UUID_1)
    run_batch(
        crash_report_url=_CRASH_URL,
        base_path=tmp_path,
        name="pro mysite",
        mail="test@example.com",
        dry_run=True,
    )
    assert len(responses.calls) == 0
    assert not (crash_dir / ".uploaded").exists()
