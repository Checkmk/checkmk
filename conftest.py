import pytest

# Our enterprise tests are located at enterprise/tests. During tests our enterprise tests are
# found by py.tests because of symlinks at tests/{integration,unit}/enterprise.
# Since https://github.com/pytest-dev/pytest/issues/4174 the conftest.py in tests/conftest.py
# does not apply anymore on the tests that are physically located in enterprise/tests.
# Our workaround to make the skipping work again was to move this function to the top level
# conftest.py file.
def pytest_runtest_setup(item):
    """Skip tests of unwanted types"""
    test_type = item.get_closest_marker("type")
    if test_type is None:
        raise Exception("Test is not TYPE marked: %s" % item)

    if not item.config.getoption("-T"):
        raise SystemExit("Please specify type of tests to be executed (py.test -T TYPE)")

    test_type_name = test_type.args[0]
    if test_type_name != item.config.getoption("-T"):
        pytest.skip("Not testing type %r" % test_type_name)
