import pytest

import cmk.gui.sidebar as sidebar
import cmk.gui.config as config
import cmk.gui.pages
import cmk.store as store
from cmk.gui.globals import html
from cmk.gui.exceptions import MKUserError


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


def test_user_config_fold_unfold():
    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    assert user_config.folded == False
    user_config.folded = True
    assert user_config.folded == True
    user_config.folded = False
    assert user_config.folded == False


def test_user_config_add_snapin():
    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    del user_config.snapins[:]
    user_config.add_snapin("tactical_overview")
    assert user_config.snapins == [("tactical_overview", "open")]


@pytest.mark.parametrize("move,before,result", [
    ("tactical_overview",  "views", [
        ("admin", "open"),
        ("tactical_overview", "open"),
        ("views", "open"),
    ]),
    ("tactical_overview",  "admin", [
        ("tactical_overview", "open"),
        ("admin", "open"),
        ("views", "open"),
    ]),
    ("not_existing",  "admin", None),
    # TODO: Shouldn't this also be handled?
    #("admin",  "not_existing", [
    #    ("admin", "open"),
    #    ("views", "open"),
    #    ("tactical_overview", "open"),
    #]),
    ("admin",  "", [
        ("views", "open"),
        ("tactical_overview", "open"),
        ("admin", "open"),
    ]),
])
def test_user_config_move_snapin_before(mocker, move, before, result):
    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    del user_config.snapins[:]
    user_config.snapins.extend([
        ("admin", "open"),
        ("views", "open"),
        ("tactical_overview", "open"),
    ])

    if result is None:
        with pytest.raises(MKUserError) as e:
            user_config.move_snapin_before(move, before)
        assert "Snapin being moved is not configured" in "%s" % e
    else:
        user_config.move_snapin_before(move, before)
        assert user_config.snapins == result


def test_load_default_config(monkeypatch):
    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    assert user_config.folded == False
    assert user_config.snapins == [
        ('tactical_overview', 'open'),
        ('search',            'open'),
        ('views',             'open'),
        ('reports',           'closed'),
        ('bookmarks',         'open'),
        ('admin',             'open'),
        ('master_control',    'closed')
    ]


def test_load_legacy_list_user_config(monkeypatch):
    monkeypatch.setattr(sidebar.UserSidebarConfig, "_user_config",
        lambda x: [("tactical_overview", "open"),
                   ("views", "closed")])

    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    assert user_config.folded == False
    assert user_config.snapins == [
        ('tactical_overview', 'open'),
        ('views', 'closed'),
    ]


def test_load_legacy_off_user_config(monkeypatch):
    monkeypatch.setattr(sidebar.UserSidebarConfig, "_user_config",
        lambda x: [("search", "off"),
                   ("views", "closed")])

    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    assert user_config.folded == False
    assert user_config.snapins == [
        ('views', 'closed'),
    ]


def test_load_skip_not_existing(monkeypatch):
    monkeypatch.setattr(sidebar.UserSidebarConfig, "_user_config",
        lambda x: {
            "fold": False,
            "snapins": [("bla", "closed"), ("views", "closed")]
        })

    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    assert user_config.folded == False
    assert user_config.snapins == [
        ('views', 'closed'),
    ]


def test_load_skip_not_permitted(monkeypatch):
    monkeypatch.setattr(sidebar.UserSidebarConfig, "_user_config",
        lambda x: {
            "fold": False,
            "snapins": [("tactical_overview", "closed"), ("views", "closed")]
        })
    monkeypatch.setattr(config.user, "may", lambda x: x != "sidesnap.tactical_overview")

    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    assert user_config.folded == False
    assert user_config.snapins == [
        ('views', 'closed'),
    ]


def test_load_user_config(monkeypatch):
    monkeypatch.setattr(sidebar.UserSidebarConfig, "_user_config", lambda x: {
        "fold": True,
        "snapins": [
            ("search", "closed"),
            ("views", "open"),
        ]
    })

    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    assert user_config.folded == True
    assert user_config.snapins == [
        ('search', 'closed'),
        ('views', 'open'),
    ]


def test_save_user_config_denied(mocker, monkeypatch):
    monkeypatch.setattr(config.user, "may", lambda x: x != "general.configure_sidebar")
    save_user_file_mock = mocker.patch.object(config.user, "save_file")
    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    user_config.save()
    save_user_file_mock.assert_not_called()


def test_save_user_config_allowed(mocker, monkeypatch):
    monkeypatch.setattr(config.user, "may", lambda x: x == "general.configure_sidebar")
    save_user_file_mock = mocker.patch.object(config.user, "save_file")
    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    user_config._config = {}
    user_config.save()
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

    m_config = mocker.patch.object(config.user, "load_file", return_value={
        "fold": origin_state,
        "snapins": [("tactical_overview", "open")],
    })
    m_save = mocker.patch.object(config.user, "save_file")
    html.set_current(MockHtml())

    sidebar.ajax_fold()

    m_config.assert_called_once()
    m_save.assert_called_once_with("sidebar", {
        "fold": set_state,
        "snapins": [("tactical_overview", "open")],
    })


def test_ajax_openclose_page():
    assert cmk.gui.pages.get_page_handler("sidebar_openclose") == sidebar.ajax_openclose


@pytest.mark.parametrize("origin_state,set_state", [
    ("open",   "closed"),
    ("closed", "open"),
    ("closed", "closed"),
    ("open",   "open"),
    ("open",   "off"),
    ("closed", "off"),
])
def test_ajax_openclose_close(mocker, origin_state, set_state):
    class MockHtml(object):
        def var(self, varname):
            if varname == "name":
                return "tactical_overview"
            elif varname == "state":
                return set_state

    m_config = mocker.patch.object(config.user, "load_file", return_value={
        "fold": False,
        "snapins": [
            ("tactical_overview", origin_state),
            ("views", "open"),
        ],
    })
    html.set_current(MockHtml())
    m_save = mocker.patch.object(config.user, "save_file")

    sidebar.ajax_openclose()

    snapins = [
        ("views", "open"),
    ]

    if set_state != "off":
        snapins.insert(0, ("tactical_overview", set_state))

    m_config.assert_called_once()
    m_save.assert_called_once_with("sidebar", {
        "fold": False,
        "snapins": snapins,
    })


def test_move_snapin_page():
    assert cmk.gui.pages.get_page_handler("sidebar_move_snapin") == sidebar.move_snapin


def test_move_snapin_not_permitted(monkeypatch, mocker):
    monkeypatch.setattr(config.user, "may", lambda x: x != "general.configure_sidebar")
    m_load = mocker.patch.object(sidebar.UserSidebarConfig, "_load")
    sidebar.move_snapin()
    m_load.assert_not_called()


@pytest.mark.parametrize("move,before,do_save", [
    ("tactical_overview",  "views", True),
    ("not_existing",  "admin", None),
])
def test_move_snapin(mocker, move, before, do_save):
    class MockHtml(object):
        def var(self, varname):
            if varname == "name":
                return move
            elif varname == "before":
                return before
    html.set_current(MockHtml())

    m_save = mocker.patch.object(sidebar.UserSidebarConfig, "save")

    sidebar.move_snapin()

    if do_save is None:
        m_save.assert_not_called()
    else:
        m_save.assert_called_once()
