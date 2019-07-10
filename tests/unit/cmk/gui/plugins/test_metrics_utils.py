# -*- coding: utf-8 -*-
import pytest
import cmk.gui.config
from cmk.gui.plugins.metrics import utils


@pytest.mark.parametrize("data_string, result", [
    ("he lo", ["he", "lo"]),
    ("'há li'", ["há li"]),
    (u"hé ßß", [u"hé", u"ßß"]),
])
def test_split_perf_data(data_string, result):
    assert utils._split_perf_data(data_string) == result


@pytest.mark.parametrize("perf_str, check_command, result", [
    ("", None, ([], None)),
    ("hi=6 [ihe]", "ter", ([("hi", 6, "", None, None, None, None)], "ihe")),
    (u"hi=l6 [ihe]", "ter", ([], "ihe")),
    (u"hi=6 [ihe]", "ter", ([("hi", 6, "", None, None, None, None)], "ihe")),
    ("hi=5 no=6", "test", ([
        ("hi", 5, u"", None, None, None, None),
        ("no", 6, u"", None, None, None, None),
    ], "test")),
    ("hi=5;6;7;8;9 'not here'=6;5.6;;;", "test", ([
        ("hi", 5, u"", 6, 7, 8, 9),
        ("not_here", 6, u"", 5.6, None, None, None),
    ], "test")),
    ("hi=5G;;;; 'not here'=6M;5.6;;;", "test", ([
        ("hi", 5, u"G", None, None, None, None),
        ("not_here", 6, u"M", 5.6, None, None, None),
    ], "test")),
])
def test_parse_perf_data(perf_str, check_command, result):
    assert utils.parse_perf_data(perf_str, check_command) == result


def test_parse_perf_data2(monkeypatch):
    with pytest.raises(ValueError):
        monkeypatch.setattr(cmk.gui.config, "debug", True)
        utils.parse_perf_data("hi ho", None)


@pytest.mark.parametrize("perf_name, check_command, result", [
    ("in", "check_mk-lnx_if", {
        "scale": 8,
        "name": "if_in_bps",
        "auto_graph": True
    }),
    ("memused", "check_mk-hr_mem", {
        "auto_graph": False,
        "name": "total_used",
        "scale": 1024**2
    }),
    ("fake", "check_mk-imaginary", {
        "auto_graph": True,
        "name": "fake",
        "scale": 1.0
    }),
])
def test_perfvar_translation(perf_name, check_command, result):
    assert utils.perfvar_translation(perf_name, check_command) == result


@pytest.mark.parametrize("perf_data, check_command, result", [
    (("in", 496876.200933, "", None, None, 0, 125000000), 'check_mk-lnx_if', ('if_in_bps', {
        "orig_name": "in",
        "value": 3975009.607464,
        "scalar": {
            "max": 1000000000,
            "min": 0
        },
        "scale": 8,
        "auto_graph": True,
    })),
    (("fast", 5, "", 4, 9, 0, 10), 'check_mk-imaginary', ('fast', {
        "orig_name": "fast",
        "value": 5.0,
        "scalar": {
            "warn": 4.0,
            "crit": 9.0,
            "min": 0.0,
            "max": 10.0
        },
        "scale": 1.0,
        "auto_graph": True,
    })),
])
def test_normalize_perf_data(perf_data, check_command, result):
    assert utils.normalize_perf_data(perf_data, check_command) == result


@pytest.mark.parametrize("canonical_name, perf_data_names", [
    ('user', {'user'}),
    ('io_wait', {'wait', 'io_wait'}),
    ('mem_used', {'mem_used', 'memory', 'memory_used', 'memused', 'ramused', 'usage'}),
])
def test_reverse_translation_metric_name(canonical_name, perf_data_names):
    assert utils.reverse_translate_metric_name, (canonical_name) == perf_data_names


@pytest.mark.parametrize(
    "metric_names, check_command, graph_ids",
    [
        ([u'user', u'system', u'wait', u'util'
         ], 'check_mk-kernel.util', ['util_average_1', 'cpu_utilization_5']),  # TODO: drop first
        ([u'util1', u'util15'], None, ['util_average_2']),
        ([u'util'], None, ['util_average_1']),
        ([u'util', u'util_average'], None, ['util_average_1']),
        ([u'user', u'util_numcpu_as_max'], None, ['cpu_utilization_numcpus']),
        ([u'user', u'system', u'idle', u'nice'], None, ['cpu_utilization_3']),
        ([u'user', u'system', u'idle', u'io_wait'
         ], None, ['cpu_utilization_4', 'cpu_utilization_5']),  # TODO: drop 5
        ([u'user', u'system', u'io_wait'], None, ['cpu_utilization_5']),
        ([u'user', u'system', u'io_wait', 'guest', 'steal'
         ], 'check_mk-statgrab_cpu', ['cpu_utilization_7']),
        ([u'user', u'system', u'interrupt'], None, ['cpu_utilization_8']),
        ([u'user', u'system', u'wait', u'util', u'cpu_entitlement', u'cpu_entitlement_util'
         ], 'check_mk-lparstat_aix.cpu_util',
         ['util_average_1', 'cpu_utilization_5', 'cpu_entitlement']),  # TODO: drop first
    ])
def test_get_graph_templates(load_plugins, metric_names, check_command, graph_ids):
    perfdata = [(n, 0, u'', None, None, None, None) for n in metric_names]
    translated_metrics = utils.translate_metrics(perfdata, check_command)
    templates = utils.get_graph_templates(translated_metrics)
    assert set(graph_ids) == set(t['id'] for t in templates)
