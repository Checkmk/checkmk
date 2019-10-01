import os
import cmk


# Would move this to unit tests, but it would not work, because the
# unit tests monkeypatch the cmk.omd_version() function
def test_omd_version(tmp_path, monkeypatch):
    link_path = str(tmp_path / "version")

    monkeypatch.setattr(cmk.utils.paths, 'omd_root', os.path.dirname(link_path))

    os.symlink("/omd/versions/2016.09.12.cee", link_path)
    assert cmk.omd_version() == "2016.09.12.cee"
    os.unlink(link_path)

    os.symlink("/omd/versions/2016.09.12.cee.demo", link_path)
    assert cmk.omd_version() == "2016.09.12.cee.demo"
    os.unlink(link_path)
