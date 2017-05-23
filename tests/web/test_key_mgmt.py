# encoding: utf-8

import os
import time

def test_key_mgmt_create_key(monkeypatch):
    import config
    monkeypatch.setattr(config.user, "id", u"dingdöng")
    monkeypatch.setattr(time, "time", lambda: 123)

    import key_mgmt
    key_dict = key_mgmt.PageEditKey()._generate_key(u"älias", "passphra$e")
    assert type(key_dict) == dict
    assert sorted(key_dict.keys()) == [ "alias", "certificate", "date", "owner", "private_key" ]
    assert type(key_dict["alias"]) == unicode
    assert key_dict["alias"] == u"älias"

    assert key_dict["date"] == 123

    assert type(key_dict["owner"]) == unicode
    assert key_dict["owner"] == u"dingdöng"

    assert key_dict["certificate"].startswith("-----BEGIN CERTIFICATE---")
    assert key_dict["private_key"].startswith("-----BEGIN ENCRYPTED PRIVATE KEY---")
