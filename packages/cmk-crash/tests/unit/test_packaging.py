#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import io
import tarfile

from cmk.crash_reporting import crash_report_submit_payload, pack_crash_report


def _unpack(packed: bytes) -> dict[str, bytes]:
    with tarfile.open(mode="r:gz", fileobj=io.BytesIO(packed)) as tar:
        return {
            member.name: tar.extractfile(member).read()  # type: ignore[union-attr]
            for member in tar.getmembers()
        }


def test_pack_crash_report_round_trip() -> None:
    packed = pack_crash_report({"crash_info": b'{"a": 1}', "agent_output": b"hi"})
    # "crash_info" is stored as "crash.info"; other keys keep their name.
    assert _unpack(packed) == {"crash.info": b'{"a": 1}', "agent_output": b"hi"}


def test_pack_crash_report_skips_none() -> None:
    packed = pack_crash_report({"crash_info": b"{}", "agent_output": None})
    assert set(_unpack(packed)) == {"crash.info"}


def test_pack_crash_report_empty() -> None:
    assert _unpack(pack_crash_report({})) == {}


def test_crash_report_submit_payload_fields() -> None:
    payload = crash_report_submit_payload(
        name="Alice",
        mail="alice@example.com",
        serialized_crash_report={"crash_info": b"{}"},
    )

    assert [key for key, _ in payload] == ["name", "mail", "crashdump"]
    fields = dict(payload)
    assert fields["name"] == "Alice"
    assert fields["mail"] == "alice@example.com"

    # The crashdump is the base64-encoded tar.gz of the crash report.
    crashdump = fields["crashdump"]
    assert isinstance(crashdump, str)
    assert _unpack(base64.b64decode(crashdump)) == {"crash.info": b"{}"}
