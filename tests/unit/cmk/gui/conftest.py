# pylint: disable=redefined-outer-name

import pytest  # type: ignore
from werkzeug.test import create_environ
from pathlib2 import Path

import cmk.utils.log
import cmk.utils.paths
import cmk.gui.config as config
import cmk.gui.htmllib as htmllib
from cmk.gui.http import Request, Response
from cmk.gui.globals import html, current_app


# TODO: Better make our application available?
class DummyApplication(object):
    def __init__(self, environ, start_response):
        self._environ = environ
        self._start_response = start_response
        self.g = {}


@pytest.fixture()
def register_builtin_html():
    """This fixture registers a global htmllib.html() instance just like the regular GUI"""
    environ = dict(create_environ(), REQUEST_URI='')
    current_app.set_current(DummyApplication(environ, None))
    html.set_current(htmllib.html(Request(environ), Response(is_secure=False)))
    yield
    html.finalize()
    html.unset_current()


@pytest.fixture()
def load_config(register_builtin_html):
    old_root_log_level = cmk.utils.log.logger.getEffectiveLevel()
    config.initialize()
    yield
    cmk.utils.log.logger.setLevel(old_root_log_level)


@pytest.fixture()
def load_plugins(register_builtin_html, monkeypatch, tmp_path):
    import cmk.gui.modules as modules
    config_dir = tmp_path / "var/check_mk/web"
    config_dir.mkdir(parents=True)  # pylint: disable=no-member
    monkeypatch.setattr(config, "config_dir", "%s" % config_dir)
    modules.load_all_plugins()
