from generictests.crashtest import CrashReportList


def pytest_addoption(parser):
    parser.addoption("--datasetfile", action="store", default="")
    parser.addoption("--crashstates", action="store", default="")


def pytest_generate_tests(metafunc):
    # This is called for every test. Only get/set command line arguments
    # if the argument is specified in the list of test "fixturenames".
    if 'datasetfile' in metafunc.fixturenames and metafunc.config.option.datasetfile is not None:
        metafunc.parametrize('datasetfile', [metafunc.config.option.datasetfile])

    if 'crashdata' in metafunc.fixturenames and metafunc.config.option.crashstates is not None:
        crash_reports = CrashReportList(metafunc.config.option.crashstates)
        metafunc.parametrize('crashdata', crash_reports, ids=[r.crash_id for r in crash_reports])
