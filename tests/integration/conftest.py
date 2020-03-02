import pytest  # type: ignore[import]
from testlib.site import get_site_factory
from testlib.utils import current_base_branch_name


# Session fixtures must be in conftest.py to work properly
@pytest.fixture(scope="session", autouse=True)
def site(request):
    sf = get_site_factory(prefix="int_", update_from_git=True, install_test_python_modules=True)
    site_obj = sf.get_existing_site(current_base_branch_name())
    yield site_obj
    print("")
    print("Cleanup site processes after test execution...")
    site_obj.stop()
