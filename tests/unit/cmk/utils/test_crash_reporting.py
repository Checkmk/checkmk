# pylint: disable=redefined-outer-name
import copy
import pytest  # type: ignore

import cmk.utils.paths
from cmk.utils.crash_reporting import ABCCrashReport, _format_var_for_export


class UnitTestCrashReport(ABCCrashReport):
    @classmethod
    def type(cls):
        return "test"

    def ident(self):
        return ("m@y", "ident")


@pytest.fixture()
def crash():
    try:
        raise ValueError("XYZ")
    except ValueError:
        return UnitTestCrashReport.from_exception()


def test_crash_report_type(crash):
    assert crash.type() == "test"


def test_crash_report_ident(crash):
    assert crash.ident() == ("m@y", "ident")


def test_crash_report_ident_to_text(crash):
    assert crash.ident_to_text() == "m~y@ident"


def test_crash_report_crash_dir(crash):
    assert crash.crash_dir() == cmk.utils.paths.crash_dir.joinpath(crash.type(),
                                                                   crash.ident_to_text())


def test_crash_report_local_crash_report_url(crash):
    assert crash.local_crash_report_url() == "crash.py?component=test&ident=m%7Ey%40ident"


def test_format_var_for_export_strip_nested_dict():
    orig_var = {
        "a": {
            "b": {
                "c": {
                    "d": {},
                },
            },
        },
    }

    var = copy.deepcopy(orig_var)
    formated = _format_var_for_export(var)

    # Stripped?
    assert formated["a"]["b"]["c"]["d"] == "Max recursion depth reached"

    # Not modified original data
    assert orig_var == var


def test_format_var_for_export_strip_large_data():
    orig_var = {
        "a": {
            "y": ("a" * 1024 * 1024) + "a"
        },
    }

    var = copy.deepcopy(orig_var)
    formated = _format_var_for_export(var)

    # Stripped?
    assert formated["a"]["y"].endswith("(1 bytes stripped)")

    # Not modified original data
    assert orig_var == var


def test_format_var_for_export_strip_nested_dict_with_list():
    orig_var = {
        "a": {
            "b": {
                "c": [{}],
            },
        },
    }

    var = copy.deepcopy(orig_var)
    formated = _format_var_for_export(var)

    # Stripped?
    assert formated["a"]["b"]["c"][0] == "Max recursion depth reached"

    # Not modified original data
    assert orig_var == var
