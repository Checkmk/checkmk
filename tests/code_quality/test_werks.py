#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
import re
import subprocess
from collections import defaultdict
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import NamedTuple

import git
import pytest

import cmk.ccc.version as cmk_version
import cmk.utils.werks
import cmk.werks.utils
from cmk.werks.models import WerkV2, WerkV3
from tests.testlib.common.repo import repo_path

CVSS_REGEX_V31 = re.compile(
    r"CVSS:3.1/AV:[NALP]/AC:[LH]/PR:[NLH]/UI:[NR]/S:[UC]/C:[NLH]/I:[NLH]/A:[NLH]"
)
CVSS_REGEX_V40 = re.compile(
    r"CVSS:4.0/AV:[NALP]/AC:[LH]/AT:[NP]/PR:[NLH]/UI:[NPA]/VC:[NLH]/VI:[NLH]/VA:[NLH]/SC:[NLH]/SI:[NLH]/SA:[NLH]"
)
JIRA_ISSUE_REGEX = re.compile(r"(CMK|SUP|KNW|SAASDEV)-\d+")


class WerksLoader(NamedTuple):
    base_dir: Path
    load: Callable[[], dict[int, WerkV2 | WerkV3]]


@pytest.fixture(scope="function", name="werks_loader_empty")
def fixture_werks_loader_empty(tmp_path: Path) -> WerksLoader:
    """
    provide a function to load precompiled werks from base_dir
    """
    base_dir = tmp_path / "ut_werks_base_dir"
    base_dir.mkdir()
    unacknowledged_werks_json = tmp_path / "ut_unacknowledged_werks_json"
    acknowledged_werks_mk = tmp_path / "ut_acknowledged_werks_mk"
    return WerksLoader(
        base_dir=base_dir,
        load=partial(
            cmk.utils.werks.load,
            base_dir=base_dir,
            unacknowledged_werks_json=unacknowledged_werks_json,
            acknowledged_werks_mk=acknowledged_werks_mk,
        ),
    )


@pytest.fixture(scope="function", name="werks_loaded")
def fixture_werks_loader(tmp_path: Path) -> dict[int, WerkV2 | WerkV3]:
    """
    provide all werks available in the git repository
    """
    base_dir = tmp_path / "werks_base_dir_precompiled"
    base_dir.mkdir()
    all_werks = cmk.werks.utils.load_raw_files(repo_path() / ".werks")
    cmk.werks.utils.write_precompiled_werks(base_dir / "werks", {w.id: w for w in all_werks})

    unacknowledged_werks_json = tmp_path / "ut_unacknowledged_werks_json"
    acknowledged_werks_mk = tmp_path / "ut_acknowledged_werks_mk"
    return cmk.utils.werks.load(
        base_dir=base_dir,
        unacknowledged_werks_json=unacknowledged_werks_json,
        acknowledged_werks_mk=acknowledged_werks_mk,
    )


def test_write_precompiled_werks(werks_loader_empty: WerksLoader) -> None:
    all_werks = cmk.werks.utils.load_raw_files(repo_path() / ".werks")
    # Handle both v2 editions (cre, cee, cme, cce, cse) and v3 editions (community, pro, ultimatemt, ultimate, cloud)
    cre_werks = {w.id: w for w in all_werks if w.edition.value in ("cre", "community")}
    cee_werks = {w.id: w for w in all_werks if w.edition.value in ("cee", "pro")}
    cme_werks = {w.id: w for w in all_werks if w.edition.value in ("cme", "ultimatemt")}
    cce_werks = {w.id: w for w in all_werks if w.edition.value in ("cce", "ultimate")}
    cse_werks = {w.id: w for w in all_werks if w.edition.value in ("cse", "cloud")}
    assert len(all_werks) == sum(
        [len(cre_werks), len(cee_werks), len(cme_werks), len(cce_werks), len(cse_werks)]
    )

    assert len(cre_werks) > 9847
    assert [w for w in cre_werks.keys() if 9000 <= w < 10000] == []
    cmk.werks.utils.write_precompiled_werks(werks_loader_empty.base_dir / "werks", cre_werks)

    assert len(cee_werks) > 1358
    cmk.werks.utils.write_precompiled_werks(
        werks_loader_empty.base_dir / "werks-enterprise", cee_werks
    )

    assert len(cme_werks) > 50
    cmk.werks.utils.write_precompiled_werks(
        werks_loader_empty.base_dir / "werks-managed", cme_werks
    )

    assert len(cce_werks) > 10
    cmk.werks.utils.write_precompiled_werks(werks_loader_empty.base_dir / "werks-cloud", cce_werks)

    # We currently don't have cse werks (yet)
    assert len(cse_werks) == 0
    cmk.werks.utils.write_precompiled_werks(werks_loader_empty.base_dir / "werks-saas", cse_werks)

    werks_loaded = werks_loader_empty.load()

    merged_werks = cre_werks
    merged_werks.update(cee_werks)
    merged_werks.update(cme_werks)
    merged_werks.update(cce_werks)
    merged_werks.update(cse_werks)
    assert len(all_werks) == len(merged_werks)

    assert set(merged_werks.keys()) == (werks_loaded.keys())
    for werk_id, werk in werks_loaded.items():
        raw_werk = merged_werks[werk_id]
        assert werk.title == raw_werk.title
        assert werk.description == raw_werk.description


def test_werk_versions(werks_loaded: dict[int, WerkV2 | WerkV3]) -> None:
    parsed_version = cmk_version.Version.from_str(cmk_version.__version__)

    for werk_id, werk in werks_loaded.items():
        parsed_werk_version = cmk_version.Version.from_str(werk.version)

        assert parsed_werk_version <= parsed_version, (
            "Version %s of werk #%d is not allowed in this branch" % (werk.version, werk_id)
        )


def test_secwerk_has_cvss(werks_loaded: dict[int, WerkV2 | WerkV3]) -> None:
    # The CVSS in Sec Werks is only mandatory for new Werks, so we start with 14485
    skip_lower = 14485
    for werk_id, werk in werks_loaded.items():
        if werk_id < skip_lower:
            continue
        if werk.class_.value != "security":
            continue
        assert (
            CVSS_REGEX_V31.search(werk.description) is not None
            or CVSS_REGEX_V40.search(werk.description) is not None
        ), f"Werk {werk_id} is missing a CVSS:\n{werk.description}"


def test_werk_versions_after_tagged(werks_loaded: dict[int, WerkV2 | WerkV3]) -> None:
    _assert_git_tags_available()

    list_of_offenders = []
    for werk_id, werk in werks_loaded.items():
        if werk_id < 8800:
            continue  # Do not care about older versions for the moment

        # Some werks were added after the version was released. Mostly they were forgotten by
        # the developer. Consider it a hall of shame ;)
        if werk_id in {10062, 10063, 10064, 10125, 12836}:
            continue

        tag_name = "v%s" % werk.version
        if not _git_tag_exists(tag_name):
            # print "No tag found in git: %s. Assuming version was not released yet." % tag_name
            continue

        if not _werk_exists_in_git_tag(tag_name, werk_id):
            werk_tags = sorted(
                _tags_containing_werk(werk_id),
                key=lambda t: cmk_version.Version.from_str(t[1:]),
            )
            list_of_offenders.append(
                (werk_id, werk.version, tag_name, werk_tags[0] if werk_tags else "-")
            )

    assert not list_of_offenders, (
        "The following Werks are not found in the git tag corresponding to their Version. "
        "Looks like the wrong version was declared in these werks:\n%s\n"
        "Your HEAD thinks the next version to be released is %s."
        % (
            "\n".join(
                "Werk #%d has version %s, not found in git tag %s, first found in %s" % entry
                for entry in list_of_offenders
            ),
            cmk_version.__version__,
        )
    )


def test_werks_commit_message() -> None:
    repo = git.Repo(repo_path())

    if not _are_werks_files_added_in_the_commit(repo.head.commit):
        pytest.skip("No werks files added in the latest commit")

    commit_messsage = repo.head.commit.message

    if isinstance(commit_messsage, bytes):
        commit_messsage = commit_messsage.decode(repo.head.commit.encoding or "utf-8")

    assert JIRA_ISSUE_REGEX.search(commit_messsage) is not None, (
        "The latest commit message for a Werk does not contain a valid reference to "
        "a Jira issue ID (e.g., CMK-12345, SUP-12345, KNW-12345). Commit message is:\n%s"
        % commit_messsage
    )


def _assert_git_tags_available() -> None:
    # By the time writing, we had more than 700 tags in the git repo
    assert (
        len(
            subprocess.check_output(
                ["git", "tag", "--list"],
                cwd=repo_path(),
            )
            .decode()
            .split("\n")
        )
        > 700
    ), (
        "The amount of found git tags looks suspicous low. Please check if there is an issue with your checkout"
    )


@functools.lru_cache
def _git_tag_exists(tag: str) -> bool:
    return (
        subprocess.Popen(
            ["git", "rev-list", tag],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            cwd=repo_path(),
        ).wait()
        == 0
    )


def _werk_exists_in_git_tag(tag: str, werk_id: int) -> bool:
    return f".werks/{werk_id}" in _werks_in_git_tag(
        tag
    ) or f".werks/{werk_id}.md" in _werks_in_git_tag(tag)


def _tags_containing_werk(werk_id: int) -> list[str]:
    return _werk_to_git_tag[werk_id]


_werk_to_git_tag = defaultdict(list)


@functools.lru_cache
def _werks_in_git_tag(tag: str) -> list[str]:
    werks_in_tag = (
        subprocess.check_output(
            [b"git", b"ls-tree", b"-r", b"--name-only", tag.encode(), b".werks"],
            cwd=repo_path(),
        )
        .decode()
        .split("\n")
    )

    # Populate the map of all tags a werk is in
    for werk_file in werks_in_tag:
        try:
            werk_id = int(Path(werk_file).stem)
        except ValueError:
            continue
        _werk_to_git_tag[werk_id].append(tag)

    return werks_in_tag


def _are_werks_files_added_in_the_commit(commit: git.Commit) -> bool:
    for parent in commit.parents if commit.parents else (git.NULL_TREE,):
        for change in commit.diff(parent, R=True):
            if change.new_file and change.b_path and change.b_path.startswith(".werks/"):
                return True

    return False
