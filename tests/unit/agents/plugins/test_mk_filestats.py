# -*- encoding: utf-8
# pylint: disable=protected-access,redefined-outer-name
import os
import ast
import pytest  # type: ignore
from testlib import import_module


@pytest.fixture(scope="module")
def mk_filestats():
    return import_module("agents/plugins/mk_filestats.py")


def test_lazy_file(mk_filestats):
    lfile = mk_filestats.LazyFileStats("no such file")
    assert lfile.path == "no such file"
    assert lfile._size is None
    assert lfile._age is None

    assert lfile.stat_status is None
    assert lfile.size is None
    assert lfile.stat_status == "file vanished"
    assert lfile.age is None

    assert isinstance(ast.literal_eval(lfile.dumps()), dict)

    lfile = mk_filestats.LazyFileStats(__file__)  # this should exist...
    assert lfile.path == __file__
    assert lfile.size == os.stat(__file__).st_size
    assert lfile.stat_status == "ok"
    assert lfile.age is not None
    assert isinstance(ast.literal_eval(lfile.dumps()), dict)


@pytest.mark.parametrize("config", [({}), ({
    "input_unknown": None
}), ({
    "input_one": None,
    "input_two": None
})])
def test_get_file_iterator_invalid(mk_filestats, config):
    with pytest.raises(ValueError):
        mk_filestats.get_file_iterator(config)


@pytest.mark.parametrize("config,pat_list", [
    ({
        "input_patterns": "foo"
    }, ["foo"]),
    ({
        "input_patterns": '"foo bar" gee*'
    }, ["foo bar", "gee*"]),
])
def test_get_file_iterator_pattern(mk_filestats, config, pat_list):
    iter_obj = mk_filestats.get_file_iterator(config)
    assert isinstance(iter_obj, mk_filestats.PatternIterator)
    assert iter_obj._patterns == [os.path.abspath(p) for p in pat_list]


@pytest.mark.parametrize("operator,values,results", [
    ('>', (2000., 1024, "1000"), (True, False, False)),
    ('>=', (2000., 1024, "1000"), (True, True, False)),
    ('<', (2000., 1024, "1000"), (False, False, True)),
    ('<=', (2000., 1024, "1000"), (False, True, True)),
    ('==', (2000., 1024, "1000"), (False, True, False)),
])
def test_numeric_filter(mk_filestats, operator, values, results):
    num_filter = mk_filestats.AbstractNumericFilter('%s1024' % operator)
    for value, result in zip(values, results):
        assert result == num_filter._matches_value(value)


@pytest.mark.parametrize("invalid_arg", ['<>1024', '<NaN'])
def test_numeric_filter_raises(mk_filestats, invalid_arg):
    with pytest.raises(ValueError):
        mk_filestats.AbstractNumericFilter(invalid_arg)


@pytest.mark.parametrize("reg_pat,paths,results", [(
    r'.*\.txt',
    ("/path/to/some.txt", "to/sometxt", "/path/to/some.TXT"),
    (True, False, False),
), (u'[^ð]*ð{2}[^ð]*', (u'foðbar', u'fððbar'), (False, True))])
def test_path_filter(mk_filestats, reg_pat, paths, results):
    path_filter = mk_filestats.RegexFilter(reg_pat)
    for path, result in zip(paths, results):
        lazy_file = mk_filestats.LazyFileStats(path)
        assert result == path_filter.matches(lazy_file)


@pytest.mark.parametrize("config", [
    {
        "filter_foo": None
    },
    {
        "filter_size": "!=käse"
    },
])
def test_get_file_filters_invalid(mk_filestats, config):
    with pytest.raises(ValueError):
        mk_filestats.get_file_filters(config)


def test_get_file_filters(mk_filestats):
    config = {"filter_size": ">1", "filter_age": "==0", "filter_regex": "foo"}
    filters = mk_filestats.get_file_filters(config)
    assert len(filters) == 3
    assert isinstance(filters[0], mk_filestats.RegexFilter)
    assert isinstance(filters[1], mk_filestats.AbstractNumericFilter)
    assert isinstance(filters[2], mk_filestats.AbstractNumericFilter)


@pytest.mark.parametrize("config", [{}, {"output": "/dev/null"}])
def test_get_ouput_aggregator_invalid(mk_filestats, config):
    with pytest.raises(ValueError):
        mk_filestats.get_output_aggregator(config)


@pytest.mark.parametrize("output_value", ["count_only", "file_stats"])
def test_get_ouput_aggregator(mk_filestats, output_value):
    aggr = mk_filestats.get_output_aggregator({"output": output_value})
    assert aggr is getattr(mk_filestats, "output_aggregator_%s" % output_value)
