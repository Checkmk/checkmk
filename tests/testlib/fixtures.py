# pylint: disable=redefined-outer-name
import pytest  # type: ignore[import]

from testlib.web_session import CMKWebSession
from testlib.event_console import CMKEventConsole


@pytest.fixture(scope="module")
def web(site):
    web = CMKWebSession(site)
    web.login()
    web.set_language("en")
    return web


@pytest.fixture(scope="module")
def ec(site, web):
    return CMKEventConsole(site)
