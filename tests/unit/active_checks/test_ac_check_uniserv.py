# -*- encoding: utf-8
# pylint: disable=protected-access,redefined-outer-name
import pytest  # type: ignore
from testlib import import_module  # pylint: disable=import-error


@pytest.fixture(scope="module")
def check_uniserv():
    return import_module("active_checks/check_uniserv")


@pytest.mark.parametrize("args", [
    [],
    [
        "host",
    ],
    ["host", "port"],
    ["host", "port", "service"],
    ["host", "port", "service", "ADDRESS"],
    ["host", "port", "service", "ADDRESS", "street"],
    ["host", "port", "service", "ADDRESS", "street", "street_nr"],
    ["host", "port", "service", "ADDRESS", "street", "street_nr", "city", "regex"],
])
def test_ac_check_uniserv_broken_arguments(capsys, check_uniserv, args):
    with pytest.raises(SystemExit):
        check_uniserv.parse_arguments(args)
    out, _err = capsys.readouterr()
    assert out == " Usage: check_uniserv HOSTNAME PORT SERVICE (VERSION|ADDRESS STREET NR CITY SEARCH_REGEX)\n"


@pytest.mark.parametrize("args, expected_args", [
    (["host", "123", "service", "job"], ("host", 123, "service", "job", None, None, None, None)),
    (["host", "123", "service", "ADDRESS", "street", "street_nr", "city", "regex"],
     ("host", 123, "service", "ADDRESS", "street", "street_nr", "city", "regex")),
])
def test_ac_check_uniserv_parse_arguments(check_uniserv, args, expected_args):
    assert check_uniserv.parse_arguments(args) == expected_args
