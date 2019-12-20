# pylint: disable=redefined-outer-name
import contextlib
import os

import pathlib2
import pytest  # type: ignore
from werkzeug.test import create_environ

import cmk.utils.log
import cmk.utils.paths
import cmk.gui.config as config
import cmk.gui.htmllib as htmllib
from cmk.gui.http import Request, Response
from cmk.gui.globals import AppContext, RequestContext
from cmk.gui.plugins.userdb import htpasswd
from cmk.gui.utils import get_random_string
from cmk.gui.watolib.users import edit_users, delete_users
from testlib.utils import DummyApplication


@pytest.fixture(scope='function')
def register_builtin_html():
    """This fixture registers a global htmllib.html() instance just like the regular GUI"""
    environ = create_environ()
    with AppContext(DummyApplication(environ, None)), \
            RequestContext(htmllib.html(Request(environ), Response(is_secure=False))):
        yield


@pytest.fixture(scope='module')
def module_wide_request_context():
    # This one is kind of an hack because some other test-fixtures touch the user object AFTER the
    # request context has already ended. If we increase our scope this won't matter, but it is of
    # course wrong. These other fixtures have to be fixed.
    environ = create_environ()
    with AppContext(DummyApplication(environ, None)), \
         RequestContext(htmllib.html(Request(environ), Response(is_secure=False))):
        yield


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
    config_dir.mkdir(parents=True)
    monkeypatch.setattr(config, "config_dir", "%s" % config_dir)
    modules.load_all_plugins()


def _mk_user_obj(username, password, automation=False):
    user = {
        username: {
            'attributes': {
                'alias': username,
                'email': 'admin@example.com',
                'password': htpasswd.hash_password(password),
                'notification_method': 'email',
                'roles': ['admin'],
                'serial': 0
            },
            'is_new_user': True,
        }
    }
    if automation:
        user[username]['attributes'].update(automation_secret=password,)
    return user


@contextlib.contextmanager
def _create_and_destroy_user(automation=False):
    contacts_mk = cmk.utils.paths.omd_root + "/etc/check_mk/conf.d/wato/contacts.mk"
    contact_existed = os.path.exists(contacts_mk)
    _touch(cmk.utils.paths.htpasswd_file)
    _touch(cmk.utils.paths.omd_root + '/etc/diskspace.conf')
    _makepath(cmk.utils.paths.var_dir + "/wato/auth")
    _makepath(config.config_dir)
    username = 'test123-' + get_random_string(size=5, from_ascii=ord('a'), to_ascii=ord('z'))
    password = 'Ischbinwischtisch'
    edit_users(_mk_user_obj(username, password, automation=automation))
    yield username, password
    delete_users([username])
    if not contact_existed:
        os.unlink(contacts_mk)


@pytest.fixture(scope='function')
def with_user(register_builtin_html, load_config):
    with _create_and_destroy_user(automation=False) as user:
        yield user


@pytest.fixture(scope='function')
def with_automation_user(register_builtin_html, load_config):
    with _create_and_destroy_user(automation=True) as user:
        yield user


def _makepath(path):
    pathlib2.Path(path).mkdir(parents=True, exist_ok=True)


def _touch(path):
    pathlib2.Path(path).parent.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member
    pathlib2.Path(path).touch()
