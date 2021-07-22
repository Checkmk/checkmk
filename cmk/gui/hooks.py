#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import functools

import sys
import traceback
from typing import Any, Callable, Dict, List, NamedTuple, Union, Literal

from cmk.gui.globals import config
import cmk.gui.i18n
from cmk.gui.i18n import _
from cmk.gui.globals import html

Hook = NamedTuple("Hook", [
    ("handler", Callable),
    ("is_builtin", bool),
])

hooks: Dict[str, List[Hook]] = {}

# Datastructures and functions needed before plugins can be loaded
loaded_with_language: Union[bool, None, str] = False


# Load all login plugins
def load_plugins(force: bool) -> None:
    global loaded_with_language
    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        return

    # Cleanup all plugin hooks. They need to be renewed by load_plugins()
    # of the other modules
    unregister_plugin_hooks()

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = cmk.gui.i18n.get_current_language()


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


def get(name: str) -> List[Hook]:
    return hooks.get(name, [])


def registered(name: str) -> bool:
    """ Returns True if at least one function is registered for the given hook """
    return hooks.get(name, []) != []


def call(name: str, *args: Any) -> None:
    n = 0
    for hook in hooks.get(name, []):
        n += 1
        try:
            hook.handler(*args)
        except Exception as e:
            if config.debug:
                t, v, tb = sys.exc_info()
                msg = "".join(traceback.format_exception(t, v, tb, None))
                html.show_error("<h1>" + _("Error executing hook") + " %s #%d: %s</h1>"
                                "<pre>%s</pre>" % (name, n, e, msg))
            raise


ClearEvent = Literal[
    'activate-changes',
    'pre-activate-changes',
    'all-hosts-changed',
    'contactgroups-saved',
    'hosts-changed',
    'ldap-sync-finished',
    'request-start',
    'request-end',
    'roles-saved',
    'users-saved',
]  # yapf: disable

ClearEvents = Union[List[ClearEvent], ClearEvent]


def _scoped_memoize(
    clear_events: ClearEvents,
    maxsize: int = 128,
    typed: bool = False,
):
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

    def _decorator(func):
        cached_func = functools.lru_cache(maxsize=maxsize, typed=typed)(func)
        for clear_event in clear_events:
            register(clear_event, cached_func.cache_clear)  # hooks.register
        return cached_func

    return _decorator


def request_memoize(maxsize: int = 128, typed: bool = False):
    """A cache decorator which only has a scope for one request.

    Args:
        maxsize:
            See `functools.lru_cache`

        typed:
            See `functools.lru_cache`

    Returns:
        A `_scoped_memoize` decorator which clears on every request-start.

    """
    return _scoped_memoize(clear_events=['request-end'], maxsize=maxsize, typed=typed)
