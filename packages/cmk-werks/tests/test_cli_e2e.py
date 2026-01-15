#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from git.repo import Repo


def initialize_werks_project(
    path: Path,
    *,
    project: str,
    first_free: int,
    commit: bool = True,
    repo_url: str = "some-url/check_mk",
    branch_name: str = "testmain",
) -> Repo:
    path.mkdir()
    werks = path / ".werks"
    werks.mkdir()
    (werks / "first_free").write_text(f"{first_free}\n")
    commit_option = ""
    if commit is False:
        commit_option = "create_commit = False"
    (werks / "config").write_text(f"""
editions = [("cre", "CRE")]
components = [("ccc", "CCC")]
edition_components = {"{}"}
classes = [
    ("feature", "New feature", ""),
    ("fix", "Bug fix", "FIX"),
    ("security", "Security fix", "SEC"),
]
levels = [
    ("1", "Trivial change"),
    ("2", "Prominent change"),
    ("3", "Major change"),
]
compatible = [
    ("compat", "Compatible"),
    ("incomp", "Incompatible"),
]
online_url = "https://checkmk.com/werk/%d"
project = "{project}"
current_version = "0.1.0"
branch = "{branch_name}"
repo = "{repo_url}"
{commit_option}
    """)
    Repo.init(path)
    repo = Repo(path)
    (path / "README.md").write_text(f"# repo {project}")
    cw = repo.config_writer()
    cw.set_value("user", "email", "git@example.com")
    cw.set_value("user", "name", "git")
    cw.release()
    repo.index.add(["README.md", ".werks/first_free"])
    repo.index.commit("initial commit")
    repo.create_remote("origin", f"git@{repo_url}")
    branch = repo.create_head(branch_name)
    repo.head.reference = branch
    return repo


def run_cli_with_vcr(
    args: list[str], cassette_path: str, vcr_config: dict[str, Any], input_data: bytes = b""
) -> tuple[int, bytes, bytes]:
    """Run CLI with VCR recording support via sitecustomize injection."""
    env = os.environ.copy()

    # Setup PYTHONPATH with our VCR injector and package paths
    test_dir = Path(__file__).parent
    injector = test_dir / "vcr_injector"

    # Add the necessary paths for cmk.werks module to be found
    # Go up from tests dir to get to the package root
    package_root = test_dir.parent  # cmk-werks package
    repo_root = package_root.parent.parent  # check_mk repo root
    packages_dir = repo_root / "packages"

    pythonpath_parts = [
        str(injector),
        str(package_root),
        str(repo_root),
        str(packages_dir),
    ]

    # Add existing PYTHONPATH if present
    existing_pythonpath = env.get("PYTHONPATH", "")
    if existing_pythonpath:
        pythonpath_parts.append(existing_pythonpath)

    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

    # Setup VCR configuration via environment variables
    env["VCR_CASSETTE"] = str(cassette_path)
    env["VCR_CONFIG"] = json.dumps(vcr_config)

    # Debug info
    print("Running CLI with VCR:")  # nosemgrep: disallow-print
    # nosemgrep: disallow-print
    print(f"  Command: {[sys.executable, '-m', 'cmk.werks.cli'] + args}")
    print(f"  Cassette: {cassette_path}")  # nosemgrep: disallow-print
    print(f"  VCR Config: {vcr_config}")  # nosemgrep: disallow-print
    print(f"  PYTHONPATH: {env['PYTHONPATH']}")  # nosemgrep: disallow-print

    p = subprocess.Popen(
        [sys.executable, "-m", "cmk.werks.cli"] + args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    out, err = p.communicate(input=input_data, timeout=60)

    print(f"CLI completed with return code: {p.returncode}")  # nosemgrep: disallow-print
    if out:
        print(f"stdout: {out.decode()}")  # nosemgrep: disallow-print
    if err:
        print(f"stderr: {err.decode()}")  # nosemgrep: disallow-print

    return p.returncode, out, err


def call(*args: str) -> None:
    # we can not call main directly, because the script was not created with that in mind
    # for example we have very sticky caches
    subprocess.check_call(["python", "-m", "cmk.werks.cli", *args])


def create_werk(*, title: str, vcr_cassette_dir: str, vcr_config: dict[str, Any]) -> None:
    change = Path(f"some_change{title}")
    change.write_text("smth")
    repo = Repo(".")
    repo.index.add([str(change)])

    # Use VCR recording for the subprocess with pytest fixture paths
    cassette_name = f"create_werk_{title.replace(' ', '_')}.yaml"
    # Make cassette path absolute to avoid issues with changing working directories
    if not Path(vcr_cassette_dir).is_absolute():
        test_base_dir = Path(__file__).parent
        cassette_path = test_base_dir / vcr_cassette_dir / cassette_name
    else:
        cassette_path = Path(vcr_cassette_dir) / cassette_name
    input_data = title.encode() + b"\nf\nc\nc\n1\nc\nk\n"

    returncode, stdout, stderr = run_cli_with_vcr(
        ["new"], str(cassette_path), vcr_config, input_data=input_data
    )

    if returncode != 0:
        print(f"CLI failed with return code {returncode}")  # nosemgrep: disallow-print
        print(f"stdout: {stdout.decode()}")  # nosemgrep: disallow-print
        print(f"stderr: {stderr.decode()}")  # nosemgrep: disallow-print
        raise RuntimeError(f"CLI command failed with return code {returncode}")


def latest_commit_subject(repo_path: Path) -> str:
    repo = Repo(repo_path)
    message = repo.head.commit.message
    if message is None:  # type: ignore[comparison-overlap]
        raise RuntimeError("message is none")
    if isinstance(message, bytes):
        message = message.decode("utf-8")
    return message.split("\n")[0]


@pytest.mark.vcr
def test_reserve_ids_and_create_werk(
    tmp_path: Path, vcr_cassette_dir: str, vcr_config: dict[str, Any]
) -> None:
    home = tmp_path / "home"
    home.mkdir()

    def read_reserved_werks() -> Any:
        return json.loads((home / ".cmk-werk-ids").read_text().strip())["ids_by_project"]

    cmk_repo_path = tmp_path / "repo_cmk"
    cloudmk_repo_path = tmp_path / "repo_cloudmk"

    initialize_werks_project(cmk_repo_path, project="cmk", first_free=11_111)
    initialize_werks_project(
        cloudmk_repo_path,
        project="cloudmk",
        first_free=1_111_111,
        repo_url="some-url/cloudmk",
        branch_name="foobar",
    )

    with mock.patch.dict(os.environ, {"HOME": str(home), "EDITOR": "true"}):
        os.chdir(cmk_repo_path)
        call("ids", "5")
        assert latest_commit_subject(cmk_repo_path) == "Reserved 5 Werk IDS"
        assert (cmk_repo_path / ".werks/first_free").read_text().strip() == "11116"
        assert read_reserved_werks() == {
            "cmk": [11111, 11112, 11113, 11114, 11115],
        }

        os.chdir(cloudmk_repo_path)
        call("ids", "2")
        assert latest_commit_subject(cloudmk_repo_path) == "Reserved 2 Werk IDS"
        assert (cloudmk_repo_path / ".werks/first_free").read_text().strip() == "1111113"
        assert read_reserved_werks() == {
            "cmk": [11111, 11112, 11113, 11114, 11115],
            "cloudmk": [1111111, 1111112],
        }

        os.chdir(cmk_repo_path)
        create_werk(title="some_title", vcr_cassette_dir=vcr_cassette_dir, vcr_config=vcr_config)
        assert latest_commit_subject(cmk_repo_path) == "11111 some_title"
        assert "some_title" in (cmk_repo_path / ".werks/11111.md").read_text()
        assert read_reserved_werks() == {
            "cmk": [11112, 11113, 11114, 11115],
            "cloudmk": [1111111, 1111112],
        }

        os.chdir(cloudmk_repo_path)
        create_werk(
            title="some_cloud_title", vcr_cassette_dir=vcr_cassette_dir, vcr_config=vcr_config
        )
        assert latest_commit_subject(cloudmk_repo_path) == "1111111 some_cloud_title"
        assert "some_cloud_title" in (cloudmk_repo_path / ".werks/1111111.md").read_text()
        assert read_reserved_werks() == {
            "cmk": [11112, 11113, 11114, 11115],
            "cloudmk": [1111112],
        }


@pytest.mark.vcr
def test_commit_config(tmp_path: Path, vcr_cassette_dir: str, vcr_config: dict[str, Any]) -> None:
    home = tmp_path / "home"
    home.mkdir()
    cloudmk_repo_path = tmp_path / "repo_cloudmk"
    initialize_werks_project(
        cloudmk_repo_path, project="cloudmk", first_free=1_111_111, commit=False
    )
    assert latest_commit_subject(cloudmk_repo_path) == "initial commit"

    with mock.patch.dict(os.environ, {"HOME": str(home), "EDITOR": "true"}):
        os.chdir(cloudmk_repo_path)
        call("ids", "2")
        assert latest_commit_subject(cloudmk_repo_path) == "initial commit"
        # just lets make sure that the ids were actually reserved:
        json.loads((home / ".cmk-werk-ids").read_text())["ids_by_project"] == {
            "cloudmk": [1111111, 1111112]
        }

        create_werk(
            title="some_cloud_title", vcr_cassette_dir=vcr_cassette_dir, vcr_config=vcr_config
        )
        assert latest_commit_subject(cloudmk_repo_path) == "initial commit"
        # just lets make sure that the werk was actually created:
        assert "some_cloud_title" in (cloudmk_repo_path / ".werks/1111111.md").read_text()
