#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

import typing
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, NamedTuple
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from pytest_mock import MockerFixture

import cmk.gui.config as config_module
import cmk.gui.watolib.password_store
import cmk.utils.log
from cmk.automations.results import DeleteHostsResult
from cmk.ccc.hostaddress import HostName
from cmk.ccc.user import UserId
from cmk.ccc.version import Edition
from cmk.gui import hooks, http, main_modules
from cmk.gui.config import active_config, Config
from cmk.gui.script_helpers import session_wsgi_app
from cmk.gui.watolib.hosts_and_folders import folder_tree

from .web_test_app import WebTestAppForCMK


class RemoteAutomation(NamedTuple):
    automation: MagicMock
    responses: Any


def create_flask_app() -> Iterator[Flask]:
    """Initialize a Flask app for testing purposes.

    Register a global htmllib.html() instance, just like in the regular GUI.
    """
    app = session_wsgi_app(debug=False, testing=True)
    with app.test_request_context():
        app.preprocess_request()
        yield app
        app.process_response(http.Response())


def create_wsgi_app(flask_app: Flask) -> Iterator[WebTestAppForCMK]:
    """Yield a Flask test client."""
    flask_app.test_client_class = WebTestAppForCMK
    with flask_app.test_client() as client:
        if isinstance(client, WebTestAppForCMK):
            yield client
        else:
            raise TypeError(
                f"Expected flask client of type: 'WebTestAppForCMK' and not '{type(client)}'!"
            )


def create_aut_user_auth_wsgi_app(
    wsgi_app: WebTestAppForCMK,
    with_automation_user: tuple[UserId, str],
) -> WebTestAppForCMK:
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", f"{username} {secret}"))
    return wsgi_app


def validate_background_job_annotation(
    request: pytest.FixtureRequest, mocker: MockerFixture
) -> None:
    """Unannotated background job call

    Tests must not execute logic in background job processes, which may continue to run
    independently of the test case.

    If your test shall execute a background job, the default is to annotate your test with the
    `inline_background_jobs` fixture above. It makes the background job run synchronously so that
    the test code waits for the job to complete. In many cases this is the desired behavior and
    makes it easier to deal with the jobs in the tests.

    However, in some cases you actually want to have a backrgound job being executed as in the
    production environment. In that case, you need to define a local  klacono-op finamed
    "inline_background_jobs" to override these global fixtures.xture

    This autoload fixture is here to make you aware of the fact that you are calling a background
    job and that you have to decide explicitly which behavior you want to have.
    """
    if (
        "inline_background_jobs" in request.fixturenames
        or "allow_background_jobs" in request.fixturenames
    ):
        return

    mocker.patch(
        "cmk.gui.background_job.job._base.BackgroundJob.start",
        side_effect=RuntimeError(validate_background_job_annotation.__doc__),
    )


def perform_gui_cleanup_after_test(
    mocker: MockerFixture,
) -> Iterator[None]:
    # deactivate_search_index_building_at_requenst_end.
    mocker.patch("cmk.gui.search.engines.setup.updates_requested", return_value=False)
    yield
    # In case some tests use @request_memoize but don't use the request context, we'll emit the
    # clear event after each request.
    hooks.call("request-end")


def perform_load_config() -> Iterator[config_module.Config]:
    old_root_log_level = cmk.utils.log.logger.getEffectiveLevel()
    yield config_module.initialize()
    cmk.utils.log.logger.setLevel(old_root_log_level)


def perform_load_plugins(edition: Edition) -> None:
    main_modules.register(edition)

    if errors := main_modules.get_failed_plugins():
        raise Exception(f"The following errors occured during plug-in loading: {errors}")


@contextmanager
def set_config_context(**kwargs: Any) -> Iterator[None]:  # type: ignore[misc]
    """Patch the config

    This works even in WSGI tests, where the config is (re-)loaded by the app itself,
    through the registered callback.
    """

    def _set_config(config: Config) -> None:
        config._raw_config = {**config._raw_config, **kwargs}
        for key, val in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, val)

    def fake_load_single_global_wato_setting(
        varname: str,
        deflt: typing.Any | None = None,
    ) -> typing.Any:
        return kwargs.get(varname, deflt)

    try:
        config_module.register_post_config_load_hook(_set_config)
        patchable = {k: v for k, v in kwargs.items() if hasattr(active_config, k)}
        if patchable:
            # NOTE: patch.multiple doesn't want to receive an empty kwargs dict and will crash.
            with (
                mock.patch.multiple(active_config, **patchable),
                mock.patch(
                    "cmk.gui.single_global_setting._load_single_global_wato_setting",
                    new=fake_load_single_global_wato_setting,
                ),
            ):
                yield
        elif kwargs:
            with mock.patch(
                "cmk.gui.single_global_setting._load_single_global_wato_setting",
                new=fake_load_single_global_wato_setting,
            ):
                yield
        else:
            yield
    finally:
        config_module._post_config_load_hooks.remove(_set_config)


def inline_background_jobs_patches(mocker: MockerFixture) -> None:
    """Prevent threading.Thread to spin off a new thread

    This will run the code (non-concurrently, blocking) in the main execution path.
    """
    # Thread.start spins of the new thread. We tell it to just run the job instead.
    mocker.patch("threading.Thread.start", new=lambda self: self.run())
    ####
    mocker.patch("multiprocessing.Process.start", new=lambda self: self.run())
    mocker.patch("multiprocessing.context.SpawnProcess.start", new=lambda self: self.run())
    # We stub out everything preventing smooth execution.
    mocker.patch("threading.Thread.join")
    mocker.patch("multiprocessing.Process.join")
    mocker.patch("multiprocessing.context.SpawnProcess.join")
    mocker.patch("multiprocessing.Process.pid", 1234)
    mocker.patch("multiprocessing.context.SpawnProcess.pid", 1234)
    mocker.patch("multiprocessing.Process.exitcode", 0)
    mocker.patch("multiprocessing.context.SpawnProcess.exitcode", 0)

    class SynchronousQueue(list[Any]):
        def put(self, x: Any) -> None:
            self.append(x)

        def get(self) -> Any:
            return self.pop()

        def empty(self) -> bool:
            return not bool(self)

    mocker.patch("multiprocessing.Queue", wraps=SynchronousQueue)
    # ThreadPool creates its own Process internally so we need to mock explictly
    thread_pool_mock = mocker.patch("multiprocessing.pool.ThreadPool")
    thread_pool_mock.return_value.__enter__.return_value.apply_async = (
        lambda func, args=None, kwds=None, callback=(lambda *_args: None): callback(
            func(*(args or ()), **(kwds or {}))
        )
    )
    mocker.patch("sys.exit")
    mocker.patch("cmk.ccc.daemon.daemonize")
    mocker.patch("cmk.ccc.daemon.closefrom")


def suppress_remote_automation_calls_patches(mocker: MockerFixture) -> RemoteAutomation:
    """Stub out calls to the remote automation system
    This is needed because in order for remote automation calls to work, the site needs to be set up
    properly, which can't be done in an unit-test context."""
    remote_automation = mocker.patch("cmk.gui.watolib.automations.do_remote_automation")
    mocker.patch("cmk.gui.watolib.automations.do_remote_automation", new=remote_automation)
    return RemoteAutomation(
        automation=remote_automation,
        responses=None,
    )


def create_test_hosts() -> Iterator[list[HostName]]:
    hostnames = [HostName("heute"), HostName("example.com")]
    root_folder = folder_tree().root_folder()
    root_folder.create_hosts(
        [(hostname, {}, None) for hostname in hostnames], pprint_value=False, use_git=False
    )
    yield hostnames
    root_folder.delete_hosts(
        hostnames,
        automation=lambda *args, **kwargs: DeleteHostsResult(),
        pprint_value=False,
        debug=False,
        use_git=False,
    )


def _fake_detect_icon_path(_: None, icon_name: str = "", prefix: str = "") -> str:
    if icon_name == "link":
        return "themes/facelift/images/icon_link.png"
    if icon_name == "info":
        return "themes/facelift/images/icon_info.svg"
    return "unittest.png"


def patch_theme_context() -> Iterator[None]:
    with (
        patch(
            "cmk.gui.htmllib.html.HTMLGenerator._inject_vue_frontend",
        ),
        patch(
            "cmk.gui.theme.Theme.detect_icon_path",
            new=_fake_detect_icon_path,
        ),
        patch(
            "cmk.gui.theme.Theme.get",
            return_value="modern-dark",
        ),
        patch(
            "cmk.gui.theme.choices.theme_choices",
            return_value=[("modern-dark", "dark ut"), ("facelift", "light ut")],
        ),
    ):
        yield
