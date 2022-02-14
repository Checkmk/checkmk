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

import pytest  # type: ignore[import]
from six import ensure_binary, ensure_str

import testlib

import cmk.utils.version as cmk_version
import cmk.utils.werks
import cmk.utils.memoize


@pytest.mark.parametrize("version_str,expected", [
    ("1.2.0", 1020050000),
    ("1.2.0i1", 1020010100),
    ("1.2.0b1", 1020020100),
    ("1.2.0b10", 1020021000),
    ("1.2.0p10", 1020050010),
    ("2.0.0i1", 2000010100),
    ("1.6.0-2020.05.26", 1060090000),
    ("2020.05.26", 2020052650000),
    ("2020.05.26-sandbox-lm-1.7-drop-py2", 2020052600000),
])
def test_parse_check_mk_version(version_str, expected):
    assert cmk.utils.werks.parse_check_mk_version(version_str) == expected


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
    parsed_version = cmk.utils.werks.parse_check_mk_version(cmk_version.__version__)

    for werk_id, werk in cmk.utils.werks.load().items():
        parsed_werk_version = cmk.utils.werks.parse_check_mk_version(werk["version"])

        assert parsed_werk_version <= parsed_version, \
            "Version %s of werk #%d is not allowed in this branch" % (werk["version"], werk_id)


def test_werk_versions_after_tagged(precompiled_werks):
    list_of_offenders = []
    for werk_id, werk in cmk.utils.werks.load().items():
        if werk_id < 8800:
            continue  # Do not care about older versions for the moment

        # Some werks were added after the version was released. Mostly they were forgotten by
        # the developer. Consider it a hall of shame ;)
        if werk_id in {10062, 10063, 10064, 10125, 12836, 13083}:
            continue

        tag_name = "v%s" % werk["version"]
        if not _git_tag_exists(tag_name):
            #print "No tag found in git: %s. Assuming version was not released yet." % tag_name
            continue

        if not _werk_exists_in_git_tag(tag_name, ".werks/%d" % werk_id):
            werk_tags = sorted(_tags_containing_werk(werk_id),
                               key=lambda t: cmk.utils.werks.parse_check_mk_version(t[1:]))
            list_of_offenders.append(
                (werk_id, werk["version"], tag_name, werk_tags[0] if werk_tags else "-"))

    assert not list_of_offenders, (
        "The following Werks are not found in the git tag corresponding to their Version. "
        "Looks like the wrong version was declared in these werks:\n" +
        "\n".join("Werk #%d has version %s, not found in git tag %s, first found in %s" % entry
                  for entry in list_of_offenders))


@cmk.utils.memoize.MemoizeCache
def _git_tag_exists(tag):
    return subprocess.Popen(
        ["git", "rev-list", tag],
        stdout=open(os.devnull, "w"),
        stderr=subprocess.STDOUT,
        cwd=testlib.cmk_path(),
    ).wait() == 0


def _werk_exists_in_git_tag(tag, rel_path):
    return rel_path in _werks_in_git_tag(tag)


def _tags_containing_werk(werk_id):
    return _werk_to_git_tag[werk_id]


_werk_to_git_tag = defaultdict(list)


@cmk.utils.memoize.MemoizeCache
def _werks_in_git_tag(tag):
    werks_in_tag = ensure_str(
        subprocess.check_output(
            [b"git", b"ls-tree", b"-r", b"--name-only",
             ensure_binary(tag), b".werks"],
            cwd=ensure_binary(testlib.cmk_path()))).split("\n")

    # Populate the map of all tags a werk is in
    for werk_file in werks_in_tag:
        try:
            werk_id = int(os.path.basename(werk_file))
        except ValueError:
            continue
        _werk_to_git_tag[werk_id].append(tag)

    return werks_in_tag
