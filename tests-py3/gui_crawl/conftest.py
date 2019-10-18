import pytest


# Should not be executed in site
@pytest.fixture(scope="session")
def site(request):
    pass
