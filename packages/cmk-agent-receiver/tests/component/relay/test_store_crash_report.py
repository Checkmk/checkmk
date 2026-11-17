#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import io
import json
import tarfile
import uuid
from http import HTTPStatus
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cmk.agent_receiver.lib.config import Config
from cmk.agent_receiver.relay.api.routers.relays import dependencies
from cmk.agent_receiver.relay.api.routers.relays.handlers import store_crash_report
from cmk.agent_receiver.relay.api.routers.relays.handlers.store_crash_report import (
    StoreCrashReportHandler,
)
from cmk.agent_receiver.relay.lib.shared_types import RelayID
from cmk.ccc import tar_archive
from cmk.testlib.agent_receiver.clients import RelayClient, RelayRegistrationClient
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock, User

CRASH_TYPE = "agent"


@pytest.fixture
def crashes_dir(site_context: Config) -> Path:
    crashes = site_context.crashes_dir
    crashes.parent.mkdir(parents=True)  # var/check_mk, where the staging dirs are created
    return crashes


@pytest.fixture
def relay(test_client: TestClient, user: User, site: SiteMock) -> RelayClient:
    relay_id = RelayID(str(uuid.uuid4()))
    site.set_scenario([], [(relay_id, OP.ADD)])
    RelayRegistrationClient(test_client, site.site_name).register(str(uuid.uuid4()), relay_id, user)
    return RelayClient(test_client, site.site_name, relay_id)


def test_forwarded_crash_lands_where_the_consolidation_cron_looks(
    crashes_dir: Path, relay: RelayClient
) -> None:
    crash_id = str(uuid.uuid4())

    response = relay.submit_crash(CRASH_TYPE, crash_id, crash_archive())

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    crash_dir = crashes_dir / CRASH_TYPE / crash_id
    assert json.loads((crash_dir / "crash.info").read_text())["crash_type"] == CRASH_TYPE
    assert (crash_dir / "agent_output").read_bytes() == b"some agent output"


def test_resending_the_same_crash_id_does_not_duplicate(
    crashes_dir: Path, relay: RelayClient
) -> None:
    """The relay re-sends when its delete failed or the response never arrived."""
    crash_id = str(uuid.uuid4())

    assert relay.submit_crash(CRASH_TYPE, crash_id, crash_archive()).status_code == (
        HTTPStatus.NO_CONTENT
    )
    assert relay.submit_crash(CRASH_TYPE, crash_id, crash_archive()).status_code == (
        HTTPStatus.NO_CONTENT
    )

    assert [p.name for p in (crashes_dir / CRASH_TYPE).iterdir()] == [crash_id]


def test_a_resend_refills_a_crash_dir_left_empty_by_the_consolidation_cron(
    crashes_dir: Path, relay: RelayClient
) -> None:
    """The cron unlinks a crash dir's files and rmdir's it under suppress(OSError), so a
    failed rmdir leaves the dir behind empty. Skipping a re-send on the dir rather than on
    crash.info would strand that crash: the relay drops its copy on the 204."""
    crash_id = str(uuid.uuid4())
    (crashes_dir / CRASH_TYPE / crash_id).mkdir(parents=True)

    response = relay.submit_crash(CRASH_TYPE, crash_id, crash_archive())

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    assert (crashes_dir / CRASH_TYPE / crash_id / "crash.info").is_file()


@pytest.mark.parametrize(
    "archive",
    [
        pytest.param(b"this is not a gzip stream", id="not_a_gzip_stream"),
        pytest.param(b"\x1f\x8b", id="gzip_magic_only"),
        pytest.param(b"\x1f\x8b\x08", id="gzip_header_cut_after_the_method_byte"),
    ],
)
def test_undecodable_archive_is_rejected_as_terminal(
    crashes_dir: Path, relay: RelayClient, archive: bytes
) -> None:
    """Each body fails in a different exception family. One the handler does not catch
    answers 500, which stops the relay's whole batch instead of dropping one crash."""
    response = relay.submit_crash(CRASH_TYPE, str(uuid.uuid4()), archive)

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.text
    assert not crashes_dir.exists()


def test_an_archive_that_unpacks_past_the_limit_is_rejected(
    crashes_dir: Path, relay: RelayClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """gzip reaches ~1000:1, so without a bound one small body fills the site's disk. 400
    rather than 500: the relay must drop such an archive, not retry it forever."""
    monkeypatch.setattr(
        store_crash_report,
        "_CRASH_LIMITS",
        tar_archive.ArchiveLimits(raw_limit_bytes=4096, size_limit_bytes=1024),
    )

    response = relay.submit_crash(CRASH_TYPE, str(uuid.uuid4()), crash_archive(payload=b"x" * 4096))

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.text
    assert not crashes_dir.exists()


def test_a_member_traversing_out_of_the_archive_is_rejected(
    crashes_dir: Path, relay: RelayClient
) -> None:
    """tar_archive rejects the member before extracting it. Without that check it lands
    outside the extraction root, anywhere the site user can reach."""
    escaped = crashes_dir.parent.parent / "escaped"

    response = relay.submit_crash(CRASH_TYPE, str(uuid.uuid4()), crash_archive("../../escaped"))

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.text
    assert not escaped.exists()


def test_no_staging_dir_is_left_behind(crashes_dir: Path, relay: RelayClient) -> None:
    """Staging lives beside crashes_dir; a leak there would accumulate silently."""
    relay.submit_crash(CRASH_TYPE, str(uuid.uuid4()), crash_archive())
    relay.submit_crash(CRASH_TYPE, str(uuid.uuid4()), b"not a gzip stream")

    assert [p.name for p in crashes_dir.parent.iterdir()] == ["crashes"]


@pytest.mark.parametrize(
    "crash_type, crash_id",
    [
        pytest.param("%2e%2e", str(uuid.uuid4()), id="traversal_in_crash_type"),
        pytest.param("Agent", str(uuid.uuid4()), id="uppercase_crash_type"),
        pytest.param(CRASH_TYPE, "not-a-uuid", id="crash_id_not_a_uuid"),
        pytest.param("a" * 300, str(uuid.uuid4()), id="crash_type_longer_than_a_path_component"),
    ],
)
def test_malformed_identity_is_rejected(
    crashes_dir: Path, relay: RelayClient, crash_type: str, crash_id: str
) -> None:
    """The archive is decodable, so rejection can only come from the identity -- and a
    crash_type of ".." would otherwise store the crash beside crashes/ rather than in it."""
    response = relay.submit_crash(crash_type, crash_id, crash_archive())

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY, response.text
    assert [p.name for p in crashes_dir.parent.iterdir()] == []


def crash_archive(*extra_members: str, payload: bytes = b"some agent output") -> bytes:
    """More than one file, so the unpack is exercised beyond a lone crash.info."""
    files = {
        "crash.info": json.dumps({"crash_type": CRASH_TYPE, "exc_type": "ValueError"}).encode(),
        "agent_output": payload,
        **dict.fromkeys(extra_members, b"escaped"),
    }
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, content in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def test_a_slow_unpack_answers_503_and_the_retry_stores_the_crash(
    crashes_dir: Path, relay: RelayClient, relay_app: FastAPI
) -> None:
    """503 is not in the relay's terminal set, so it keeps the crash and retries."""
    relay_app.dependency_overrides[dependencies.get_store_crash_report_handler] = lambda: (
        StoreCrashReportHandler(crashes_base=crashes_dir, timeout=0.001)
    )
    crash_id = str(uuid.uuid4())
    archive = crash_archive(payload=bytes(24 * 1024 * 1024))

    timed_out = relay.submit_crash(CRASH_TYPE, crash_id, archive)
    relay_app.dependency_overrides.clear()
    retried = relay.submit_crash(CRASH_TYPE, crash_id, archive)

    assert timed_out.status_code == HTTPStatus.SERVICE_UNAVAILABLE, timed_out.text
    assert retried.status_code == HTTPStatus.NO_CONTENT, retried.text
    assert (crashes_dir / CRASH_TYPE / crash_id / "crash.info").is_file()


def test_a_site_side_failure_is_not_reported_as_a_bad_archive(
    crashes_dir: Path, relay: RelayClient
) -> None:
    """The archive decoded, so the fault is the site's. A 400 here would make the relay
    drop a crash the site was unable to store."""
    # A regular file rather than a chmod: the mkdir of the type dir then fails after the
    # extraction, and unlike a mode bit it still fails when CI runs the suite as root.
    crashes_dir.write_bytes(b"")

    with pytest.raises(NotADirectoryError):
        relay.submit_crash(CRASH_TYPE, str(uuid.uuid4()), crash_archive())

    assert [p.name for p in crashes_dir.parent.iterdir()] == ["crashes"]


def test_a_rename_collision_keeps_the_dir_already_there_and_drops_the_crash(
    crashes_dir: Path, relay: RelayClient
) -> None:
    """rename cannot replace a non-empty dir, so a target left behind by a partial
    cleanup wins and the freshly unpacked copy goes with the staging dir."""
    crash_id = str(uuid.uuid4())
    (target_dir := crashes_dir / CRASH_TYPE / crash_id).mkdir(parents=True)
    (stray := target_dir / "left_by_a_partial_cleanup").write_bytes(b"stray")

    response = relay.submit_crash(CRASH_TYPE, crash_id, crash_archive())

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    assert stray.read_bytes() == b"stray"
    assert not (target_dir / "crash.info").exists()
