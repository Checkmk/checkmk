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
    Item,
    Problem,
    render_json,
    render_status,
    SCHEMA_VERSION,
    SERVER_NOT_CHECKED,
    ServerInfo,
    SetupInfo,
    SetupState,
    Severity,
    StashInfo,
    Status,
)
from cmk.werks.tool.cli.werk import WerkId


def _no_werk_exists(_werk_id: WerkId) -> bool:
    return False


def _paths(
    tmp_path: Path,
    ids: Sequence[int] = (),
    *,
    secret_mode: int | None = 0o600,
    stash: bool = True,
    legacy_ids: Sequence[int] | None = None,
) -> Paths:
    paths = make_paths_object(tmp_path)
    if secret_mode is not None:
        paths.secret_file.parent.mkdir(parents=True, exist_ok=True)
        paths.secret_file.write_text("s3cret", encoding="utf-8")
        paths.secret_file.chmod(secret_mode)
    if stash:
        paths.stash_file.parent.mkdir(parents=True, exist_ok=True)
        paths.stash_file.write_text(
            Stash(ids=list(ids)).model_dump_json(by_alias=True), encoding="utf-8"
        )
    if legacy_ids is not None:
        paths.legacy_stash_file.write_text(
            LegacyStash(ids_by_project={"cmk": list(legacy_ids)}).model_dump_json(by_alias=True),
            encoding="utf-8",
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
        paths=paths,
        home=home,
        server_url="http://werk-ids.test",
        server_status=server_status,
        werk_exists=werk_exists,
    )


# ---------------------------------------------------------------------------
# The setup state
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("files", "expected"),
    [
        pytest.param(
            lambda tmp_path: _paths(tmp_path, [20_251]),
            SetupInfo(state=SetupState.SERVER, active_stash=Item.RESERVED_IDS),
            id="secret and stash file",
        ),
        pytest.param(
            lambda tmp_path: _paths(tmp_path, stash=False),
            SetupInfo(state=SetupState.SERVER, active_stash=Item.RESERVED_IDS),
            id="secret, nothing reserved yet",
        ),
        pytest.param(
            lambda tmp_path: _paths(tmp_path, secret_mode=None, stash=False, legacy_ids=[20_260]),
            SetupInfo(state=SetupState.LEGACY, active_stash=Item.LEGACY_STASH),
            id="legacy stash only",
        ),
        pytest.param(
            lambda tmp_path: _paths(tmp_path, stash=False, legacy_ids=[20_260]),
            SetupInfo(state=SetupState.ORPHANED_LEGACY, active_stash=Item.RESERVED_IDS),
            id="secret and legacy stash",
        ),
        pytest.param(
            lambda tmp_path: _paths(tmp_path, [20_251], secret_mode=None),
            SetupInfo(state=SetupState.ORPHANED_STASH, active_stash=None),
            id="stash file without a secret",
        ),
        pytest.param(
            lambda tmp_path: _paths(tmp_path, [20_251], legacy_ids=[20_260]),
            SetupInfo(state=SetupState.CONFLICT, active_stash=None),
            id="both stash files",
        ),
        pytest.param(
            lambda tmp_path: _paths(tmp_path, secret_mode=None, stash=False),
            SetupInfo(state=SetupState.UNINITIALIZED, active_stash=None),
            id="nothing at all",
        ),
    ],
)
def test_the_setup_state_follows_the_files_that_exist(
    tmp_path: Path, files: Callable[[Path], Paths], expected: SetupInfo
) -> None:
    status = _collect(tmp_path, files(tmp_path))

    assert status.setup == expected


def test_the_ids_of_the_stash_in_use_are_the_available_ones(tmp_path: Path) -> None:
    status = _collect(
        tmp_path,
        _paths(tmp_path, [20_251], secret_mode=None, stash=False, legacy_ids=[20_260]),
    )

    assert status.setup.active_stash is Item.LEGACY_STASH
    assert status.legacy_stash.next_id == 20_260
    assert status.reserved_ids.count == 0


# ---------------------------------------------------------------------------
# One problem per state
# ---------------------------------------------------------------------------


def test_a_healthy_setup_has_no_problems(tmp_path: Path) -> None:
    status = _collect(tmp_path, _paths(tmp_path, [20_251, 20_252]))

    assert status.problems == []
    assert status.has_errors is False
    assert status.reserved_ids.count == 2
    assert status.reserved_ids.next_id == 20_251
    assert status.reserved_ids.exists is True


def test_the_legacy_stash_on_its_own_is_only_a_warning(tmp_path: Path) -> None:
    # 'werk new' still reserves from the legacy file, so nothing is broken here.
    paths = _paths(tmp_path, secret_mode=None, stash=False, legacy_ids=[20_260, 20_261])

    status = _collect(tmp_path, paths, server_status=None)

    assert status.problems == [
        Problem(
            item=Item.LEGACY_STASH,
            severity=Severity.WARNING,
            problem="still the stash in use, the werk ID server is not set up yet",
            fix="werk init",
        )
    ]
    assert status.has_errors is False
    assert status.legacy_stash.count == 2


def test_a_legacy_stash_left_over_next_to_the_secret_is_a_warning(tmp_path: Path) -> None:
    paths = _paths(tmp_path, stash=False, legacy_ids=[20_260])

    status = _collect(tmp_path, paths)

    assert status.problems == [
        Problem(
            item=Item.LEGACY_STASH,
            severity=Severity.WARNING,
            problem="left over next to the secret, its IDs are not used any more",
            fix="merge the IDs you still need into the stash by hand, then delete it",
        )
    ]
    assert status.has_errors is False


def test_both_stash_files_are_an_error(tmp_path: Path) -> None:
    paths = _paths(tmp_path, [20_251], legacy_ids=[20_260])

    status = _collect(tmp_path, paths)

    assert status.problems == [
        Problem(
            item=Item.LEGACY_STASH,
            severity=Severity.ERROR,
            problem="exists next to the current stash file, every other command bails out",
            fix="look at both stash files and merge them by hand",
        )
    ]
    assert status.has_errors is True
    assert status.legacy_stash.exists is True
    assert status.legacy_stash.path == paths.legacy_stash_file
    assert status.legacy_stash.count == 1
    assert status.legacy_stash.next_id == 20_260


def test_a_stash_file_without_a_secret_is_an_error(tmp_path: Path) -> None:
    status = _collect(tmp_path, _paths(tmp_path, [20_251], secret_mode=None), server_status=None)

    assert status.problems == [
        Problem(
            item=Item.SECRET,
            severity=Severity.ERROR,
            problem="missing, so the reserved IDs are not used",
            fix="werk init",
        )
    ]
    assert status.secret.exists is False
    assert status.secret.mode is None
    assert status.server.status == SERVER_NOT_CHECKED


def test_a_setup_without_any_file_is_an_error(tmp_path: Path) -> None:
    status = _collect(tmp_path, _paths(tmp_path, secret_mode=None, stash=False), server_status=None)

    assert status.problems == [
        Problem(
            item=Item.SECRET,
            severity=Severity.ERROR,
            problem="missing, no werk IDs are set up",
            fix="werk init",
        )
    ]


def test_a_state_without_a_stash_in_use_reports_nothing_about_reserved_ids(
    tmp_path: Path,
) -> None:
    # The state says why no IDs are available; a second problem about them would only
    # repeat it.
    status = _collect(
        tmp_path,
        _paths(tmp_path, [20_251], legacy_ids=[20_260]),
        server_status=ServerStatus.UNREACHABLE,
    )

    assert [problem.item for problem in status.problems] == [Item.LEGACY_STASH]


# ---------------------------------------------------------------------------
# Server and reserved IDs
# ---------------------------------------------------------------------------


def test_reserved_ids_without_any_id(tmp_path: Path) -> None:
    status = _collect(tmp_path, _paths(tmp_path))

    assert status.problems == []
    assert status.reserved_ids.count == 0
    assert status.reserved_ids.next_id is None


def test_no_reserved_ids_and_unreachable_server_is_a_problem(tmp_path: Path) -> None:
    status = _collect(tmp_path, _paths(tmp_path), server_status=ServerStatus.UNREACHABLE)

    assert status.problems == [
        Problem(
            item=Item.RESERVED_IDS,
            severity=Severity.ERROR,
            problem="none reserved and the server is unavailable",
            fix="reconnect to the VPN, then 'werk new'",
        )
    ]


def test_the_stash_in_use_is_the_one_the_reserved_id_problems_belong_to(tmp_path: Path) -> None:
    paths = _paths(tmp_path, secret_mode=None, stash=False, legacy_ids=[])

    status = _collect(tmp_path, paths, server_status=None)

    assert Problem(
        item=Item.LEGACY_STASH,
        severity=Severity.ERROR,
        problem="none reserved and the server is unavailable",
        fix="reconnect to the VPN, then 'werk new'",
    ) in list(status.problems)


def test_unreachable_server_with_reserved_ids_reports_no_problem(tmp_path: Path) -> None:
    status = _collect(tmp_path, _paths(tmp_path, [20_251]), server_status=ServerStatus.UNREACHABLE)

    assert status.problems == []
    assert status.server.status == "unreachable"


def test_rejected_secret_is_a_problem(tmp_path: Path) -> None:
    status = _collect(tmp_path, _paths(tmp_path, [20_251]), server_status=ServerStatus.UNAUTHORIZED)

    assert status.problems == [
        Problem(
            item=Item.SERVER,
            severity=Severity.ERROR,
            problem="rejected your secret",
            fix="werk init",
        )
    ]


def test_server_error_is_a_problem(tmp_path: Path) -> None:
    status = _collect(tmp_path, _paths(tmp_path, [20_251]), server_status=ServerStatus.ERROR)

    assert status.problems == [
        Problem(
            item=Item.SERVER,
            severity=Severity.ERROR,
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
            item=Item.RESERVED_IDS,
            severity=Severity.ERROR,
            problem="werk 20252 already exists on disk",
            fix="remove 20252 from the stash",
        )
    ]


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
            item=Item.SECRET,
            severity=Severity.ERROR,
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
    assert status.problems[0].item is Item.SECRET
    assert status.problems[0].problem.startswith("readable by others")


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _status(
    *,
    setup: SetupInfo | None = None,
    server_status: str = "ok",
    secret: FileInfo | None = None,
    reserved_ids: StashInfo | None = None,
    legacy_stash: StashInfo | None = None,
    problems: Sequence[Problem] = (),
) -> Status:
    return Status(
        setup=setup or SetupInfo(state=SetupState.SERVER, active_stash=Item.RESERVED_IDS),
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


def test_render_explains_the_setup_state() -> None:
    output = _rendered(
        _NO_HOME, _status(setup=SetupInfo(state=SetupState.LEGACY, active_stash=Item.LEGACY_STASH))
    )

    assert "setup" in output
    assert "not migrated yet" in output


def test_render_says_which_stash_is_in_use() -> None:
    output = _rendered(
        _NO_HOME,
        _status(
            setup=SetupInfo(state=SetupState.LEGACY, active_stash=Item.LEGACY_STASH),
            legacy_stash=StashInfo(
                path=Path("/h/.cmk-werk-ids"), exists=True, mode="0600", count=2, next_id=11_120
            ),
        ),
    )

    assert "2 reserved, next 11120 (in use)" in output
    assert "3 reserved, next 20251 (not in use)" in output


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
                Problem(
                    item=Item.SECRET,
                    severity=Severity.ERROR,
                    problem="readable by others (0644)",
                    fix="chmod 600 x",
                ),
                Problem(
                    item=Item.SERVER,
                    severity=Severity.ERROR,
                    problem="rejected your secret",
                    fix="werk init",
                ),
            ]
        ),
    )

    assert "PROBLEM" in output
    assert "FIX" in output
    assert "readable by others (0644)" in output
    assert "chmod 600 x" in output
    assert "rejected your secret" in output
    assert "none found" not in output


def test_render_marks_the_setup_row_after_the_state_alone() -> None:
    # A problem elsewhere must not make the setup look broken.
    output = _rendered(
        _NO_HOME,
        _status(
            problems=[
                Problem(
                    item=Item.RESERVED_IDS,
                    severity=Severity.ERROR,
                    problem="none reserved and the server is unavailable",
                    fix="reconnect to the VPN, then 'werk new'",
                )
            ]
        ),
    )

    assert "✓   setup" in output
    assert "✗   reserved ids" in output


def test_render_marks_a_file_that_is_not_there_neither_good_nor_bad() -> None:
    output = _rendered(
        _NO_HOME,
        _status(
            reserved_ids=StashInfo(
                path=Path("/h/reserved"), exists=False, mode=None, count=0, next_id=None
            )
        ),
    )

    assert "-   reserved ids" in output
    assert "✓   secret" in output


def test_render_marks_a_warning_apart_from_an_error() -> None:
    warning = Problem(
        item=Item.LEGACY_STASH, severity=Severity.WARNING, problem="left over", fix="delete it"
    )
    error = Problem(item=Item.SECRET, severity=Severity.ERROR, problem="missing", fix="werk init")

    assert "!" in _rendered(_NO_HOME, _status(problems=[warning]))
    assert "✗" in _rendered(_NO_HOME, _status(problems=[error]))
    assert "✗" not in _rendered(_NO_HOME, _status(problems=[warning]))


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


def test_json_states_are_machine_readable_tokens() -> None:
    document = json.loads(
        render_json(
            _NO_HOME, _status(setup=SetupInfo(state=SetupState.CONFLICT, active_stash=None))
        )
    )

    assert document["setup"] == {"state": "conflict", "active_stash": None}


def test_json_keeps_a_fixed_shape() -> None:
    # the tables hide the legacy stash while it does not exist; the document must not
    document = json.loads(render_json(_NO_HOME, _status()))

    assert set(document) == {
        "schema_version",
        "setup",
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
                    Problem(item=Item.RESERVED_IDS, severity=Severity.ERROR, problem="p", fix="f"),
                    Problem(
                        item=Item.LEGACY_STASH, severity=Severity.WARNING, problem="p", fix="f"
                    ),
                ]
            ),
        )
    )

    for problem in document["problems"]:
        assert problem["item"] in document, f"{problem['item']} is not a section key"
    assert document["problems"][0] == {
        "item": "reserved_ids",
        "severity": "error",
        "problem": "p",
        "fix": "f",
    }
    assert document["problems"][1]["severity"] == "warning"


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
        _NO_HOME,
        _status(
            problems=[Problem(item=Item.SECRET, severity=Severity.ERROR, problem="p", fix="f")]
        ),
    )


# ---------------------------------------------------------------------------
# Error vs. warning
# ---------------------------------------------------------------------------


def test_only_errors_count_as_errors() -> None:
    warning = Problem(
        item=Item.LEGACY_STASH, severity=Severity.WARNING, problem="left over", fix="delete it"
    )
    error = Problem(item=Item.SECRET, severity=Severity.ERROR, problem="missing", fix="werk init")

    assert _status(problems=[warning]).has_errors is False
    assert _status(problems=[warning, error]).has_errors is True


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
