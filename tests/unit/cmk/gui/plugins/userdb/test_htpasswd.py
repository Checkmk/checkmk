#!/usr/bin/env python3
# encoding: utf-8

import pytest

import cmk.gui.plugins.userdb.htpasswd as htpasswd


@pytest.fixture(name="test_config")
def fixture_test_config(tmp_path):
    file_path = tmp_path / "htpasswd"
    htpwd = htpasswd.Htpasswd(file_path)

    htpwd.save(
        {
            "non-unicode": "non-unicode",
            "abcä": "bbbä",
        }
    )

    return htpwd


def test_load(test_config):
    assert test_config.load() == {
        "non-unicode": "non-unicode",
        "abcä": "bbbä",
    }


def test_exists(test_config):
    assert test_config.exists("non-unicode")
    assert test_config.exists("non-unicode")
    assert not test_config.exists("not-existant")
    assert not test_config.exists("not-existant")
    assert not test_config.exists("")


def test_save(tmp_path):
    file_path = tmp_path / "htpasswd"
    htpwd = htpasswd.Htpasswd(file_path)

    htpwd.save(
        {
            "non-unicode": "non-unicode",
            "abcä": "bbbä",
        }
    )

    loaded = htpwd.load()
    assert loaded == {
        "non-unicode": "non-unicode",
        "abcä": "bbbä",
    }
