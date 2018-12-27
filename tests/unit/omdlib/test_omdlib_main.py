from pathlib2 import Path

import omdlib.main


def test_read_skel_permissions(monkeypatch, tmpdir):
    tmp_path = Path("%s" % tmpdir)
    pfile = tmp_path / "skel.permissions"
    pfile.open("w", encoding="utf-8").write(u"bla 755\nblub 644\n")  # pylint: disable=no-member

    monkeypatch.setattr(omdlib.main, "skel_permissions_file_path", lambda v: "%s" % (pfile))

    omdlib.main.read_skel_permissions()
    assert omdlib.main.g_skel_permissions == {'bla': 493, 'blub': 420}


def test_initialize_site_ca(monkeypatch, tmpdir):
    site_id = "tested"
    ca_path = Path("%s" % tmpdir) / site_id / "etc" / "ssl"
    ca_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(omdlib.certs.CertificateAuthority, "ca_path", property(lambda x: ca_path))

    omdlib.main.initialize_site_ca(omdlib.main.SiteContext(site_id))
    assert (ca_path / "ca.pem").exists()
    assert (ca_path / "sites" / ("%s.pem" % site_id)).exists()
