#!/usr/bin/env python

from pathlib2 import Path
import pytest

import testlib
import cmk.utils.werks


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
