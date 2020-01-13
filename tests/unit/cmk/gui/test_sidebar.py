import pytest

import cmk.gui.sidebar as sidebar
import cmk.gui.config as config
from cmk.gui.globals import html
from cmk.gui.sidebar import UserSidebarSnapin


@pytest.fixture(scope="module", autouse=True)
def gui_config():
    config._initialize_with_default_config()


# TODO: Can be removed once all snapins have been refactored
# to class based snapins
sidebar._register_custom_snapins = lambda: None
sidebar.load_plugins(True)


@pytest.fixture(scope="function", autouse=True)
def user(module_wide_request_context, monkeypatch):
    # We use the module wide request context because the monkeypatch would roll back the user
    # stuff after the request context has already been ended and thus throwing an error. So we
    # actually need to fix these tests and their user-handling because the natural way to test
    # with a request-context is to have a fresh one for each function call.
    monkeypatch.setattr(config.user, "confdir", "")
    monkeypatch.setattr(config.user, "may", lambda x: True)


def test_user_config_fold_unfold():
    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    assert user_config.folded is False
    user_config.folded = True
    assert user_config.folded is True
    user_config.folded = False
    assert user_config.folded is False


def test_user_config_add_snapin():
    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    del user_config.snapins[:]
    snapin = UserSidebarSnapin.from_snapin_type_id("tactical_overview")
    user_config.add_snapin(snapin)
    assert user_config.snapins == [snapin]


def test_user_config_get_snapin():
    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    del user_config.snapins[:]
    snapin = UserSidebarSnapin.from_snapin_type_id("tactical_overview")
    user_config.add_snapin(snapin)

    assert user_config.get_snapin("tactical_overview") == snapin


def test_user_config_get_not_existing_snapin():
    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    del user_config.snapins[:]

    with pytest.raises(KeyError) as e:
        user_config.get_snapin("tactical_overview")
    msg = "%s" % e
    assert "does not exist" in msg


@pytest.mark.parametrize(
    "move_id,before_id,result",
    [
        ("tactical_overview", "views", [
            UserSidebarSnapin.from_snapin_type_id("admin"),
            UserSidebarSnapin.from_snapin_type_id("tactical_overview"),
            UserSidebarSnapin.from_snapin_type_id("views"),
        ]),
        ("tactical_overview", "admin", [
            UserSidebarSnapin.from_snapin_type_id("tactical_overview"),
            UserSidebarSnapin.from_snapin_type_id("admin"),
            UserSidebarSnapin.from_snapin_type_id("views"),
        ]),
        ("not_existing", "admin", None),
        # TODO: Shouldn't this also be handled?
        #("admin",  "not_existing", [
        #    ("admin", "open"),
        #    ("views", "open"),
        #    ("tactical_overview", "open"),
        #]),
        ("admin", "", [
            UserSidebarSnapin.from_snapin_type_id("views"),
            UserSidebarSnapin.from_snapin_type_id("tactical_overview"),
            UserSidebarSnapin.from_snapin_type_id("admin"),
        ]),
    ])
def test_user_config_move_snapin_before(mocker, move_id, before_id, result):
    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    del user_config.snapins[:]
    user_config.snapins.extend([
        UserSidebarSnapin.from_snapin_type_id("admin"),
        UserSidebarSnapin.from_snapin_type_id("views"),
        UserSidebarSnapin.from_snapin_type_id("tactical_overview"),
    ])

    try:
        move = user_config.get_snapin(move_id)
    except KeyError as e:
        if result is None:
            assert "does not exist" in "%s" % e
            return
        else:
            raise

    try:
        before = user_config.get_snapin(before_id)
    except KeyError:
        before = None

    user_config.move_snapin_before(move, before)
    assert user_config.snapins == result


def test_load_default_config(monkeypatch):
    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    assert user_config.folded is False
    assert user_config.snapins == [
        UserSidebarSnapin.from_snapin_type_id('tactical_overview'),
        UserSidebarSnapin.from_snapin_type_id('search'),
        UserSidebarSnapin.from_snapin_type_id('views'),
        UserSidebarSnapin.from_snapin_type_id('admin'),
        UserSidebarSnapin.from_snapin_type_id('bookmarks'),
        UserSidebarSnapin(sidebar.snapin_registry["master_control"],
                          sidebar.SnapinVisibility.CLOSED),
    ]


def test_load_legacy_list_user_config(monkeypatch):
    monkeypatch.setattr(sidebar.UserSidebarConfig, "_user_config",
                        lambda x: [("tactical_overview", "open"), ("views", "closed")])

    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    assert user_config.folded is False
    assert user_config.snapins == [
        UserSidebarSnapin.from_snapin_type_id('tactical_overview'),
        UserSidebarSnapin(sidebar.snapin_registry["views"], sidebar.SnapinVisibility.CLOSED),
    ]


def test_load_legacy_off_user_config(monkeypatch):
    monkeypatch.setattr(sidebar.UserSidebarConfig, "_user_config", lambda x: [("search", "off"),
                                                                              ("views", "closed")])

    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    assert user_config.folded is False
    assert user_config.snapins == [
        UserSidebarSnapin(sidebar.snapin_registry["views"], sidebar.SnapinVisibility.CLOSED),
    ]


def test_load_skip_not_existing(monkeypatch):
    monkeypatch.setattr(
        sidebar.UserSidebarConfig, "_user_config", lambda x: {
            "fold": False,
            "snapins": [("bla", "closed"), ("views", "closed")]
        })

    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    assert user_config.folded is False
    assert user_config.snapins == [
        UserSidebarSnapin(sidebar.snapin_registry["views"], sidebar.SnapinVisibility.CLOSED),
    ]


def test_load_skip_not_permitted(monkeypatch, register_builtin_html):
    monkeypatch.setattr(
        sidebar.UserSidebarConfig, "_user_config", lambda x: {
            "fold": False,
            "snapins": [("tactical_overview", "closed"), ("views", "closed")]
        })
    monkeypatch.setattr(config.user, "may", lambda x: x != "sidesnap.tactical_overview")

    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    assert user_config.folded is False
    assert user_config.snapins == [
        UserSidebarSnapin(sidebar.snapin_registry["views"], sidebar.SnapinVisibility.CLOSED),
    ]


def test_load_user_config(monkeypatch):
    monkeypatch.setattr(
        sidebar.UserSidebarConfig, "_user_config", lambda x: {
            "fold": True,
            "snapins": [
                ("search", "closed"),
                ("views", "open"),
            ]
        })

    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    assert user_config.folded is True
    assert user_config.snapins == [
        UserSidebarSnapin(sidebar.snapin_registry["search"], sidebar.SnapinVisibility.CLOSED),
        UserSidebarSnapin.from_snapin_type_id('views'),
    ]


def test_save_user_config_denied(mocker, monkeypatch):
    monkeypatch.setattr(config.user, "may", lambda x: x != "general.configure_sidebar")
    save_user_file_mock = mocker.patch.object(config.user, "save_file")
    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    user_config.save()
    save_user_file_mock.assert_not_called()


def test_save_user_config_allowed(register_builtin_html, mocker, monkeypatch):
    monkeypatch.setattr(config.user, "may", lambda x: x == "general.configure_sidebar")
    save_user_file_mock = mocker.patch.object(config.user, "save_file")
    user_config = sidebar.UserSidebarConfig(config.user, config.sidebar)
    user_config._config = {"fold": True, "snapins": []}
    user_config.save()
    save_user_file_mock.assert_called_once_with("sidebar", {"fold": True, "snapins": []})


@pytest.mark.parametrize("origin_state,fold_var,set_state", [
    (False, "yes", True),
    (True, "", False),
])
def test_ajax_fold(module_wide_request_context, mocker, origin_state, fold_var, set_state):
    html.request.set_var("fold", fold_var)
    m_config = mocker.patch.object(config.user,
                                   "load_file",
                                   return_value={
                                       "fold": origin_state,
                                       "snapins": [("tactical_overview", "open")],
                                   })
    m_save = mocker.patch.object(config.user, "save_file")

    sidebar.ajax_fold()

    m_config.assert_called_once()
    m_save.assert_called_once_with("sidebar", {
        "fold": set_state,
        "snapins": [{
            "snapin_type_id": "tactical_overview",
            "visibility": "open",
        }],
    })


@pytest.mark.parametrize("origin_state,set_state", [
    ("open", "closed"),
    ("closed", "open"),
    ("closed", "closed"),
    ("open", "open"),
    ("open", "off"),
    ("closed", "off"),
])
def test_ajax_openclose_close(module_wide_request_context, mocker, origin_state, set_state):
    html.request.set_var("name", "tactical_overview")
    html.request.set_var("state", set_state)
    m_config = mocker.patch.object(config.user,
                                   "load_file",
                                   return_value={
                                       "fold": False,
                                       "snapins": [
                                           ("tactical_overview", origin_state),
                                           ("views", "open"),
                                       ],
                                   })
    m_save = mocker.patch.object(config.user, "save_file")

    sidebar.ajax_openclose()

    snapins = [
        UserSidebarSnapin.from_snapin_type_id("views"),
    ]

    if set_state != "off":
        snapins.insert(
            0,
            UserSidebarSnapin.from_config({
                "snapin_type_id": "tactical_overview",
                "visibility": set_state
            }))

    m_config.assert_called_once()
    m_save.assert_called_once_with("sidebar", {
        "fold": False,
        "snapins": [e.to_config() for e in snapins],
    })


def test_move_snapin_not_permitted(monkeypatch, mocker, module_wide_request_context):
    monkeypatch.setattr(config.user, "may", lambda x: x != "general.configure_sidebar")
    m_load = mocker.patch.object(sidebar.UserSidebarConfig, "_load")
    sidebar.move_snapin()
    m_load.assert_not_called()


@pytest.mark.parametrize("move,before,do_save", [
    ("tactical_overview", "views", True),
    ("not_existing", "admin", None),
])
def test_move_snapin(module_wide_request_context, mocker, move, before, do_save):
    html.request.set_var("name", move)
    html.request.set_var("before", before)
    m_save = mocker.patch.object(sidebar.UserSidebarConfig, "save")

    sidebar.move_snapin()

    if do_save is None:
        m_save.assert_not_called()
    else:
        m_save.assert_called_once()
