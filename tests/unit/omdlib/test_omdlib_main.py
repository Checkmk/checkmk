import pytest
from pathlib2 import Path

import omdlib.main


def test_read_skel_permissions(monkeypatch, tmp_path):
    pfile = tmp_path / "skel.permissions"
    pfile.open("w", encoding="utf-8").write(u"bla 755\nblub 644\n")  # pylint: disable=no-member

    monkeypatch.setattr(omdlib.main, "skel_permissions_file_path", lambda v: "%s" % (pfile))

    omdlib.main.read_skel_permissions()
    assert omdlib.main.g_skel_permissions == {'bla': 493, 'blub': 420}


def test_initialize_site_ca(monkeypatch, tmp_path):
    site_id = "tested"
    ca_path = tmp_path / site_id / "etc" / "ssl"
    ca_path.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member

    monkeypatch.setattr(omdlib.certs.CertificateAuthority, "ca_path", property(lambda x: ca_path))

    omdlib.main.initialize_site_ca(omdlib.main.SiteContext(site_id))
    assert (ca_path / "ca.pem").exists()  # pylint: disable=no-member
    assert (ca_path / "sites" / ("%s.pem" % site_id)).exists()  # pylint: disable=no-member


@pytest.fixture()
def site_context():
    return omdlib.main.SiteContext("unit")


@pytest.fixture()
def tmp_fstab(tmp_path, monkeypatch):
    fstab_path = tmp_path / "fstab"
    monkeypatch.setattr(omdlib.main, "fstab_path", lambda: str(fstab_path))
    return fstab_path


def test_add_to_fstab_not_existing(tmp_fstab, site_context):
    assert not tmp_fstab.exists()
    omdlib.main.add_to_fstab(site_context)
    assert not tmp_fstab.exists()


def test_add_to_fstab(tmp_fstab, site_context):
    tmp_fstab.open("w", encoding="utf-8").write(u"# system fstab bla\n")
    omdlib.main.add_to_fstab(site_context)
    assert tmp_fstab.open().read() == (
        "# system fstab bla\n"
        "tmpfs  /opt/omd/sites/unit/tmp tmpfs noauto,user,mode=755,uid=unit,gid=unit 0 0\n")


def test_add_to_fstab_with_size(tmp_fstab, site_context):
    tmp_fstab.open("w", encoding="utf-8").write(u"# system fstab bla\n")
    omdlib.main.add_to_fstab(site_context, tmpfs_size="1G")
    assert tmp_fstab.open().read() == (
        "# system fstab bla\n"
        "tmpfs  /opt/omd/sites/unit/tmp tmpfs noauto,user,mode=755,uid=unit,gid=unit,size=1G 0 0\n")


def test_add_to_fstab_no_newline_at_end(tmp_fstab, site_context):
    tmp_fstab.open("w", encoding="utf-8").write(u"# system fstab bla")
    omdlib.main.add_to_fstab(site_context)
    assert tmp_fstab.open().read() == (
        "# system fstab bla\n"
        "tmpfs  /opt/omd/sites/unit/tmp tmpfs noauto,user,mode=755,uid=unit,gid=unit 0 0\n")


def test_add_to_fstab_empty(tmp_fstab, site_context):
    tmp_fstab.open("w", encoding="utf-8").write(u"")
    omdlib.main.add_to_fstab(site_context)
    assert tmp_fstab.open().read() == (
        "tmpfs  /opt/omd/sites/unit/tmp tmpfs noauto,user,mode=755,uid=unit,gid=unit 0 0\n")
