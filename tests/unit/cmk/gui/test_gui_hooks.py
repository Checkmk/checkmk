#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import threading
from collections.abc import Generator

import pytest
from pytest_mock import MockerFixture

from tests.unit.cmk.web_test_app import WebTestAppForCMK

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui import hooks
from cmk.gui.config import Config
from cmk.gui.pages import Page, page_registry, PageEndpoint


@pytest.fixture()
def reset_hooks() -> Generator[None, None, None]:
    old_hooks = hooks.hooks
    try:
        hooks.hooks = {}
        hooks.register_thread_cache_cleanup()
        yield
    finally:
        hooks.hooks = old_hooks


@pytest.mark.usefixtures("patch_theme", "reset_hooks")
def test_flask_request_memoize(wsgi_app: WebTestAppForCMK) -> None:
    @hooks.request_memoize()
    def cached_function():
        return datetime.datetime.now()

    assert len(hooks.hooks) > 0

    prev = cached_function()

    # Only Checkmk and REST API Blueprint requests trigger the cache eviction.
    resp = wsgi_app.get("/")
    assert resp.status_code == 404

    assert prev == cached_function()

    # After another request, the cache is evicted.
    resp = wsgi_app.get("/NO_SITE/check_mk/login.py")
    assert resp.status_code == 200
    assert prev != cached_function()


@pytest.mark.usefixtures("patch_theme", "reset_hooks")
def test_request_memoize() -> None:
    @hooks.request_memoize()
    def blah(a=[]):
        a.append(1)
        return a

    assert blah() == [1]
    assert blah() == [1]

    hooks.call("request-end")

    assert blah() == [1, 1]


@pytest.mark.usefixtures("patch_theme", "reset_hooks")
def test_request_memoize_request_integration(
    logged_in_wsgi_app: WebTestAppForCMK, mocker: MockerFixture
) -> None:
    mock = mocker.MagicMock()

    @hooks.request_memoize()
    def memoized():
        return mock()

    class PageClass(Page):
        def page(self, config: Config) -> None:
            mock.return_value = 1
            assert memoized() == 1

            # Test that it gives the memoized value instead of the new mock value
            mock.return_value = 2
            assert memoized() == 1

    page_registry.register(PageEndpoint("my_page", PageClass))

    # Try a first request. Memoization within this request is tested in page() above.
    logged_in_wsgi_app.get("/NO_SITE/check_mk/my_page.py", status=200)

    # After the request has ended we get the new value
    mock.return_value = 2
    assert memoized() == 2
    # But there is no reset triggered outside of the request. We do it manually here.
    hooks.call("request-end")

    # And now try a second request
    mock.return_value = 1
    logged_in_wsgi_app.get("/NO_SITE/check_mk/my_page.py", status=200)

    page_registry.unregister("my_page")


@pytest.mark.usefixtures("patch_theme", "reset_hooks")
def test_request_memoize_unregister() -> None:
    # Make sure request-start hooks are still called, after plug-in hooks are
    # unregistered. In previous versions unregister_plugin_hooks also
    # unregistered hooks used by memoize.

    @hooks.request_memoize()
    def blah(a: list[int] = []) -> list[int]:
        a.append(1)
        return a

    assert blah() == [1]
    assert blah() == [1]

    hooks.call("request-end")

    assert blah() == [1, 1]

    hooks.unregister_plugin_hooks()
    hooks.call("request-end")

    assert blah() == [1, 1, 1]
    assert blah() == [1, 1, 1]


@pytest.mark.usefixtures("reset_hooks")
@pytest.mark.parametrize("setup_cache_in_main_thread", [True, False])
def test_threaded_memoize(
    logged_in_wsgi_app: WebTestAppForCMK, setup_cache_in_main_thread: bool
) -> None:
    @hooks.request_memoize()
    def cached_function(x: int) -> int:
        return x * x

    class PageClass(Page):
        def page(self, config: Config) -> None:
            def worker(i: int) -> None:
                cached_function(i)
                cached_function(i)
                result = cached_function(i)
                cache_info = cached_function.cache_info()  # type: ignore[attr-defined]
                assert cache_info.hits == 2
                assert cache_info.misses == 1
                assert result == i * i

            if setup_cache_in_main_thread:
                # Call function, populate cache, test cache info
                for i in range(10, 20):
                    cached_function(i)
                assert cached_function.cache_info().misses == 10  # type: ignore[attr-defined]

            # Test if worker threads all have their own cache
            threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Test if the main cache is still in the same state after the threads have finished
            if setup_cache_in_main_thread:
                assert cached_function.cache_info().misses == 10  # type: ignore[attr-defined]
            else:
                assert cached_function.cache_info() is None  # type: ignore[attr-defined]

    page_registry.register(PageEndpoint("my_page", PageClass))

    logged_in_wsgi_app.get("/NO_SITE/check_mk/my_page.py", status=200)
    # Note: Even after the get request from the line above, no request end has been called yet
    # Check both event types
    for clear_event in ["request-end", "request-context-exit"]:
        # Note: This only clears the main thread cache. caches are cleared on termination
        cached_function(42)
        hooks.call(clear_event)
        assert cached_function.cache_info() is None  # type: ignore[attr-defined]

    page_registry.unregister("my_page")


@pytest.mark.usefixtures("reset_hooks")
def test_cache_clear_of_function() -> None:
    @hooks.request_memoize()
    def cached_function(x: int) -> int:
        return x * x

    @hooks.request_memoize()
    def other_cached_function(x: int) -> int:
        return x * x

    cached_function(42)
    cached_function(42)
    other_cached_function(42)
    assert cached_function.cache_info().hits == 1  # type: ignore[attr-defined]
    assert cached_function.cache_info().misses == 1  # type: ignore[attr-defined]
    cached_function.cache_clear()  # type: ignore[attr-defined]
    assert cached_function.cache_info() is None  # type: ignore[attr-defined]

    assert other_cached_function.cache_info().misses == 1  # type: ignore[attr-defined]
    other_cached_function.cache_clear()  # type: ignore[attr-defined]
    assert cached_function.cache_info() is None  # type: ignore[attr-defined]


@pytest.mark.usefixtures("reset_hooks")
def test_cache_clear_all() -> None:
    @hooks.request_memoize()
    def cached_function(x: int) -> int:
        return x * x

    @hooks.request_memoize()
    def other_cached_function(x: int) -> int:
        return x * x

    cached_function(42)
    cached_function(42)
    other_cached_function(42)

    hooks._thread_cache.cache_clear_all()
    assert cached_function.cache_info() is None  # type: ignore[attr-defined]
    assert other_cached_function.cache_info() is None  # type: ignore[attr-defined]


@pytest.mark.usefixtures("reset_hooks")
def test_hook_registration() -> None:
    # Thread caching already registered two hooks
    assert len(hooks.hooks) == 2

    # pre 1.6 API
    hooks.register("bla", lambda: True)
    assert hooks.get("bla")[0].is_builtin is False

    hooks.register_builtin("blub", lambda: True)
    hooks.register_from_plugin("blub", lambda: False)
    assert hooks.get("blub")[0].is_builtin is True
    assert hooks.get("blub")[1].is_builtin is False

    assert hooks.registered("bla") is True
    assert hooks.registered("blub") is True
    assert hooks.registered("bli") is False

    assert len(hooks.get("bla")) == 1
    assert len(hooks.get("blub")) == 2
    assert len(hooks.get("bli")) == 0


@pytest.mark.usefixtures("reset_hooks")
def test_call(mocker: MockerFixture) -> None:
    hook1_mock = mocker.Mock()
    hook2_mock = mocker.Mock()
    hooks.register("bla", hook1_mock)
    hooks.register("blub", hook2_mock)

    hooks.call("bla")
    hook1_mock.assert_called_once()
    hook2_mock.assert_not_called()

    hooks.call("blub")
    hook1_mock.assert_called_once()
    hook2_mock.assert_called_once()


@pytest.mark.usefixtures("reset_hooks")
def test_call_exception_handling_for_plugin_register(mocker: MockerFixture) -> None:
    hooks.register_from_plugin("bli", lambda: 1.0 / 0.0)
    hook3_mock = mocker.Mock()
    hooks.register("bli", hook3_mock)
    with pytest.raises(MKGeneralException, match="float division by zero"):
        hooks.call("bli")
    hook3_mock.assert_not_called()


@pytest.mark.usefixtures("reset_hooks")
def test_call_exception_handling_for_builtin_register(mocker: MockerFixture) -> None:
    hooks.register_builtin("bli", lambda: 1.0 / 0.0)
    hook3_mock = mocker.Mock()
    hooks.register("bli", hook3_mock)
    with pytest.raises(ZeroDivisionError, match="float division by zero"):
        hooks.call("bli")
    hook3_mock.assert_not_called()


@pytest.mark.usefixtures("reset_hooks")
def test_builtin_vs_plugin_hooks() -> None:
    hooks.register_builtin("bla", lambda: True)
    assert hooks.registered("bla") is True

    hooks.register_from_plugin("blub", lambda: True)
    assert hooks.registered("blub") is True

    hooks.load_plugins()

    assert hooks.registered("bla") is True
    assert hooks.registered("blub") is False
