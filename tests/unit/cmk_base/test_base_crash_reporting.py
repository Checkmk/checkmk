import tarfile
import StringIO
import base64
import cmk_base.crash_reporting as crash_reporting


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
    try:
        raise ValueError("DINGELING")
    except Exception:
        crash = crash_reporting.CMKBaseCrashReport.from_exception()
        crash.save_to_crash_dir()

    crash2 = crash_reporting.CMKBaseCrashReport({})
    crash2.from_crash_dir("base")

    assert crash.crash_info["exc_type"] == crash2.crash_info["exc_type"]
    assert crash.crash_info["time"] == crash2.crash_info["time"]


def test_cmk_base_crash_report_get_packed():
    try:
        raise ValueError("DINGELING")
    except Exception:
        crash = crash_reporting.CMKBaseCrashReport.from_exception()
        crash.save_to_crash_dir()

    b64tgz = crash.get_packed()
    tgz = base64.b64decode(b64tgz)
    buf = StringIO.StringIO(tgz)
    with tarfile.open(mode="r:gz", fileobj=buf) as tar:
        assert tar.getnames() == ["crash.info"]
