import collections

EXECUTE_IN_SITE, EXECUTE_IN_VENV = True, False

test_types = collections.OrderedDict([
    ("unit",        EXECUTE_IN_VENV),
    ("pylint",      EXECUTE_IN_VENV),
    ("docker",      EXECUTE_IN_VENV),
    ("integration", EXECUTE_IN_SITE),
    ("gui_crawl",   EXECUTE_IN_SITE),
    ("packaging",   EXECUTE_IN_VENV),
])


def pytest_addoption(parser):
    """Register the -T option to pytest"""
    parser.addoption("-T", action="store", metavar="TYPE", default=None,
        help="Run tests of the given TYPE. Available types are: %s" %
                                           ", ".join(test_types.keys()))
