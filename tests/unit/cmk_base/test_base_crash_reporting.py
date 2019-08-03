import tarfile
import StringIO
import base64
import cmk.utils.crash_reporting
import cmk_base.crash_reporting as crash_reporting


def test_cmk_base_report_registry():
    assert cmk.utils.crash_reporting.crash_report_registry["base"] \
            == crash_reporting.CMKBaseCrashReport


def _check_generic_crash_info(crash):
    assert "details" in crash.crash_info

    for key, ty in {
            "crash_type": str,
            "time": float,
            "os": str,
            "version": str,
            "python_version": str,
            "python_paths": list,
            "exc_type": str,
            "exc_value": unicode,
            "exc_traceback": list,
            "local_vars": str,
    }.items():
        assert key in crash.crash_info
        assert isinstance(crash.crash_info[key], ty), \
                "Key %r has an invalid type %r" % (key, type(crash.crash_info[key]))


def test_cmk_base_crash_report_from_exception():
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


def test_cmk_base_crash_report_save():
    store = crash_reporting.CrashReportStore()
    try:
        raise ValueError("DINGELING")
    except Exception:
        crash = crash_reporting.CMKBaseCrashReport.from_exception()
        store.save(crash)

    crash2 = store.load_from_directory(crash.crash_dir())

    assert crash.crash_info["exc_type"] == crash2.crash_info["exc_type"]
    assert crash.crash_info["time"] == crash2.crash_info["time"]


def test_cmk_base_crash_report_get_packed():
    try:
        raise ValueError("DINGELING")
    except Exception:
        crash = crash_reporting.CMKBaseCrashReport.from_exception()
        crash_reporting.CrashReportStore().save(crash)

    b64tgz = crash.get_packed()
    tgz = base64.b64decode(b64tgz)
    buf = StringIO.StringIO(tgz)
    with tarfile.open(mode="r:gz", fileobj=buf) as tar:
        assert tar.getnames() == ["crash.info"]
