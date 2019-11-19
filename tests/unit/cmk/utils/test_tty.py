# -*- coding: utf-8 -*-

import pytest  # type: ignore
import cmk.utils.tty


@pytest.mark.parametrize("row", [
    ['check.type', None],
    ['check.type', ""],
    ['check.type', b"h\xc3\xa9 \xc3\x9f\xc3\x9f"],
    ['check.type', u"hé ßß"],
    ['check.type', 123],
    ['check.type', 123.4],
    ['check.type', {}],
    ['check.type', []],
])
def test_print_table(capsys, row):
    cmk.utils.tty.print_table(["foo", "bar"], ["", ""], [row])
