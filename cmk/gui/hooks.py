#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import functools
import sys
import traceback
import typing
from collections.abc import Callable
from typing import Any, Literal, NamedTuple

from cmk.ccc.exceptions import MKGeneralException

from cmk import trace

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

ClearEvents = list[ClearEvent] | ClearEvent

R = typing.TypeVar("R")
P = typing.ParamSpec("P")
F = typing.TypeVar("F")

CacheWrapperArgs = typing.ParamSpec("CacheWrapperArgs")


def scoped_memoize(
    clear_events: ClearEvents,
    cache_impl: Callable[CacheWrapperArgs, Callable[[Callable[P, R]], Callable[P, R]]],
    cache_impl_args: CacheWrapperArgs.args,
    cache_impl_kwargs: CacheWrapperArgs.kwargs,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """A scoped memoization decorator.

    This caches the decorated function with a supplied implementation. The cache will be
    explicitly cleared whenever one of the supplied events in `clear_events` is triggered.

    For this to work, the return-value of the cache implementation needs to have a `cache_clear`
    method.

    Args:
        clear_events:
            A list of hook events, which shall trigger a clearing of the cache.

        cache_impl:
            The actual cache implementation. Is a function which returns a caching decorator.

        cache_impl_args:
            The var-args to be passed to the cache implementation.

        cache_impl_kwargs:
            The keyword arguments to be passed to the cache implementation.

    Returns:
        A wrapped function which clears the cache according to `clear_events`.

    Raises:
        ValueError - When no or unknown clear events are supplied.

    """
    if isinstance(clear_events, str):
        clear_events = [clear_events]
    if not clear_events:
        raise ValueError(f"No clear-events specified. Use one of: {ClearEvent!r}")

    def _decorator(func: Callable[P, R]) -> Callable[P, R]:
        cached_func = cache_impl(*cache_impl_args, **cache_impl_kwargs)(func)
        for clear_event in clear_events:
            # Tried to generically type this such that parameters and added methods are checked,
            # but this is not easily possible right now. lru_cache also has an incompatible
            # type then.
            # See: https://github.com/python/mypy/issues/5107
            register_builtin(clear_event, cached_func.cache_clear)  # type: ignore[attr-defined]
        return cached_func

    return _decorator


def request_memoize(
    maxsize: int | None = 128, typed: bool = False
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """A cache decorator which only has a scope for one request.

    This one uses `functools.lru_cache`, as the caching-scope can only be in one process anyway.

    Args:
        maxsize:
            See `functools.lru_cache`

        typed:
            See `functools.lru_cache`

    Returns:
        A `_scoped_memoize` decorator which clears on every request-end and request-context-exit.

    """
    return scoped_memoize(
        clear_events=["request-end", "request-context-exit"],
        cache_impl=functools.lru_cache,  # type: ignore[return-value]  # too specialized _lru_cache[_P, _R] ...
        cache_impl_args=(),
        cache_impl_kwargs={"maxsize": maxsize, "typed": typed},
    )
