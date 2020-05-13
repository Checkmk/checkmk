import json

import cmk.gui.htmllib  # noqa: F401 pylint: disable=unused-import


class Bla(object):
    def to_json(self):
        return {"class": "Bla"}


def test_to_json():
    assert json.dumps(Bla()) == '{"class": "Bla"}'


def test_forward_slash_escape():
    assert json.dumps("<script>alert(1)</script>") == '"<script>alert(1)<\\/script>"'
