import pytest

pytestmark = pytest.mark.unit

# Unit tests should not be executed in site.
# -> Disabled site fixture for them
@pytest.fixture(scope="session")
def site(request):
    pass
