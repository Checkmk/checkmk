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

from cmk.utils.exceptions import MKGeneralException


class Hook(NamedTuple):
    handler: Callable
    is_builtin: bool


hooks: dict[str, list[Hook]] = {}


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    # Cleanup all plugin hooks. They need to be renewed by load_plugins()
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


def register_from_plugin(name: str, func: Callable) -> None:
    register(name, func, is_builtin=False)


# Kept public for compatibility with pre 1.6 plugins (is_builtin needs to be optional for pre 1.6)
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
    n = 0
    for hook in hooks.get(name, []):
        n += 1
        try:
            hook.handler(*args)
        except Exception as e:
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


# NOTE
# We can't make a type alias like Foo = Callable[P, R] right now, because of a bug in mypy. We
# therefore need to duplicate the Callable[P, R] part in every site of use. It seems to work, but
# the declaration itself raises an error.
# For more detailed information see: https://github.com/python/mypy/issues/11855


def _scoped_memoize(
    clear_events: ClearEvents,
    maxsize: int | None = 128,
    typed: bool = False,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """A scoped memoization decorator.

    This caches the decorated function with a `functools.lru_cache`, however the cache will be
    explicitly cleared whenever a

    Args:
        clear_events:
            A list of hook events, which shall trigger a clearing of the cache.

        maxsize:
            As documented in @functools.lru_cache

        typed:
            As documented in @functools.lru_cache

    Returns:
        A wrapped function which caches through `functools.lru_cache`, and clears the cache
        according to `clear_events`.

    Raises:
        ValueError - When no or unknown clear events are supplied.

    """
    if isinstance(clear_events, str):
        clear_events = [clear_events]
    if not clear_events:
        raise ValueError(f"No clear-events specified. Use one of: {ClearEvent!r}")

    def _decorator(func: Callable[P, R]) -> Callable[P, R]:
        cached_func = functools.lru_cache(maxsize=maxsize, typed=typed)(func)
        for clear_event in clear_events:
            register_builtin(clear_event, cached_func.cache_clear)  # hooks.register_builtin
        # TODO: mypy does more complex type overloads depending on arity
        return typing.cast(Callable[P, R], cached_func)

    return _decorator


def request_memoize(
    maxsize: int | None = 128, typed: bool = False
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """A cache decorator which only has a scope for one request.

    Args:
        maxsize:
            See `functools.lru_cache`

        typed:
            See `functools.lru_cache`

    Returns:
        A `_scoped_memoize` decorator which clears on every request-start.

    """
    return _scoped_memoize(
        clear_events=["request-end", "request-context-exit"], maxsize=maxsize, typed=typed
    )
