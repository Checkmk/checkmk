#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import os
import subprocess
from collections import defaultdict
from pathlib import Path

import pytest

import tests.testlib as testlib

import cmk.utils.memoize
import cmk.utils.version as cmk_version
import cmk.utils.werks


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
def test_old_parse_check_mk_version_equals_new_version_class(version_str):
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
    ],
)
def test_version_comparison(version_str_a, version_str_b):
    a = cmk_version.Version(version_str_a)
    b = cmk_version.Version(version_str_b)

    assert a > b


@pytest.fixture(scope="function")
def precompiled_werks(tmp_path, monkeypatch):
    all_werks = cmk.utils.werks.load_raw_files(Path(testlib.cmk_path()) / ".werks")
    cmk.utils.werks.write_precompiled_werks(tmp_path / "werks", all_werks)
    monkeypatch.setattr(cmk.utils.werks, "_compiled_werks_dir", lambda: tmp_path)


def test_write_precompiled_werks(tmp_path, monkeypatch):
    tmp_dir = str(tmp_path)

    all_werks = cmk.utils.werks.load_raw_files(Path(testlib.cmk_path()) / ".werks")
    cre_werks = {w["id"]: w for w in all_werks.values() if w["edition"] == "cre"}
    cee_werks = {w["id"]: w for w in all_werks.values() if w["edition"] == "cee"}
    cme_werks = {w["id"]: w for w in all_werks.values() if w["edition"] == "cme"}

    assert len(cre_werks) > 1000
    assert [w for w in cre_werks.keys() if 9000 <= w < 10000] == []
    cmk.utils.werks.write_precompiled_werks(Path(tmp_dir) / "werks", cre_werks)

    assert len(cee_werks) > 700
    cmk.utils.werks.write_precompiled_werks(Path(tmp_dir) / "werks-enterprise", cee_werks)

    assert len(cme_werks) > 5
    cmk.utils.werks.write_precompiled_werks(Path(tmp_dir) / "werks-managed", cme_werks)

    monkeypatch.setattr(cmk.utils.werks, "_compiled_werks_dir", lambda: Path(tmp_dir))
    werks_loaded = cmk.utils.werks.load()

    merged_werks = cre_werks
    merged_werks.update(cee_werks)
    merged_werks.update(cme_werks)

    assert merged_werks == werks_loaded


def test_werk_versions(precompiled_werks):
    parsed_version = cmk_version.Version(cmk_version.__version__)

    for werk_id, werk in cmk.utils.werks.load().items():
        parsed_werk_version = cmk_version.Version(werk["version"])

        assert (
            parsed_werk_version <= parsed_version
        ), "Version %s of werk #%d is not allowed in this branch" % (werk["version"], werk_id)


def test_werk_versions_after_tagged(precompiled_werks):
    list_of_offenders = []
    for werk_id, werk in cmk.utils.werks.load().items():
        if werk_id < 8800:
            continue  # Do not care about older versions for the moment

        # Some werks were added after the version was released. Mostly they were forgotten by
        # the developer. Consider it a hall of shame ;)
        if werk_id in {10062, 10063, 10064, 10125, 12836, 13810, 13788, 13789, 13930, 14101}:
            continue

        tag_name = "v%s" % werk["version"]
        if not _git_tag_exists(tag_name):
            # print "No tag found in git: %s. Assuming version was not released yet." % tag_name
            continue

        if not _werk_exists_in_git_tag(tag_name, ".werks/%d" % werk_id):
            werk_tags = sorted(
                _tags_containing_werk(werk_id),
                key=lambda t: cmk_version.Version(t[1:]),
            )
            list_of_offenders.append(
                (werk_id, werk["version"], tag_name, werk_tags[0] if werk_tags else "-")
            )

    assert not list_of_offenders, (
        "The following Werks are not found in the git tag corresponding to their Version. "
        "Looks like the wrong version was declared in these werks:\n"
        + "\n".join(
            "Werk #%d has version %s, not found in git tag %s, first found in %s" % entry
            for entry in list_of_offenders
        )
    )


@cmk.utils.memoize.MemoizeCache
def _git_tag_exists(tag):
    return (
        subprocess.Popen(
            ["git", "rev-list", tag],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            cwd=testlib.cmk_path(),
        ).wait()
        == 0
    )


def _werk_exists_in_git_tag(tag: str, rel_path):
    return rel_path in _werks_in_git_tag(tag)


def _tags_containing_werk(werk_id):
    return _werk_to_git_tag[werk_id]


_werk_to_git_tag = defaultdict(list)


@cmk.utils.memoize.MemoizeCache
def _werks_in_git_tag(tag: str):
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
