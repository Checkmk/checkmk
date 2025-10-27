import base64
import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.testlib.site import Site
from tests.testlib.web_session import CMKWebSession

FAULTY_PAGE = """
from cmk.gui.pages import AjaxPage, page_registry, PageEndpoint

class FooPage(AjaxPage):
    def page(self, _config: object) -> None:
        password = "verysecret"
        some_local_var = [{"foo": {"deep": True, "password": "verysecret", "foo": "notsecret"}}]
        raise ValueError("This is intended, please move on... Really")

page_registry.register(PageEndpoint("foo", FooPage()))
"""


@pytest.fixture(name="faulty_page")
def create_faulty_page(site: Site) -> Iterator[None]:
    site.write_file(Path("local/share/check_mk/web/plugins/pages/foo.py"), FAULTY_PAGE)
    site.omd("restart", "apache")
    try:
        yield
    finally:
        site.delete_file(Path("local/share/check_mk/web/plugins/pages/foo.py"))


def _get_crash_report(site: Site) -> tuple[Path, dict[str, object]] | None:
    for crash_dir in site.crash_reports_dirs():
        crash_file = crash_dir / "crash.info"
        try:
            crash = json.loads(site.read_file(crash_file))
        except Exception:
            # probably not ours, the site will take care of it later
            continue
        if (
            crash.get("exc_type", "") == "ValueError"
            and crash.get("exc_value", "") == "This is intended, please move on... Really"
        ):
            return crash_dir, crash
    return None


@pytest.mark.skip_if_edition("saas")
def test_crash_report(site: Site, faulty_page: None) -> None:
    web = CMKWebSession(site)
    web.login()
    web.get("foo.py?password=get_var_secret")

    crash_dir_and_report = _get_crash_report(site)
    assert crash_dir_and_report is not None
    crash_dir, crash = crash_dir_and_report
    site.delete_dir(crash_dir)

    crash_details = crash["details"]
    assert isinstance(crash_details, dict)
    crash_vars = crash_details["vars"]
    assert isinstance(crash_vars, dict)
    crash_vars = crash_details["vars"]
    assert isinstance(crash_vars, dict)
    assert crash_vars["password"] == "redacted"
    crash_local_vars = crash["local_vars"]
    assert isinstance(crash_local_vars, str)
    assert b"verysecret" not in base64.b64decode(crash_local_vars)
