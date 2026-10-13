#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from pathlib import Path

import pytest
from git.repo import Repo

from cmk.werks.tool.utils.__main__ import main as utils_main
from cmk.werks.tool.utils.collect import main

from ._werk_files import werk_text

_APPLIANCE_WERK = """Title: Check_MK version upload now checks required firmware version correctly
Level: 1
Component: firmware
Version: 1.1.3
Date: 1414753336
Class: fix
"""


def _init_repo(path: Path) -> Repo:
    repo = Repo.init(path)
    writer = repo.config_writer()
    writer.set_value("user", "email", "git@example.com")
    writer.set_value("user", "name", "git")
    writer.release()
    return repo


def _commit(repo: Repo, files: Mapping[str, str]) -> str:
    root = Path(repo.working_dir)
    for name, content in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(content, encoding="utf-8")
    repo.index.add(list(files))
    return repo.index.commit("commit").hexsha


def _collect(
    capsys: pytest.CaptureFixture[str], flavor: str, repo: Repo, branches: Mapping[str, str]
) -> dict[str, dict[str, object]]:
    match flavor:
        case "cmk" | "cma" | "checkmk_kube_agent" | "cloudmk":
            main(flavor, Path(repo.working_dir), branches)
        case _:
            raise RuntimeError(f"unknown flavor {flavor}")
    collected: dict[str, dict[str, object]] = json.loads(capsys.readouterr().out)
    return collected


@pytest.fixture(name="two_releases")
def fixture_two_releases(tmp_path: Path) -> tuple[Repo, Mapping[str, str]]:
    repo = _init_repo(tmp_path / "repo")
    stable = _commit(
        repo,
        {
            "defines.make": "VERSION := 2.4.0p1\n",
            ".werks/1234.md": werk_text(title="Old title", version="2.4.0b1"),
        },
    )
    master = _commit(
        repo,
        {
            "defines.make": "VERSION := 2.5.0b1\n",
            ".werks/1234.md": werk_text(title="New title", version="2.5.0b1"),
        },
    )
    return repo, {"master": master, "2.4.0": stable}


def test_the_werk_of_the_newest_branch_wins(
    capsys: pytest.CaptureFixture[str], two_releases: tuple[Repo, Mapping[str, str]]
) -> None:
    repo, branches = two_releases

    collected = _collect(capsys, "cmk", repo, branches)

    assert collected["1234"]["title"] == "New title"


def test_every_branch_lists_its_version_of_the_werk(
    capsys: pytest.CaptureFixture[str], two_releases: tuple[Repo, Mapping[str, str]]
) -> None:
    repo, branches = two_releases

    collected = _collect(capsys, "cmk", repo, branches)

    assert collected["1234"]["versions"] == {"2.4.0": "2.4.0b1", "master": "2.5.0b1"}


def test_a_branch_without_a_release_version_is_skipped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _init_repo(tmp_path / "repo")
    unreleased = _commit(repo, {".werks/1234.md": werk_text(version="2.4.0")})
    master = _commit(repo, {"defines.make": "VERSION := 2.5.0\n", ".werks/1234.md": werk_text()})

    collected = _collect(capsys, "cmk", repo, {"2.4.0": unreleased, "master": master})

    assert collected["1234"]["versions"] == {"master": "2.5.0"}


def test_substituted_branches_name_the_revisions_to_collect(
    capsys: pytest.CaptureFixture[str], two_releases: tuple[Repo, Mapping[str, str]]
) -> None:
    repo, branches = two_releases

    utils_main(
        [
            "collect",
            "cmk",
            str(repo.working_dir),
            "--substitute-branches",
            *(f"{name}:{revision}" for name, revision in branches.items()),
        ]
    )

    assert json.loads(capsys.readouterr().out)["1234"]["versions"] == {
        "2.4.0": "2.4.0b1",
        "master": "2.5.0b1",
    }


def test_an_innovation_branch_counts_for_its_release(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _init_repo(tmp_path / "repo")
    commit = _commit(
        repo,
        {"defines.make": "VERSION := 2.4.0i1\n", ".werks/1234.md": werk_text(version="2.4.0i1")},
    )

    collected = _collect(capsys, "cmk", repo, {"2.4.0i1": commit})

    assert collected["1234"]["versions"] == {"2.4.0": "2.4.0i1"}


def test_only_the_release_branches_of_origin_are_collected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    origin = _init_repo(tmp_path / "origin")
    stable = _commit(
        origin,
        {"defines.make": "VERSION := 2.4.0\n", ".werks/1234.md": werk_text(version="2.4.0")},
    )
    _commit(origin, {"defines.make": "VERSION := 2.5.0\n", ".werks/1234.md": werk_text()})
    origin.create_head("2.4.0", stable)
    origin.create_head("sandbox/feature", stable)
    origin.git.branch("-M", "master")
    clone = Repo.clone_from(origin.working_dir, tmp_path / "clone")

    collected = _collect(capsys, "cmk", clone, {})

    assert collected["1234"]["versions"] == {"2.4.0": "2.4.0", "master": "2.5.0"}


def test_an_appliance_branch_with_cma_defines_is_collected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _init_repo(tmp_path / "repo")
    commit = _commit(repo, {"cma-defines": "VERSION=1.1.3\n", ".werks/9088": _APPLIANCE_WERK})

    collected = _collect(capsys, "cma", repo, {"1.1": commit})

    assert collected["9088"]["versions"] == {"1.1": "1.1.3"}


def test_a_kube_agent_branch_with_a_versioned_werk_config_is_collected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _init_repo(tmp_path / "repo")
    commit = _commit(
        repo,
        {
            ".werks/config": 'current_version = "1.2.0"\n',
            ".werks/1234.md": werk_text(version="1.2.0"),
        },
    )

    collected = _collect(capsys, "checkmk_kube_agent", repo, {"main": commit})

    assert collected["1234"]["versions"] == {"main": "1.2.0"}


def test_an_unexpected_file_among_the_werks_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _init_repo(tmp_path / "repo")
    commit = _commit(repo, {"defines.make": "VERSION := 2.5.0\n", ".werks/notes.txt": "notes"})

    with pytest.raises(RuntimeError, match="Found unexpected file 'notes.txt'"):
        _collect(capsys, "cmk", repo, {"master": commit})


def test_collecting_no_werk_at_all_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _init_repo(tmp_path / "repo")
    commit = _commit(repo, {"defines.make": "VERSION := 2.5.0\n", ".werks/first_free": "1\n"})

    with pytest.raises(RuntimeError, match="Expected to collect at least one Werk"):
        _collect(capsys, "cmk", repo, {"master": commit})


def test_a_branch_whose_defines_make_names_no_version_is_skipped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _init_repo(tmp_path / "repo")
    unversioned = _commit(
        repo,
        {"defines.make": "EDITION := community\n", ".werks/1234.md": werk_text(version="2.4.0")},
    )
    master = _commit(repo, {"defines.make": "VERSION := 2.5.0\n", ".werks/1234.md": werk_text()})

    collected = _collect(capsys, "cmk", repo, {"2.4.0": unversioned, "master": master})

    assert collected["1234"]["versions"] == {"master": "2.5.0"}


def test_a_branch_without_werks_is_skipped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _init_repo(tmp_path / "repo")
    without_werks = _commit(repo, {"defines.make": "VERSION := 2.4.0\n"})
    master = _commit(repo, {"defines.make": "VERSION := 2.5.0\n", ".werks/1234.md": werk_text()})

    collected = _collect(capsys, "cmk", repo, {"2.4.0": without_werks, "master": master})

    assert collected["1234"]["versions"] == {"master": "2.5.0"}


def test_the_werks_of_old_1_2_branches_count_for_1_2_0(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _init_repo(tmp_path / "repo")
    commit = _commit(
        repo, {"defines.make": "VERSION := 1.2.8\n", ".werks/1234.md": werk_text(version="1.2.8")}
    )

    collected = _collect(capsys, "cmk", repo, {"1.2.8": commit})

    assert collected["1234"]["versions"] == {"1.2.0": "1.2.8"}


def test_a_werk_that_cannot_be_parsed_names_its_branch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _init_repo(tmp_path / "repo")
    commit = _commit(repo, {"defines.make": "VERSION := 2.5.0\n", ".werks/1234.md": "no werk"})

    with pytest.raises(RuntimeError, match="could not parse werk 1234.md from branch master"):
        _collect(capsys, "cmk", repo, {"master": commit})


def test_a_werk_that_cannot_be_loaded_names_its_flavor(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _init_repo(tmp_path / "repo")
    commit = _commit(
        repo,
        {"defines.make": "VERSION := 2.5.0\n", ".werks/1234.md": werk_text(werk_class="bug")},
    )

    with pytest.raises(RuntimeError, match="could not load werk 1234 from flavor cmk"):
        _collect(capsys, "cmk", repo, {"master": commit})


@pytest.mark.parametrize(
    "config",
    [
        pytest.param({}, id="without-config"),
        pytest.param({".werks/config": "editions = []\n"}, id="without-current-version"),
    ],
)
def test_a_kube_agent_branch_without_a_current_version_is_skipped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], config: Mapping[str, str]
) -> None:
    repo = _init_repo(tmp_path / "repo")
    skipped = _commit(repo, {**config, ".werks/1234.md": werk_text(version="1.1.0")})
    main_branch = _commit(
        repo,
        {
            ".werks/config": 'current_version = "1.2.0"\n',
            ".werks/1234.md": werk_text(version="1.2.0"),
        },
    )

    collected = _collect(
        capsys, "checkmk_kube_agent", repo, {"1.1.0": skipped, "main": main_branch}
    )

    assert collected["1234"]["versions"] == {"main": "1.2.0"}


def test_cloud_werks_are_collected_as_cloudmk_werks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _init_repo(tmp_path / "repo")
    commit = _commit(repo, {"defines.make": "VERSION := 1.0.0\n", ".werks/1234.md": werk_text()})

    collected = _collect(capsys, "cloudmk", repo, {"main": commit})

    assert collected["1234"]["product"] == "cloudmk"
