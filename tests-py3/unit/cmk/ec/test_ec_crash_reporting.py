from cmk.utils.crash_reporting import crash_report_registry
from cmk.ec.crash_reporting import ECCrashReport, CrashReportStore


def test_ec_crash_report_registry():
    assert crash_report_registry["ec"] == ECCrashReport


def test_ec_crash_report_from_exception():
    try:
        raise ValueError("DING")
    except Exception:
        crash = ECCrashReport.from_exception()
        CrashReportStore().save(crash)

    assert crash.type() == "ec"
    assert crash.crash_info["exc_value"] == "DING"
