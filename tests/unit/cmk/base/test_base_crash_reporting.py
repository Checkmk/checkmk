import six
from pathlib2 import Path

import cmk.utils.crash_reporting
import cmk.base.crash_reporting as crash_reporting
import cmk.base.check_api as check_api
import cmk.base.config as config

from testlib.base import Scenario


def test_base_crash_report_registry():
    assert cmk.utils.crash_reporting.crash_report_registry["base"] \
            == crash_reporting.CMKBaseCrashReport


def _check_generic_crash_info(crash):
    assert "details" in crash.crash_info

    for key, ty in {
            "crash_type": str,
            "time": float,
            "os": str,
            "version": six.text_type,
            "python_version": str,
            "python_paths": list,
            "exc_type": str,
            "exc_value": six.text_type,
            "exc_traceback": list,
            "local_vars": six.text_type,
    }.items():
        assert key in crash.crash_info
        assert isinstance(crash.crash_info[key], ty), \
                "Key %r has an invalid type %r" % (key, type(crash.crash_info[key]))


def test_base_crash_report_from_exception():
    try:
        raise ValueError("DING")
    except Exception:
        crash = crash_reporting.CMKBaseCrashReport.from_exception()

    _check_generic_crash_info(crash)
    assert crash.type() == "base"
    assert isinstance(crash.crash_info["details"]["argv"], list)
    assert isinstance(crash.crash_info["details"]["env"], dict)

    assert crash.crash_info["exc_type"] == "ValueError"
    assert crash.crash_info["exc_value"] == "DING"


def test_base_crash_report_save():
    store = crash_reporting.CrashReportStore()
    try:
        raise ValueError("DINGELING")
    except Exception:
        crash = crash_reporting.CMKBaseCrashReport.from_exception()
        store.save(crash)

    crash2 = store.load_from_directory(crash.crash_dir())

    assert crash.crash_info["exc_type"] == crash2.crash_info["exc_type"]
    assert crash.crash_info["time"] == crash2.crash_info["time"]


def test_check_crash_report_from_exception(monkeypatch):
    Scenario().apply(monkeypatch)
    try:
        raise Exception("DING")
    except Exception:
        crash = crash_reporting.CheckCrashReport.from_exception_and_context(
            hostname="testhost",
            check_plugin_name="uptime",
            item=None,
            is_manual_check=False,
            params=None,
            description=u"Uptime",
            info="X",
            text=u"Output",
        )

    _check_generic_crash_info(crash)

    assert crash.type() == "check"
    assert crash.crash_info["exc_type"] == "Exception"
    assert crash.crash_info["exc_value"] == "DING"

    for key, (ty, value) in {
            "check_output": (unicode, "Output"),
            "host": (str, "testhost"),
            "is_cluster": (bool, False),
            "description": (unicode, "Uptime"),
            "check_type": (str, "uptime"),
            "item": (type(None), None),
            "params": (type(None), None),
            "uses_snmp": (bool, False),
            "inline_snmp": (bool, False),
            "manual_check": (bool, False),
    }.items():
        assert key in crash.crash_info["details"]
        assert isinstance(crash.crash_info["details"][key], ty), \
                "Key %r has wrong type: %r" % (key, type(crash.crash_info["details"][key]))
        assert crash.crash_info["details"][key] == value, "%r has invalid value" % key


def test_check_crash_report_save(monkeypatch):
    Scenario().apply(monkeypatch)
    store = crash_reporting.CrashReportStore()
    try:
        raise Exception("DING")
    except Exception:
        crash = crash_reporting.CheckCrashReport.from_exception_and_context(
            hostname="testhost",
            check_plugin_name="uptime",
            item=None,
            is_manual_check=False,
            params=None,
            description=u"Uptime",
            info="X",
            text=u"Output",
        )
        store.save(crash)

    crash2 = store.load_from_directory(crash.crash_dir())
    assert crash2.crash_info["exc_value"] == "DING"


def test_check_crash_report_read_agent_output(monkeypatch):
    Scenario().apply(monkeypatch)
    config.load_checks(
        check_api.get_check_api_context,
        ["%s/uptime" % cmk.utils.paths.checks_dir,
         "%s/snmp_uptime" % cmk.utils.paths.checks_dir])

    cache_path = Path(cmk.utils.paths.tcp_cache_dir, "testhost")
    cache_path.parent.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member
    with cache_path.open("w", encoding="utf-8") as f:
        f.write(u"<<<abc>>>\nblablub\n")

    try:
        raise Exception("DING")
    except Exception:
        crash = crash_reporting.CheckCrashReport.from_exception_and_context(
            hostname="testhost",
            check_plugin_name="uptime",
            item=None,
            is_manual_check=False,
            params=None,
            description=u"Uptime",
            info="X",
            text=u"Output",
        )

    assert crash.agent_output == u"<<<abc>>>\nblablub\n"
    assert crash.snmp_info is None


def test_check_crash_report_read_snmp_info(monkeypatch):
    Scenario().apply(monkeypatch)
    config.load_checks(
        check_api.get_check_api_context,
        ["%s/uptime" % cmk.utils.paths.checks_dir,
         "%s/snmp_uptime" % cmk.utils.paths.checks_dir])

    cache_path = Path(cmk.utils.paths.data_source_cache_dir, "snmp", "testhost")
    cache_path.parent.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member
    with cache_path.open("w", encoding="utf-8") as f:
        f.write(u"[]\n")

    try:
        raise Exception("DING")
    except Exception:
        crash = crash_reporting.CheckCrashReport.from_exception_and_context(
            hostname="testhost",
            check_plugin_name="snmp_uptime",
            item=None,
            is_manual_check=False,
            params=None,
            description=u"Uptime",
            info="X",
            text=u"Output",
        )

    assert crash.agent_output is None
    assert crash.snmp_info == u"[]\n"
