# encoding: utf-8

import os
import time
import six

import cmk.gui.config as config
import cmk.gui.key_mgmt as key_mgmt


def test_key_mgmt_create_key(monkeypatch):
    monkeypatch.setattr(config.user, "id", u"dingdöng")
    monkeypatch.setattr(time, "time", lambda: 123)

    key_dict = key_mgmt.PageEditKey()._generate_key(u"älias", "passphra$e")
    assert isinstance(key_dict, dict)
    assert sorted(key_dict.keys()) == ["alias", "certificate", "date", "owner", "private_key"]
    assert isinstance(key_dict["alias"], six.text_type)
    assert key_dict["alias"] == u"älias"

    assert key_dict["date"] == 123

    assert isinstance(key_dict["owner"], six.text_type)
    assert key_dict["owner"] == u"dingdöng"

    assert key_dict["certificate"].startswith("-----BEGIN CERTIFICATE---")
    assert key_dict["private_key"].startswith("-----BEGIN ENCRYPTED PRIVATE KEY---")
