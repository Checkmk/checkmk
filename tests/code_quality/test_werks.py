#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path

import pytest

import tests.testlib as testlib
from tests.testlib import repo_path

import cmk.utils.memoize
import cmk.utils.version as cmk_version
import cmk.utils.werks


def _render_description(description: str | cmk.utils.werks.werk.NoWiki) -> str:
    # reimplementation of cmk.gui.werks.render_description
    # can be removed as soon as all werks are converted to markdown
    if isinstance(description, cmk.utils.werks.werk.NoWiki):
        return "\n".join(description.value)
    return description


CVSS_REGEX_V31 = re.compile(
    r"CVSS:3.1/AV:[NALP]/AC:[LH]/PR:[NLH]/UI:[NR]/S:[UC]/C:[NLH]/I:[NLH]/A:[NLH]"
)
CVSS_REGEX_V40 = re.compile(
    r"CVSS:4.0/AV:[NALP]/AC:[LH]/AT:[NP]/PR:[NLH]/UI:[NPA]/VC:[NLH]/VI:[NLH]/VA:[NLH]/SC:[NLH]/SI:[NLH]/SA:[NLH]"
)


@pytest.mark.parametrize(
    "version_str",
    [
        "1.2.0",
        "1.2.0i1",
        "1.2.0b1",
        "1.2.0b10",
        "1.2.0p10",
        "2.0.0i1",
        "1.6.0-2020.05.26",
        "2020.05.26",
    ],
)
def test_old_parse_check_mk_version_equals_new_version_class(
    version_str: str,
) -> None:
    assert (
        cmk_version.parse_check_mk_version(version_str)
        == cmk_version.Version(version_str).parse_to_int()
    )


@pytest.mark.parametrize(
    "version_str_a,version_str_b",
    [
        ("1.2.0", "1.2.0i1"),
        ("1.2.0", "1.2.0b1"),
        ("1.2.0p1", "1.2.0"),
        ("1.2.0i2", "1.2.0i1"),
        ("1.2.0b2", "1.2.0b1"),
        ("1.2.0p2", "1.2.0p1"),
        ("1.2.1", "1.2.0"),
        ("1.3.0", "1.2.1"),
        ("2.0.0", "1.2.1"),
        ("2.0.0-2020.05.26", "2.0.0-2020.05.25"),
        ("2.0.0-2020.05.26", "2.0.0-2020.04.26"),
        ("2.0.0-2020.05.26", "2.0.0-2019.05.26"),
        ("2.0.1-2020.05.26", "2.0.0-2020.05.26"),
        ("2.1.0-2020.05.26", "2.0.0-2020.05.26"),
        ("2.0.0-2020.05.26", "2.0.0i2"),
        ("2.0.0-2020.05.26", "2.0.0b2"),
        ("2.0.0-2020.05.26", "2.0.0"),
        ("2.0.0-2020.05.26", "2.0.0p7"),
        ("2020.05.26", "2020.05.25"),
        ("2020.05.26", "2020.04.26"),
        ("2020.05.26", "2.0.0-2020.05.25"),
        ("2022.06.02-sandbox-lm-2.2-thing", "2022.06.01"),
        ("2.1.0-2022.06.02-sandbox-lm-2.2-thing", "2.1.0-2022.06.01"),
    ],
)
def test_version_comparison(version_str_a: str, version_str_b: str) -> None:
    a = cmk_version.Version(version_str_a)
    b = cmk_version.Version(version_str_b)

    assert a > b


@pytest.fixture(scope="function", name="precompiled_werks")
def fixture_precompiled_werks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    all_werks = cmk.utils.werks.load_raw_files(Path(testlib.cmk_path()) / ".werks")
    cmk.utils.werks.write_precompiled_werks(tmp_path / "werks", {w.id: w for w in all_werks})
    monkeypatch.setattr(cmk.utils.werks, "_compiled_werks_dir", lambda: tmp_path)


def test_write_precompiled_werks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tmp_dir = str(tmp_path)

    all_werks = cmk.utils.werks.load_raw_files(Path(testlib.cmk_path()) / ".werks")
    cre_werks = {w.id: w for w in all_werks if w.edition == "cre"}
    cee_werks = {w.id: w for w in all_werks if w.edition == "cee"}
    cme_werks = {w.id: w for w in all_werks if w.edition == "cme"}
    cce_werks = {w.id: w for w in all_werks if w.edition == "cce"}
    assert len(all_werks) == len(cre_werks) + len(cee_werks) + len(cme_werks) + len(cce_werks)

    assert len(cre_werks) > 9847
    assert [w for w in cre_werks.keys() if 9000 <= w < 10000] == []
    cmk.utils.werks.write_precompiled_werks(Path(tmp_dir) / "werks", cre_werks)

    assert len(cee_werks) > 1358
    cmk.utils.werks.write_precompiled_werks(Path(tmp_dir) / "werks-enterprise", cee_werks)

    assert len(cme_werks) > 50
    cmk.utils.werks.write_precompiled_werks(Path(tmp_dir) / "werks-managed", cme_werks)

    assert len(cce_werks) > 10
    cmk.utils.werks.write_precompiled_werks(Path(tmp_dir) / "werks-cloud", cce_werks)

    monkeypatch.setattr(cmk.utils.werks, "_compiled_werks_dir", lambda: Path(tmp_dir))
    werks_loaded = cmk.utils.werks.load()

    merged_werks = cre_werks
    merged_werks.update(cee_werks)
    merged_werks.update(cme_werks)
    merged_werks.update(cce_werks)
    assert len(all_werks) == len(merged_werks)

    assert set(merged_werks.keys()) == (werks_loaded.keys())
    for werk_id, werk in werks_loaded.items():
        raw_werk = merged_werks[werk_id]
        assert werk.title == raw_werk.title
        assert _render_description(werk.description) == "\n".join(raw_werk.description)


def test_werk_versions(precompiled_werks: None) -> None:
    parsed_version = cmk_version.Version(cmk_version.__version__)

    for werk_id, werk in cmk.utils.werks.load().items():
        parsed_werk_version = cmk_version.Version(werk.version)

        assert (
            parsed_werk_version <= parsed_version
        ), "Version %s of werk #%d is not allowed in this branch" % (werk.version, werk_id)


def test_secwerk_has_cvss(precompiled_werks: None) -> None:
    # The CVSS in Sec Werks is only mandatory for new Werks, so we start with 14485
    skip_lower = 14485
    for werk_id, werk in cmk.utils.werks.load().items():
        if werk_id < skip_lower:
            continue
        if werk.class_.value != "security":
            continue
        rendered = _render_description(werk.description)
        assert (
            CVSS_REGEX_V31.search(rendered) is not None
            or CVSS_REGEX_V40.search(rendered) is not None
        ), f"Werk {werk_id} is missing a CVSS:\n{werk.description}"


def test_werk_versions_after_tagged(precompiled_werks: None) -> None:
    _assert_git_tags_available()

    list_of_offenders = []
    for werk_id, werk in cmk.utils.werks.load().items():
        if werk_id < 8800:
            continue  # Do not care about older versions for the moment

        # Some werks were added after the version was released. Mostly they were forgotten by
        # the developer. Consider it a hall of shame ;)
        if werk_id in {10062, 10063, 10064, 10125, 12836, 15194, 15493, 16228, 16453}:
            continue

        tag_name = "v%s" % werk.version
        if not _git_tag_exists(tag_name):
            # print "No tag found in git: %s. Assuming version was not released yet." % tag_name
            continue

        if not _werk_exists_in_git_tag(tag_name, ".werks/%d" % werk_id):
            werk_tags = sorted(
                _tags_containing_werk(werk_id),
                key=lambda t: cmk_version.Version(t[1:]),
            )
            list_of_offenders.append(
                (werk_id, werk.version, tag_name, werk_tags[0] if werk_tags else "-")
            )

    assert not list_of_offenders, (
        "The following Werks are not found in the git tag corresponding to their Version. "
        "Looks like the wrong version was declared in these werks:\n"
        + "\n".join(
            "Werk #%d has version %s, not found in git tag %s, first found in %s" % entry
            for entry in list_of_offenders
        )
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
    ), "The amount of found git tags looks suspicous low. Please check if there is an issue with your checkout"


@cmk.utils.memoize.MemoizeCache
def _git_tag_exists(tag: str) -> bool:
    return (
        subprocess.Popen(
            ["git", "rev-list", tag],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            cwd=testlib.cmk_path(),
        ).wait()
        == 0
    )


def _werk_exists_in_git_tag(tag: str, rel_path: str) -> bool:
    return rel_path in _werks_in_git_tag(tag)


def _tags_containing_werk(werk_id: int) -> list[str]:
    return _werk_to_git_tag[werk_id]


_werk_to_git_tag = defaultdict(list)


@cmk.utils.memoize.MemoizeCache
def _werks_in_git_tag(tag: str) -> list[str]:
    werks_in_tag = (
        subprocess.check_output(
            [b"git", b"ls-tree", b"-r", b"--name-only", tag.encode(), b".werks"],
            cwd=testlib.cmk_path().encode(),
        )
        .decode()
        .split("\n")
    )

    # Populate the map of all tags a werk is in
    for werk_file in werks_in_tag:
        try:
            werk_id = int(os.path.basename(werk_file))
        except ValueError:
            continue
        _werk_to_git_tag[werk_id].append(tag)

    return werks_in_tag
