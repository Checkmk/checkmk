#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import json
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from rich.console import Console

from cmk.werks.tool.cli.id_pool import make_paths_object, Paths, ServerStatus
from cmk.werks.tool.cli.stash import LegacyStash, Stash
from cmk.werks.tool.cli.status import (
    collect_status,
    FileInfo,
    Problem,
    render_json,
    render_status,
    SCHEMA_VERSION,
    SERVER_NOT_CHECKED,
    ServerInfo,
    StashInfo,
    Status,
)
from cmk.werks.tool.cli.werk import WerkId


def _no_werk_exists(_werk_id: WerkId) -> bool:
    return False


def _paths(tmp_path: Path, ids: Sequence[int] = (), *, secret_mode: int | None = 0o600) -> Paths:
    paths = make_paths_object(tmp_path)
    if secret_mode is not None:
        paths.secret_file.parent.mkdir(parents=True, exist_ok=True)
        paths.secret_file.write_text("s3cret", encoding="utf-8")
        paths.secret_file.chmod(secret_mode)
    paths.stash_file.parent.mkdir(parents=True, exist_ok=True)
    paths.stash_file.write_text(
        Stash(ids=list(ids)).model_dump_json(by_alias=True), encoding="utf-8"
    )
    return paths


def _collect(
    home: Path,
    paths: Paths,
    *,
    server_status: ServerStatus | None = ServerStatus.OK,
    werk_exists: Callable[[WerkId], bool] = _no_werk_exists,
) -> Status:
    return collect_status(
        home=home,
        paths=paths,
        server_url="http://werk-ids.test",
        server_status=server_status,
        werk_exists=werk_exists,
    )


# ---------------------------------------------------------------------------
# Collecting
# ---------------------------------------------------------------------------


def test_a_healthy_setup_has_no_problems(tmp_path: Path) -> None:
    status = _collect(tmp_path, _paths(tmp_path, [20_251, 20_252]))

    assert status.problems == []
    assert status.reserved_ids.count == 2
    assert status.reserved_ids.next_id == 20_251
    assert status.reserved_ids.exists is True


def test_reserved_ids_without_any_id(tmp_path: Path) -> None:
    status = _collect(tmp_path, _paths(tmp_path))

    assert status.problems == []
    assert status.reserved_ids.count == 0
    assert status.reserved_ids.next_id is None


def test_no_reserved_ids_and_unreachable_server_is_a_problem(tmp_path: Path) -> None:
    status = _collect(tmp_path, _paths(tmp_path), server_status=ServerStatus.UNREACHABLE)

    assert status.problems == [
        Problem(
            item="reserved_ids",
            problem="none reserved and the server is unavailable",
            fix="reconnect to the VPN, then 'werk new'",
        )
    ]


def test_unreachable_server_with_reserved_ids_reports_no_problem(tmp_path: Path) -> None:
    status = _collect(tmp_path, _paths(tmp_path, [20_251]), server_status=ServerStatus.UNREACHABLE)

    assert status.problems == []
    assert status.server.status == "unreachable"


def test_rejected_secret_is_a_problem(tmp_path: Path) -> None:
    status = _collect(tmp_path, _paths(tmp_path, [20_251]), server_status=ServerStatus.UNAUTHORIZED)

    assert status.problems == [
        Problem(item="server", problem="rejected your secret", fix="werk init")
    ]


def test_server_error_is_a_problem(tmp_path: Path) -> None:
    status = _collect(tmp_path, _paths(tmp_path, [20_251]), server_status=ServerStatus.ERROR)

    assert status.problems == [
        Problem(
            item="server",
            problem="answered with an error",
            fix="check http://werk-ids.test",
        )
    ]


def test_stale_reservation_is_a_problem(tmp_path: Path) -> None:
    status = _collect(
        tmp_path,
        _paths(tmp_path, [20_251, 20_252]),
        werk_exists=lambda werk_id: werk_id == WerkId(20_252),
    )

    assert status.problems == [
        Problem(
            item="reserved_ids",
            problem="werk 20252 already exists on disk",
            fix="remove 20252 from the stash",
        )
    ]


def test_a_missing_secret_is_a_problem(tmp_path: Path) -> None:
    status = _collect(tmp_path, _paths(tmp_path, [20_251], secret_mode=None), server_status=None)

    assert Problem(item="secret", problem="missing", fix="werk init") in status.problems
    assert status.secret.exists is False
    assert status.secret.mode is None
    assert status.server.status == SERVER_NOT_CHECKED


def test_a_leftover_legacy_stash_is_a_problem(tmp_path: Path) -> None:
    paths = _paths(tmp_path, [20_251])
    paths.legacy_stash_file.write_text(
        LegacyStash(ids_by_project={"cmk": [20_260]}).model_dump_json(by_alias=True),
        encoding="utf-8",
    )

    status = _collect(tmp_path, paths)

    assert status.problems == [
        Problem(
            item="legacy_stash",
            problem="exists next to the current werk ID files",
            fix="look at both stash files and merge them by hand",
        )
    ]
    assert status.legacy_stash.exists is True
    assert status.legacy_stash.path == paths.legacy_stash_file
    assert status.legacy_stash.count == 1
    assert status.legacy_stash.next_id == 20_260


# ---------------------------------------------------------------------------
# Path existence and permissions
# ---------------------------------------------------------------------------


def test_collected_paths_are_the_real_ones(tmp_path: Path) -> None:
    paths = _paths(tmp_path, [20_251])

    status = _collect(tmp_path, paths)

    assert status.secret.path == paths.secret_file
    assert status.reserved_ids.path == paths.stash_file
    assert status.legacy_stash.path == paths.legacy_stash_file


def test_existing_paths_report_their_mode(tmp_path: Path) -> None:
    paths = _paths(tmp_path, [20_251])
    paths.stash_file.chmod(0o644)

    status = _collect(tmp_path, paths)

    assert status.secret.mode == "0600"
    assert status.reserved_ids.mode == "0644"


def test_secret_readable_by_others_is_a_problem(tmp_path: Path) -> None:
    paths = _paths(tmp_path, [20_251], secret_mode=0o644)

    status = _collect(tmp_path, paths)

    assert status.problems == [
        Problem(
            item="secret",
            problem="readable by others (0644)",
            fix="chmod 600 $HOME/.config/cmk-werks/secret",
        )
    ]


def test_secret_with_restrictive_mode_is_no_problem(tmp_path: Path) -> None:
    status = _collect(tmp_path, _paths(tmp_path, [20_251], secret_mode=0o600))

    assert status.problems == []


@pytest.mark.parametrize(
    "mode", [pytest.param(0o640, id="group read"), pytest.param(0o604, id="other read")]
)
def test_any_group_or_other_access_to_the_secret_is_a_problem(tmp_path: Path, mode: int) -> None:
    status = _collect(tmp_path, _paths(tmp_path, [20_251], secret_mode=mode))

    assert len(status.problems) == 1
    assert status.problems[0].item == "secret"
    assert status.problems[0].problem.startswith("readable by others")


@pytest.mark.parametrize(
    ("server_status", "expected"),
    [
        pytest.param(None, "not_checked", id="not checked"),
        pytest.param(ServerStatus.OK, "ok", id="ok"),
        pytest.param(ServerStatus.UNAUTHORIZED, "unauthorized", id="unauthorized"),
        pytest.param(ServerStatus.UNREACHABLE, "unreachable", id="unreachable"),
        pytest.param(ServerStatus.ERROR, "error", id="error"),
    ],
)
def test_server_status_tokens_are_machine_readable(
    tmp_path: Path, server_status: ServerStatus | None, expected: str
) -> None:
    status = _collect(tmp_path, _paths(tmp_path, [20_251]), server_status=server_status)

    assert status.server.status == expected
    assert status.server.url == "http://werk-ids.test"


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _status(
    *,
    server_status: str = "ok",
    secret: FileInfo | None = None,
    reserved_ids: StashInfo | None = None,
    legacy_stash: StashInfo | None = None,
    problems: Sequence[Problem] = (),
) -> Status:
    return Status(
        server=ServerInfo(url="http://werk-ids.test", status=server_status),
        secret=secret or FileInfo(path=Path("/h/secret"), exists=True, mode="0600"),
        reserved_ids=reserved_ids
        or StashInfo(path=Path("/h/reserved"), exists=True, mode="0600", count=3, next_id=20_251),
        legacy_stash=legacy_stash
        or StashInfo(path=Path("/h/legacy"), exists=False, mode=None, count=0, next_id=None),
        problems=list(problems),
    )


# Most of the rendering has nothing to do with the home directory: the paths of these
# statuses are below none.
_NO_HOME = Path("/nowhere")


def _rendered(home: Path, status: Status) -> str:
    stream = io.StringIO()
    render_status(home, status, Console(file=stream, width=120, no_color=True, highlight=False))
    return "\n".join(line.rstrip() for line in stream.getvalue().split("\n"))


def test_render_shows_both_sections() -> None:
    output = _rendered(_NO_HOME, _status())

    assert "WERK IDS" in output
    assert "PROBLEMS" in output
    assert "✓ none found" in output


def test_render_lists_every_item_with_its_mode() -> None:
    output = _rendered(_NO_HOME, _status())

    assert "reachable, secret accepted" in output
    assert "http://werk-ids.test" in output
    assert "/h/secret" in output
    assert "0600" in output
    assert "3 reserved, next 20251" in output


def test_render_hides_the_legacy_stash_while_it_does_not_exist() -> None:
    assert "legacy stash" not in _rendered(_NO_HOME, _status())


def test_render_shows_a_leftover_legacy_stash() -> None:
    output = _rendered(
        _NO_HOME,
        _status(
            legacy_stash=StashInfo(
                path=Path("/h/.cmk-werk-ids"), exists=True, mode="0600", count=2, next_id=11_120
            )
        ),
    )

    assert "legacy stash" in output
    assert "/h/.cmk-werk-ids" in output


def test_render_lists_problems_with_their_fix() -> None:
    output = _rendered(
        _NO_HOME,
        _status(
            problems=[
                Problem(item="secret", problem="readable by others (0644)", fix="chmod 600 x"),
                Problem(item="server", problem="rejected your secret", fix="werk init"),
            ]
        ),
    )

    assert "PROBLEM" in output
    assert "FIX" in output
    assert "readable by others (0644)" in output
    assert "chmod 600 x" in output
    assert "rejected your secret" in output
    assert "none found" not in output


def test_render_does_not_fold_a_long_path_when_wide_enough() -> None:
    long_path = "/opt/user/.local/state/cmk-werks/reserved-ids"
    output = _rendered(
        _NO_HOME,
        _status(
            reserved_ids=StashInfo(
                path=Path(long_path), exists=True, mode="0600", count=1, next_id=20_251
            )
        ),
    )

    assert long_path in output


def test_render_replaces_the_home_directory_by_its_name(tmp_path: Path) -> None:
    secret = tmp_path / ".config/cmk-werks/secret"

    output = _rendered(tmp_path, _status(secret=FileInfo(path=secret, exists=True, mode="0600")))

    assert "$HOME/.config/cmk-werks/secret" in output
    assert str(tmp_path) not in output


def test_render_leaves_a_path_outside_the_home_directory_alone(tmp_path: Path) -> None:
    outside = tmp_path.parent / "elsewhere/secret"

    output = _rendered(tmp_path, _status(secret=FileInfo(path=outside, exists=True, mode="0600")))

    assert str(outside) in output


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def test_json_is_a_single_document_with_a_schema_version() -> None:
    document = json.loads(render_json(_NO_HOME, _status()))

    assert document["schema_version"] == SCHEMA_VERSION
    assert document["server"] == {"url": "http://werk-ids.test", "status": "ok"}


def test_json_values_are_typed_not_prose() -> None:
    document = json.loads(render_json(_NO_HOME, _status()))

    assert document["reserved_ids"] == {
        "path": "/h/reserved",
        "exists": True,
        "mode": "0600",
        "count": 3,
        "next_id": 20_251,
    }


def test_json_keeps_a_fixed_shape() -> None:
    # the tables hide the legacy stash while it does not exist; the document must not
    document = json.loads(render_json(_NO_HOME, _status()))

    assert set(document) == {
        "schema_version",
        "server",
        "secret",
        "reserved_ids",
        "legacy_stash",
        "problems",
    }
    assert document["legacy_stash"] == {
        "path": "/h/legacy",
        "exists": False,
        "mode": None,
        "count": 0,
        "next_id": None,
    }


def test_json_problem_items_reference_the_section_keys() -> None:
    document = json.loads(
        render_json(
            _NO_HOME,
            _status(
                problems=[
                    Problem(item="reserved_ids", problem="p", fix="f"),
                    Problem(item="legacy_stash", problem="p", fix="f"),
                ]
            ),
        )
    )

    for problem in document["problems"]:
        assert problem["item"] in document, f"{problem['item']} is not a section key"
    assert document["problems"][0] == {"item": "reserved_ids", "problem": "p", "fix": "f"}


def test_json_replaces_the_home_directory_by_its_name(tmp_path: Path) -> None:
    secret = tmp_path / ".config/cmk-werks/secret"

    document = json.loads(
        render_json(tmp_path, _status(secret=FileInfo(path=secret, exists=True, mode="0600")))
    )

    assert document["secret"]["path"] == "$HOME/.config/cmk-werks/secret"


def test_json_has_no_problems_when_healthy() -> None:
    assert json.loads(render_json(_NO_HOME, _status()))["problems"] == []


def test_json_contains_no_ansi_escapes() -> None:
    assert "\x1b" not in render_json(
        _NO_HOME, _status(problems=[Problem(item="secret", problem="p", fix="f")])
    )


def test_a_legacy_stash_on_its_own_is_the_one_in_use(tmp_path: Path) -> None:
    # Without a secret 'werk new' still reserves from the legacy file, so its IDs count as
    # available and its presence alone is no problem.
    paths = make_paths_object(tmp_path)
    paths.legacy_stash_file.write_text(
        LegacyStash(ids_by_project={"cmk": [20_260, 20_261]}).model_dump_json(by_alias=True),
        encoding="utf-8",
    )

    status = _collect(tmp_path, paths, server_status=None)

    assert [problem.item for problem in status.problems] == ["secret"]
    assert status.legacy_stash.count == 2
    assert status.legacy_stash.next_id == 20_260
    assert status.reserved_ids.count == 0


def test_a_legacy_stash_next_to_the_stash_file_is_a_problem(tmp_path: Path) -> None:
    paths = _paths(tmp_path, [20_251], secret_mode=None)
    paths.legacy_stash_file.write_text(
        LegacyStash(ids_by_project={"cmk": [20_260]}).model_dump_json(by_alias=True),
        encoding="utf-8",
    )

    status = _collect(tmp_path, paths, server_status=None)

    assert "legacy_stash" in [problem.item for problem in status.problems]


def test_legacy_ids_count_across_projects(tmp_path: Path) -> None:
    paths = make_paths_object(tmp_path)
    paths.legacy_stash_file.write_text(
        LegacyStash(ids_by_project={"cmk": [20_261], "cloudmk": [1_111_111]}).model_dump_json(
            by_alias=True
        ),
        encoding="utf-8",
    )

    status = _collect(tmp_path, paths, server_status=None)

    assert status.legacy_stash.count == 2
    assert status.legacy_stash.next_id == 20_261
