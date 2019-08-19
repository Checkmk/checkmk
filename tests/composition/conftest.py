from __future__ import print_function
import os
import pytest
import testlib


# Disable this. We have a site_factory instead.
@pytest.fixture(scope="session")
def site(request):
    pass


@pytest.fixture(scope="session")
def site_factory():
    try:
        sf = testlib.SiteFactory(version=os.environ.get("VERSION", testlib.CMKVersion.DAILY),
                                 edition=os.environ.get("EDITION", testlib.CMKVersion.CEE),
                                 branch=os.environ.get("BRANCH", testlib.current_branch_name()))
        yield sf
    finally:
        sf.cleanup()
