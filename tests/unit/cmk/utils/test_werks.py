# pylint: disable=redefined-outer-name

import os
import subprocess
from collections import defaultdict
from pathlib2 import Path
import pytest  # type: ignore

import testlib
import cmk.utils.werks
import cmk.utils.memoize


@pytest.fixture(scope="function")
def precompiled_werks(tmp_path, monkeypatch):
    all_werks = cmk.utils.werks.load_raw_files(Path(testlib.cmk_path()) / ".werks")
    cmk.utils.werks.write_precompiled_werks(tmp_path / "werks", all_werks)
    monkeypatch.setattr(cmk.utils.werks, "_compiled_werks_dir", lambda: tmp_path)


@pytest.mark.parametrize("edition", [
    "cre",
    "cee",
    "cme",
])
def test_write_precompiled_werks(edition, tmp_path, monkeypatch):
    tmp_dir = str(tmp_path)

    all_werks = cmk.utils.werks.load_raw_files(Path(testlib.cmk_path()) / ".werks")
    cre_werks = dict([(w["id"], w) for w in all_werks.values() if w["edition"] == "cre"])
    cee_werks = dict([(w["id"], w) for w in all_werks.values() if w["edition"] == "cee"])
    cme_werks = dict([(w["id"], w) for w in all_werks.values() if w["edition"] == "cme"])

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
    parsed_version = cmk.utils.werks.parse_check_mk_version(cmk.__version__)

    for werk_id, werk in cmk.utils.werks.load().items():
        parsed_werk_version = cmk.utils.werks.parse_check_mk_version(werk["version"])

        assert parsed_werk_version <= parsed_version, \
            "Version %s of werk #%d is not allowed in this branch" % (werk["version"], werk_id)


def test_werk_versions_after_tagged(precompiled_werks):
    for werk_id, werk in cmk.utils.werks.load().items():
        if werk_id < 8800:
            continue  # Do not care about older versions for the moment

        # Some werks were added after the version was released. Mostly they were forgotten by
        # the developer. Consider it a hall of shame ;)
        if werk_id in set([10062, 10063, 10064]):
            continue

        tag_name = "v%s" % werk["version"]
        if not _git_tag_exists(tag_name):
            #print "No tag found in git: %s. Assuming version was not released yet." % tag_name
            continue

        if not _werk_exists_in_git_tag(tag_name, ".werks/%d" % werk_id):
            werk_tags = sorted(_tags_containing_werk(werk_id),
                               key=lambda t: cmk.utils.werks.parse_check_mk_version(t[1:]))

            raise Exception(
                "Werk #%d has version %s, but is not found in git tag %s. "
                "Looks like the wrong version was declared in this werk. Earliest tag with this werk: %s"
                % (werk_id, werk["version"], tag_name, werk_tags[0] if werk_tags else "-"))


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


_werk_to_git_tag = defaultdict(list)  # type: ignore


@cmk.utils.memoize.MemoizeCache
def _werks_in_git_tag(tag):
    werks_in_tag = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", tag, ".werks"],
                                           cwd=testlib.cmk_path()).split("\n")

    # Populate the map of all tags a werk is in
    for werk_file in werks_in_tag:
        try:
            werk_id = int(os.path.basename(werk_file))
        except ValueError:
            continue
        _werk_to_git_tag[werk_id].append(tag)

    return werks_in_tag
