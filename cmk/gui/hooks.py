#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import functools
import sys
import threading
import traceback
import typing
from collections.abc import Callable
from typing import Any, Literal, NamedTuple

from cmk.ccc.exceptions import MKGeneralException

from cmk import trace

# mypy: disable-error-code="no-any-return"

tracer = trace.get_tracer()


class Hook(NamedTuple):
    handler: Callable
    is_builtin: bool


hooks: dict[str, list[Hook]] = {}


def load_plugins() -> None:
    """Plug-in initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    # Cleanup all plug-in hooks. They need to be renewed by load_plugins()
    # of the other modules
    unregister_plugin_hooks()


def unregister_plugin_hooks() -> None:
    old_hooks = hooks.copy()
    for name, registered_hooks in old_hooks.items():
        hooks_left = [h for h in registered_hooks if h.is_builtin]
        if hooks_left:
            hooks[name] = hooks_left
        else:
            del hooks[name]


def register_builtin(name: str, func: Callable) -> None:
    register(name, func, is_builtin=True)


# TODO: Kept for compatibility with pre-1.6 Setup plugins
def register_hook(name: str, func: Callable) -> None:
    register_from_plugin(name, func)


def register_from_plugin(name: str, func: Callable) -> None:
    register(name, func, is_builtin=False)


# Kept public for compatibility with pre 1.6 plug-ins (is_builtin needs to be optional for pre 1.6)
def register(name: str, func: Callable, is_builtin: bool = False) -> None:
    hooks.setdefault(name, []).append(Hook(handler=func, is_builtin=is_builtin))


def unregister(name: str, func: Callable) -> None:
    registered_hooks = hooks.get(name, [])
    for hook in registered_hooks:
        if hook.handler == func:
            registered_hooks.remove(hook)


def get(name: str) -> list[Hook]:
    return hooks.get(name, [])


def registered(name: str) -> bool:
    """Returns True if at least one function is registered for the given hook"""
    return hooks.get(name, []) != []


def call(name: str, *args: Any) -> None:
    if not (registered_hooks := hooks.get(name, [])):
        return

    with tracer.span(f"hook_call[{name}]"):
        for hook in registered_hooks:
            try:
                hook.handler(*args)
            except Exception as e:
                # for builtin hooks do not change exception handling
                if hook.is_builtin:
                    raise
                t, v, tb = sys.exc_info()
                msg = "".join(traceback.format_exception(t, v, tb, None))
                raise MKGeneralException(msg) from e


ClearEvent = Literal[
    "activate-changes",
    "pre-activate-changes",
    "all-hosts-changed",
    "contactgroups-saved",
    "hosts-changed",
    "ldap-sync-finished",
    "request-start",
    "request-end",
    "request-context-enter",
    "request-context-exit",
    "roles-saved",
    "users-saved",
]

P = typing.ParamSpec("P")
R = typing.TypeVar("R")


class ThreadLocalLRUCache:
    def __init__(self) -> None:
        self._local_storage = threading.local()
        self._local_storage.caches = {}

    def _get_cached_func(self, func: Callable[P, R], maxsize: int | None) -> Callable[P, R]:
        if not hasattr(self._local_storage, "caches"):
            self._local_storage.caches = {}
        if func not in self._local_storage.caches:
            self._local_storage.caches[func] = functools.lru_cache(maxsize=maxsize)(func)
        return self._local_storage.caches[func]

    def cache_function(
        self, maxsize: int | None = 128
    ) -> Callable[[Callable[P, R]], Callable[P, R]]:
        """Create a decorator to cache a function with a thread-local LRU cache."""

        def decorator(func: Callable[P, R]) -> Callable[P, R]:
            def wrapper(*args: object, **kwargs: object) -> R:
                cached_func = self._get_cached_func(func, maxsize)
                return cached_func(*args, **kwargs)  # type: ignore[arg-type]

            return wrapper

        return decorator

    def cache_clear_all(self) -> None:
        """Clear all caches in the current thread"""
        if hasattr(self._local_storage, "caches"):
            self._local_storage.caches.clear()

    def cache_clear(self, func: Callable[P, R]) -> None:
        """Clear the cache of a function."""
        if hasattr(self._local_storage, "caches"):
            self._local_storage.caches.pop(func, None)

    def cache_info(self, func: Callable[P, R]) -> object | None:
        """Shows the cache statistics of a function"""
        if hasattr(self._local_storage, "caches") and func in self._local_storage.caches:
            return self._local_storage.caches[func].cache_info()
        return None


_thread_cache = ThreadLocalLRUCache()


def register_thread_cache_cleanup() -> None:
    for clear_event in ["request-end", "request-context-exit"]:
        # Note: This only clears the main thread cache. other caches are cleared on termination
        register_builtin(clear_event, _thread_cache.cache_clear_all)


def request_memoize(maxsize: int | None = 128) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """A cache decorator which only has a scope for one request.

    This one uses the ThreadLocalLRUCache as the caching-scope, hereby creating a separate
    cache for each thread.

    Args:
        maxsize:
            See `functools.lru_cache`

    Returns:
        A decorator which clears on every request-end and request-context-exit.
        The main thread cache is cleared on every request-end and request-context-exit.
        Worker thread caches are automatically cleared when the thread is terminated.
    """

    def _memoize_decorator(func: Callable[P, R]) -> Callable[P, R]:
        cached_function = _thread_cache.cache_function(maxsize)(func)
        cached_function.cache_clear = lambda: _thread_cache.cache_clear(func)  # type: ignore[attr-defined]
        cached_function.cache_info = lambda: _thread_cache.cache_info(func)  # type: ignore[attr-defined]
        return cached_function

    return _memoize_decorator
