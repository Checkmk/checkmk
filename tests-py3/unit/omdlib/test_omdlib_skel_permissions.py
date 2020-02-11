#!/usr/bin/env python3
# pylint: disable=redefined-outer-name

import omdlib.skel_permissions
import omdlib.main


def test_read_skel_permissions(monkeypatch, tmp_path):
    pfile = tmp_path / "skel.permissions"
    pfile.open("w", encoding="utf-8").write(u"bla 755\nblub 644\n")  # pylint: disable=no-member

    monkeypatch.setattr(omdlib.skel_permissions, "skel_permissions_file_path", lambda v: "%s" %
                        (pfile))

    assert omdlib.main.read_skel_permissions() == {'bla': 493, 'blub': 420}
