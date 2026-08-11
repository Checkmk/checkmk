#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
import subprocess
from collections import defaultdict
from collections.abc import Callable, Iterator, Sequence
from functools import lru_cache, partial
from pathlib import Path
from typing import NamedTuple

import git
import pytest

import cmk.ccc.version as cmk_version
import cmk.werks.site
import cmk.werks.tool.utils
from cmk.werks.tool.models import WerkV3
from tests.code_quality.bazel_utils import bazel_repo_root


@lru_cache
def git_dir() -> Path:
    # Note on the `Path.resolve()` call.
    #
    # The `BUILD` file tags these tests as `"no-sandbox"` to
    # simplify access to `.git`, however, if "no-sandbox"
    # removes filesystem isolation, it doesn't prevent Bazel
    # from calling the code from the runfiles.  We therefore need
    # to jump out of the runfiles and into the actual repo with
    # the `Path.resolved()` call as well.
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent / ".git"
    raise RuntimeError("Could not find .git directory")


@pytest.fixture(scope="module")
def prepare_git_env() -> Iterator[None]:
    # https://git-scm.com/docs/git-config#Documentation/git-config.txt-GITCONFIGCOUNT
    git_env = {
        "GIT_DIR": str(git_dir()),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "safe.directory",
        "GIT_CONFIG_VALUE_0": "*",
    }
    saved = {key: os.environ.pop(key, None) for key in git_env}
    os.environ.update(git_env)
    try:
        yield
    finally:
        for key, old_value in saved.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


CVSS_REGEX_V31 = re.compile(
    r"CVSS:3.1/AV:[NALP]/AC:[LH]/PR:[NLH]/UI:[NR]/S:[UC]/(?P<impact>C:[NLH]/I:[NLH]/A:[NLH])"
)
CVSS_REGEX_V40 = re.compile(
    r"CVSS:4.0/AV:[NALP]/AC:[LH]/AT:[NP]/PR:[NLH]/UI:[NPA]/"
    r"(?P<impact>VC:[NLH]/VI:[NLH]/VA:[NLH]/SC:[NLH]/SI:[NLH]/SA:[NLH])"
)
CVE_REGEX = re.compile(r"CVE-\d{4}-\d{4,}")
JIRA_ISSUE_REGEX = re.compile(r"(CMK|SUP|KNW|SAASDEV|BETA)-\d+")

# If your new Sec Werk trips one of the asserts below, please get in touch with the security
# team. These days we tend to use Sec Werks only for real vulnerabilities (which require a CVSS
# score and a CVE) and feature Werks for security improvements.
SECURITY_CONTACT_HINT = (
    "If you are unsure whether this should be a Sec Werk, or how to obtain a CVSS score or a CVE, "
    "please get in touch with the security team."
)

# Sec Werks that predate the requirement to always reference a CVE. Do not add new entries here:
# every new Sec Werk must reference a CVE.
SECWERKS_WITHOUT_CVE = {
    14871,
    14919,
    16990,
}

# The CVSS and CVE requirements are only mandatory for new Werks, so we start with 14485
OLDEST_WERK_REQUIRING_CVSS = 14485


class WerksLoader(NamedTuple):
    base_dir: Path
    load: Callable[[], dict[int, WerkV3]]


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
            cmk.werks.site.load,
            base_dir=base_dir,
            unacknowledged_werks_json=unacknowledged_werks_json,
            acknowledged_werks_mk=acknowledged_werks_mk,
        ),
    )


@pytest.fixture(scope="session", name="all_werks_raw")
def fixture_all_werks_raw() -> Sequence[WerkV3]:
    """
    provide the werks as parsed from the `.werks` directory
    """
    return cmk.werks.tool.utils.load_raw_files(bazel_repo_root() / ".werks")


@pytest.fixture(scope="session", name="werks_loaded")
def fixture_werks_loader(
    tmp_path_factory: pytest.TempPathFactory, all_werks_raw: Sequence[WerkV3]
) -> dict[int, WerkV3]:
    """
    provide all werks available in the git repository
    """
    tmp_path = tmp_path_factory.mktemp("werks")
    base_dir = tmp_path / "werks_base_dir_precompiled"
    base_dir.mkdir()
    cmk.werks.tool.utils.write_precompiled_werks(
        base_dir / "werks", {w.id: w for w in all_werks_raw}
    )

    unacknowledged_werks_json = tmp_path / "ut_unacknowledged_werks_json"
    acknowledged_werks_mk = tmp_path / "ut_acknowledged_werks_mk"
    return cmk.werks.site.load(
        base_dir=base_dir,
        unacknowledged_werks_json=unacknowledged_werks_json,
        acknowledged_werks_mk=acknowledged_werks_mk,
    )


@pytest.fixture(scope="session", name="secwerks_loaded")
def fixture_secwerks_loaded(werks_loaded: dict[int, WerkV3]) -> dict[int, WerkV3]:
    """
    provide the Sec Werks the CVSS and CVE requirements apply to
    """
    return {
        werk_id: werk
        for werk_id, werk in werks_loaded.items()
        if werk_id >= OLDEST_WERK_REQUIRING_CVSS and werk.class_.value == "security"
    }


def test_write_precompiled_werks(
    werks_loader_empty: WerksLoader, all_werks_raw: Sequence[WerkV3]
) -> None:
    # Handle both v2 editions (cre, cee, cme, cce, cse) and v3 editions (community, pro, ultimatemt, ultimate, cloud)
    cre_werks = {w.id: w for w in all_werks_raw if w.edition.value in ("cre", "community")}
    cee_werks = {w.id: w for w in all_werks_raw if w.edition.value in ("cee", "pro")}
    cme_werks = {w.id: w for w in all_werks_raw if w.edition.value in ("cme", "ultimatemt")}
    cce_werks = {w.id: w for w in all_werks_raw if w.edition.value in ("cce", "ultimate")}
    cse_werks = {w.id: w for w in all_werks_raw if w.edition.value in ("cse", "cloud")}
    assert len(all_werks_raw) == sum(
        [len(cre_werks), len(cee_werks), len(cme_werks), len(cce_werks), len(cse_werks)]
    )

    assert len(cre_werks) > 9847
    assert [w for w in cre_werks if 9000 <= w < 10000] == []
    cmk.werks.tool.utils.write_precompiled_werks(werks_loader_empty.base_dir / "werks", cre_werks)

    assert len(cee_werks) > 1358
    cmk.werks.tool.utils.write_precompiled_werks(
        werks_loader_empty.base_dir / "werks-enterprise", cee_werks
    )

    assert len(cme_werks) > 50
    cmk.werks.tool.utils.write_precompiled_werks(
        werks_loader_empty.base_dir / "werks-managed", cme_werks
    )

    assert len(cce_werks) > 10
    cmk.werks.tool.utils.write_precompiled_werks(
        werks_loader_empty.base_dir / "werks-cloud", cce_werks
    )

    cmk.werks.tool.utils.write_precompiled_werks(
        werks_loader_empty.base_dir / "werks-saas", cse_werks
    )

    werks_loaded = werks_loader_empty.load()

    merged_werks = cre_werks
    merged_werks.update(cee_werks)
    merged_werks.update(cme_werks)
    merged_werks.update(cce_werks)
    merged_werks.update(cse_werks)
    assert len(all_werks_raw) == len(merged_werks)

    assert set(merged_werks.keys()) == (werks_loaded.keys())
    for werk_id, werk in werks_loaded.items():
        raw_werk = merged_werks[werk_id]
        assert werk.title == raw_werk.title
        assert werk.description == raw_werk.description


def test_werk_versions(werks_loaded: dict[int, WerkV3]) -> None:
    parsed_version = cmk_version.Version.from_str(cmk_version.__version__)

    for werk_id, werk in werks_loaded.items():
        werk_version = werk.version
        if werk_version is None:
            continue
        parsed_werk_version = cmk_version.Version.from_str(werk_version)

        assert parsed_werk_version <= parsed_version, (
            "Version %s of werk #%d is not allowed in this branch" % (werk.version, werk_id)
        )


def test_no_werk_has_version_2_6_0b1(werks_loaded: dict[int, WerkV3]) -> None:
    for werk_id, werk in werks_loaded.items():
        assert werk.version != "2.6.0b1", (
            f"Werk #{werk_id} has version 2.6.0b1, which will never exists. "
            "The major version after 2.5.0 will be 3.0.0b1."
        )


def test_secwerk_has_cvss(secwerks_loaded: dict[int, WerkV3]) -> None:
    for werk_id, werk in secwerks_loaded.items():
        assert _cvss_vectors(werk.description), (
            f"Werk {werk_id} is missing a CVSS.\n{SECURITY_CONTACT_HINT}\n{werk.description}"
        )


def test_secwerk_has_cve(secwerks_loaded: dict[int, WerkV3]) -> None:
    # Every Sec Werk must reference a CVE: we use Sec Werks only for real vulnerabilities and
    # feature Werks for security improvements. A handful of Werks predate this rule and are
    # grandfathered in SECWERKS_WITHOUT_CVE.
    for werk_id, werk in secwerks_loaded.items():
        if werk_id in SECWERKS_WITHOUT_CVE:
            continue
        # Sec Werks with a CVSS base score of 0 (no impact) are motivated by security but do not
        # describe an actual vulnerability, so they are not required to reference a CVE.
        if _has_no_impact(werk.description):
            continue
        assert CVE_REGEX.search(werk.description) is not None, (
            f"Werk {werk_id} is a Sec Werk but does not reference a CVE. "
            "Sec Werks are reserved for real vulnerabilities (use a feature Werk for security "
            f"improvements).\n{SECURITY_CONTACT_HINT}\n{werk.description}"
        )


@pytest.mark.usefixtures("prepare_git_env")
def test_werk_versions_after_tagged(werks_loaded: dict[int, WerkV3]) -> None:
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
    repo = git.Repo(str(git_dir()))

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


def _cvss_vectors(description: str) -> list[re.Match[str]]:
    return [*CVSS_REGEX_V31.finditer(description), *CVSS_REGEX_V40.finditer(description)]


def _has_no_impact(description: str) -> bool:
    """A CVSS base score of 0 is only possible with no impact, so we look at the impact metrics."""
    vectors = _cvss_vectors(description)
    return bool(vectors) and all(
        metric.endswith(":N") for vector in vectors for metric in vector["impact"].split("/")
    )


def _assert_git_tags_available() -> None:
    # By the time writing, we had more than 700 tags in the git repo
    assert len(_existing_git_tags()) > 700, (
        "The amount of found git tags looks suspicous low. Please check if there is an issue with your checkout"
    )


@lru_cache
def _existing_git_tags() -> frozenset[str]:
    return frozenset(
        subprocess.check_output(
            ["git", "tag", "--list"],
        )
        .decode()
        .split()
    )


def _git_tag_exists(tag: str) -> bool:
    return tag in _existing_git_tags()


def _werk_exists_in_git_tag(tag: str, werk_id: int) -> bool:
    return f".werks/{werk_id}" in _werks_in_git_tag(
        tag
    ) or f".werks/{werk_id}.md" in _werks_in_git_tag(tag)


def _tags_containing_werk(werk_id: int) -> list[str]:
    return _werk_to_git_tag[werk_id]


_werk_to_git_tag: dict[int, list[str]] = defaultdict(list)


@lru_cache
def _werks_in_git_tag(tag: str) -> list[str]:
    werks_in_tag = (
        subprocess.check_output(
            [b"git", b"ls-tree", b"-r", b"--name-only", tag.encode(), b".werks"],
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
