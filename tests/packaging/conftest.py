import os
import pytest


# Packaging tests should not be executed in site.
# -> Disabled site fixture for them
@pytest.fixture(scope="session")
def site(request):
    pass


# TODO: Better hand over arguments using pytest mechanisms (http://doc.pytest.org/en/latest/example/parametrize.html)
@pytest.fixture(scope="module")
def package_path():
    path = os.environ.get("PACKAGE_PATH")
    if not path:
        raise Exception("PACKAGE_PATH environment variable pointing to the package "
                        "to be tested is missing")
    return path


# TODO: Better hand over arguments using pytest mechanisms (http://doc.pytest.org/en/latest/example/parametrize.html)
@pytest.fixture(scope="module")
def cmk_version():
    version = os.environ.get("VERSION")
    if not version:
        raise Exception("VERSION environment variable, e.g. 2016.12.22, is missing")
    return version
