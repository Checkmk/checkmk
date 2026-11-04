#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Raise from each Python callback of the netsnmp binding while it processes a request

The binding calls Python code while it processes a request (Varbind.__init__,
Varbind.__setattr__ and the VarList sequence methods). A Python signal handler, like
the fetcher timeout, can only run in these callbacks, so an exception can only become
pending there.

For each operation, the helper first counts the callbacks of an undisturbed request.
Then it repeats the request once per callback and raises in exactly that callback.
This covers every point at which a signal handler could raise, independent of timing.

Usage: helper_netsnmp_raising_callback.py HOST:PORT
Prints a JSON object, one entry per operation, with the number of callbacks and the
results that were not the injected exception. A crash of the binding kills the process.
"""

import json
import sys
from collections.abc import Callable
from typing import Any

import netsnmp  # type: ignore[import-not-found,unused-ignore]


class RaisedInCallback(Exception):
    pass


class _Injector:
    def __init__(self) -> None:
        self.active = False
        self.calls = 0
        self.raise_at: int | None = None

    def start(self, raise_at: int | None) -> None:
        self.active = True
        self.calls = 0
        self.raise_at = raise_at

    def stop(self) -> None:
        self.active = False

    def wrap(self, cls: type, name: str) -> None:
        original = getattr(cls, name)

        def wrapper(*args: object, **kwargs: object) -> object:
            if self.active:
                self.calls += 1
                if self.calls == self.raise_at:
                    raise RaisedInCallback(f"{cls.__name__}.{name}")
            return original(*args, **kwargs)

        setattr(cls, name, wrapper)


_INJECTOR = _Injector()
for _cls, _names in (
    (netsnmp.Varbind, ("__init__", "__setattr__")),
    (
        netsnmp.VarList,
        ("__len__", "__getitem__", "__setitem__", "__delitem__", "__iter__"),
    ),
):
    for _name in _names:
        _INJECTOR.wrap(_cls, _name)


def _varlist(*varbinds: tuple[object, ...]) -> Any:
    return netsnmp.VarList(*(netsnmp.Varbind(*v) for v in varbinds))


# The request VarList is built outside of the injection, so that every injected
# exception is raised in a callback made by the binding.
_OPERATIONS: dict[str, tuple[Callable[[], Any], Callable[[Any, Any], object]]] = {
    "get": (
        lambda: _varlist((".1.3.6.1.2.1.1.1.0",), (".1.3.6.1.2.1.1.5.0",)),
        lambda session, varlist: session.get(varlist),
    ),
    "getnext": (
        lambda: _varlist((".1.3.6.1.2.1.1.1",), (".1.3.6.1.2.1.1.5",)),
        lambda session, varlist: session.getnext(varlist),
    ),
    "getbulk": (
        lambda: _varlist((".1.3.6.1.2.1.1",)),
        lambda session, varlist: session.getbulk(0, 5, varlist),
    ),
    "walk": (
        lambda: _varlist((".1.3.6.1.2.1.1",)),
        lambda session, varlist: session.walk(varlist),
    ),
    "set": (
        lambda: _varlist((".1.3.6.1.2.1.1.4", "0", b"contact", "OCTETSTR")),
        lambda session, varlist: session.set(varlist),
    ),
}


def _run(
    build: Callable[[], Any], call: Callable[[Any, Any], object], session: Any, raise_at: int | None
) -> str:
    varlist = build()
    _INJECTOR.start(raise_at)
    try:
        call(session, varlist)
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    finally:
        _INJECTOR.stop()
    return "no exception"


def main(host: str) -> None:
    netsnmp.verbose = 0
    session = netsnmp.Session(
        DestHost=host, Version=2, Community="public", Timeout=1000000, Retries=0
    )
    report: dict[str, dict[str, object]] = {}
    for name, (build, call) in _OPERATIONS.items():
        undisturbed = _run(build, call, session, None)
        callbacks = _INJECTOR.calls
        unexpected = {} if undisturbed == "no exception" else {"undisturbed": undisturbed}
        for raise_at in range(1, callbacks + 1):
            result = _run(build, call, session, raise_at)
            if not result.startswith(f"{RaisedInCallback.__name__}: "):
                unexpected[str(raise_at)] = result
        report[name] = {"callbacks": callbacks, "unexpected": unexpected}
    sys.stdout.write(json.dumps(report, sort_keys=True) + "\n")


main(sys.argv[1])
