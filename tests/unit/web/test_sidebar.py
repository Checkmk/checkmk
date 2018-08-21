import pytest

import cmk.gui.sidebar as sidebar
import cmk.gui.config as config
import cmk.gui.pages
import cmk.store as store
from cmk.gui.globals import html


@pytest.fixture(scope="module", autouse=True)
def gui_config():
    config._initialize_with_default_config()


# TODO: Can be removed once all snapins have been refactored
# to class based snapins
@pytest.fixture(scope="module", autouse=True)
def load_plugins():
    sidebar.load_plugins(True)


@pytest.fixture(scope="function", autouse=True)
def user(monkeypatch):
    monkeypatch.setattr(config.user, "confdir", "")
    monkeypatch.setattr(config.user, "may", lambda x: True)


def test_load_default_config(monkeypatch):
    # TODO: Drop this once load_user_config uses
    # config.user.load_file(...). Then patch this method
    monkeypatch.setattr(store, "load_data_from_file",
        lambda x: None)

    cfg = sidebar.load_user_config()
    assert isinstance(cfg, dict)
    assert isinstance(cfg["snapins"], list)
    assert cfg["fold"] == False
    assert cfg["snapins"] == [
        ('tactical_overview', 'open'),
        ('search',            'open'),
        ('views',             'open'),
        ('reports',           'closed'),
        ('bookmarks',         'open'),
        ('admin',             'open'),
        ('master_control',    'closed')
    ]


def test_load_legacy_list_user_config(monkeypatch):
    monkeypatch.setattr(store, "load_data_from_file",
        lambda x: [("tactical_overview", "open"),
                   ("views", "closed")])

    cfg = sidebar.load_user_config()
    assert cfg["fold"] == False
    assert cfg["snapins"] == [
        ('tactical_overview', 'open'),
        ('views', 'closed'),
    ]


def test_load_legacy_off_user_config(monkeypatch):
    monkeypatch.setattr(store, "load_data_from_file",
        lambda x: [("search", "off"),
                   ("views", "closed")])

    cfg = sidebar.load_user_config()
    assert cfg["fold"] == False
    assert cfg["snapins"] == [
        ('views', 'closed'),
    ]


def test_load_skip_not_existing(monkeypatch):
    monkeypatch.setattr(store, "load_data_from_file",
        lambda x: [("bla", "closed"), ("views", "closed")])

    cfg = sidebar.load_user_config()
    assert cfg["fold"] == False
    assert cfg["snapins"] == [
        ('views', 'closed'),
    ]


def test_load_skip_not_permitted(monkeypatch):
    monkeypatch.setattr(store, "load_data_from_file",
        lambda x: [("tactical_overview", "closed"), ("views", "closed")])
    monkeypatch.setattr(config.user, "may", lambda x: x != "sidesnap.tactical_overview")

    cfg = sidebar.load_user_config()
    assert cfg["fold"] == False
    assert cfg["snapins"] == [
        ('views', 'closed'),
    ]


def test_load_user_config(monkeypatch):
    monkeypatch.setattr(store, "load_data_from_file", lambda x: {
        "fold": True,
        "snapins": [
            ("search", "closed"),
            ("views", "open"),
        ]
    })

    cfg = sidebar.load_user_config()
    assert cfg["fold"] == True
    assert cfg["snapins"] == [
        ('search', 'closed'),
        ('views', 'open'),
    ]


def test_save_user_config_denied(mocker, monkeypatch):
    monkeypatch.setattr(config.user, "may", lambda x: x != "general.configure_sidebar")
    save_user_file_mock = mocker.patch.object(config.user, "save_file")
    sidebar.save_user_config({})
    save_user_file_mock.assert_not_called()


def test_save_user_config_allowed(mocker, monkeypatch):
    monkeypatch.setattr(config.user, "may", lambda x: x == "general.configure_sidebar")
    save_user_file_mock = mocker.patch.object(config.user, "save_file")
    sidebar.save_user_config({})
    save_user_file_mock.assert_called_once_with("sidebar", {})


def test_ajax_fold_page():
    assert cmk.gui.pages.get_page_handler("sidebar_fold") == sidebar.ajax_fold


@pytest.mark.parametrize("origin_state,fold_var,set_state", [
    (False, "yes", True),
    (True, "", False),
])
def test_ajax_fold(mocker, origin_state, fold_var, set_state):
    class MockHtml(object):
        def var(self, varname):
            if varname == "fold":
                return fold_var

    m_load = mocker.patch.object(sidebar, "load_user_config", return_value={"fold": origin_state})
    m_save = mocker.patch.object(sidebar, "save_user_config")
    html.set_current(MockHtml())

    sidebar.ajax_fold()

    m_load.assert_called_once()
    m_save.assert_called_once_with({"fold": set_state})


def test_ajax_openclose_page():
    assert cmk.gui.pages.get_page_handler("sidebar_openclose") == sidebar.ajax_openclose


@pytest.mark.parametrize("origin_state,set_state", [
    ("open",   "closed"),
    ("closed", "open"),
    ("closed", "closed"),
    ("open",   "open"),
])
def test_ajax_openclose_close(mocker, origin_state, set_state):
    class MockHtml(object):
        def var(self, varname):
            if varname == "name":
                return "tactical_overview"
            elif varname == "state":
                return set_state

    m1 = mocker.patch.object(sidebar, "load_user_config", return_value={"snapins": [
        ("tactical_overview", origin_state),
        ("views", "open"),
    ]})
    html.set_current(MockHtml())
    m3 = mocker.patch.object(sidebar, "save_user_config")

    sidebar.ajax_openclose()

    m1.assert_called_once()
    m3.assert_called_once_with({"snapins": [
        ("tactical_overview", set_state),
        ("views", "open"),
    ]})


def test_move_snapin_page():
    assert cmk.gui.pages.get_page_handler("sidebar_move_snapin") == sidebar.move_snapin
