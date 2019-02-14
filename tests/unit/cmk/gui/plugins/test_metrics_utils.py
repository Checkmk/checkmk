# -*- coding: utf-8 -*-
import pytest
import cmk.gui.config
from cmk.gui.plugins.metrics import utils


@pytest.mark.parametrize(
    "data_string, result",
    [
        ("he lo", ["he", "lo"]),
        ("'há li'", ["há li"]),
        (u"hé ßß", [u"hé", u"ßß"]),
    ],
)
def test_split_perf_data(data_string, result):
    assert utils._split_perf_data(data_string) == result


@pytest.mark.parametrize("perf_str, check_command, result", [
    ('', None, ([], None)),
    ('hi ho', None, ([], None)),
    ('hi=6 [ihe]', 'ter', ([('hi', 6, '', None, None, None, None)], 'ihe')),
    (u'hi=l6 [ihe]', 'ter', ([], 'ihe')),
    (u'hi=6 [ihe]', 'ter', ([('hi', 6, '', None, None, None, None)], 'ihe')),
    ('hi=5 no=6', 'test', ([('hi', 5, u'', None, None, None, None),
                            ('no', 6, u'', None, None, None, None)], 'test')),
    ('hi=5;6;7;8;9 \'not here\'=6;5.6;;;', 'test',
     ([('hi', 5, u'', 6, 7, 8, 9), ('not_here', 6, u'', 5.6, None, None, None)], 'test')),
    ('hi=5G;;;; \'not here\'=6M;5.6;;;', 'test',
     ([('hi', 5, u'G', None, None, None, None),
       ('not_here', 6, u'M', 5.6, None, None, None)], 'test')),
])
def test_parse_perf_data(perf_str, check_command, result):
    assert utils.parse_perf_data(perf_str, check_command) == result


def test_parse_perf_data2(monkeypatch):
    with pytest.raises(ValueError):
        monkeypatch.setattr(cmk.gui.config, "debug", True)
        utils.parse_perf_data('hi ho', None)
