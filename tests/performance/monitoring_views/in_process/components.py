#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Attribute a page load's time to the parts of Checkmk it passes through.

The rest of this suite argues from the outside: how many queries, how many rows, how many
seconds. That says whether a page is slower, never where the time went, and it leaves the
premise of the whole comparison - that the parts *behind* the Livestatus socket are irrelevant
because both pages reach the same ones - as an argument from reading the code rather than a
measurement.

Running the GUI in the test process makes that measurable. A profile of one page load,
attributed to components rather than to functions, says which parts of the product a page
actually spends its time in, and therefore which ones a performance question about it has to
care about. It also says how much of the measurement is the harness itself, which is the number
that decides whether any of the rest can be believed.
"""

from __future__ import annotations

import cProfile
import pstats
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

#: Path fragments naming a component, most specific first. A frame is attributed to the first
#: one that matches its file, so ``cmk/gui/monitor`` has to be tried before ``cmk/gui``.
_COMPONENTS: Final[Sequence[tuple[str, str]]] = (
    # The harness. Its share is the first thing to read: a fake that costs a large part of the
    # measurement is measuring itself, and every other figure in this suite is then suspect.
    ("/tests/performance/monitoring_views/", "harness (the fake fleet)"),
    ("/tests/testlib/", "harness (test fixtures)"),
    # The two page implementations under comparison.
    ("/cmk/gui/monitor/", "new pages"),
    ("/cmk/gui/painter", "classic views: painters"),
    ("/cmk/gui/views/icon", "classic views: icons"),
    ("/cmk/gui/views/", "classic views"),
    ("/cmk/gui/visuals/", "classic views: filters"),
    ("/cmk/gui/visual_link", "classic views: row links"),
    # What either of them is built on.
    ("/cmk/livestatus_client/", "livestatus client"),
    ("/cmk/gui/openapi/", "rest api framework"),
    ("/cmk/web/htmllib/", "html rendering"),
    ("/cmk/gui/htmllib/", "html rendering"),
    ("/cmk/web/utils/urls", "url building"),
    ("/cmk/gui/config", "gui configuration"),
    ("/cmk/gui/permissions", "permissions"),
    ("/cmk/gui/utils/roles", "permissions"),
    ("/cmk/gui/userdb/", "user database"),
    ("/cmk/gui/watolib/", "setup (watolib)"),
    ("/cmk/gui/wato/", "setup (wato)"),
    ("/cmk/gui/session", "session handling"),
    ("/cmk/gui/ctx_stack", "request context"),
    ("/cmk/gui/hooks", "gui hooks"),
    ("/cmk/gui/", "gui (other)"),
    ("/cmk/web/", "web toolkit (other)"),
    ("/cmk/", "cmk (other)"),
    # Third-party code the request passes through.
    ("/pydantic", "pydantic"),
    ("/werkzeug/local", "request context"),
    ("/flask/", "flask"),
    ("/werkzeug/", "werkzeug"),
    ("/jinja2/", "jinja2"),
    ("/lib/python3.", "python (stdlib)"),
)

_BUILTIN = "python (builtins)"


def component_of(filename: str) -> str:
    """Which component a profiled frame belongs to.

    A frame nothing above claims is labelled by where its file sits rather than swept into a
    catch-all: an unattributed component that turns out to be expensive is exactly the thing
    this is meant to surface, and a bucket named "other" hides it.
    """
    # Under Bazel every file - the product, its dependencies, the stdlib in the venv - sits
    # below a runfiles directory named after *this test target*, so an unstripped path contains
    # this package's own name and every frame in the process would be attributed to the harness.
    # Only what follows the runfiles root says which component a file belongs to.
    stripped = filename.split(".runfiles/", 1)[-1]
    anchored = stripped if stripped.startswith("/") else f"/{stripped}"
    for fragment, label in _COMPONENTS:
        if fragment in anchored:
            return label
    if filename.startswith("<") or filename == "~":
        return _BUILTIN
    parts = Path(filename).parts
    return "/".join(parts[-3:-1]) if len(parts) >= 3 else filename


@dataclass(frozen=True, kw_only=True)
class ComponentProfile:
    """Where one page load spent its time, by component."""

    page: str
    total_seconds: float
    #: Seconds spent *inside* each component's own frames. Self time rather than cumulative
    #: time, so a caller and its callee are never both charged for the same second and the
    #: shares add up to the whole.
    seconds: Mapping[str, float]

    @property
    def shares(self) -> Mapping[str, float]:
        if not self.total_seconds:
            return {}
        return {name: value / self.total_seconds for name, value in self.seconds.items()}

    def ranked(self, limit: int = 12) -> Sequence[tuple[str, float, float]]:
        """The costliest components: name, seconds, share."""
        shares = self.shares
        ordered = sorted(self.seconds.items(), key=lambda item: item[1], reverse=True)
        return [(name, value, shares.get(name, 0.0)) for name, value in ordered[:limit]]

    @property
    def harness_share(self) -> float:
        """How much of the load was the fake fleet rather than the page.

        Reported in its own right rather than left to the ranking: it is the number that decides
        whether the rest of the profile - and every ratio the comparison prints - is measuring
        Checkmk or measuring the test. A ranking hides it precisely when it is reassuring.
        """
        if not self.total_seconds:
            return 0.0
        harness = sum(value for name, value in self.seconds.items() if name.startswith("harness"))
        return harness / self.total_seconds


def profile_page(page: str, run: object) -> ComponentProfile:
    """Profile one page load and attribute its self time to components.

    ``run`` is called twice: once to warm up, then once under the profiler. The fake fleet
    renders each site's answer the first time it is asked and serves it from memory afterwards,
    so profiling a cold run would charge the harness for work no measured round ever pays, and
    the result would say more about the fake than about the page.

    Profiling inflates absolute times, which is why this reports shares: the question is which
    components matter, not how many milliseconds they cost, and the split answers it.
    """
    run()  # type: ignore[operator]

    profiler = cProfile.Profile()
    profiler.enable()
    try:
        run()  # type: ignore[operator]
    finally:
        profiler.disable()

    seconds: dict[str, float] = {}
    for (filename, _lineno, _func), entry in pstats.Stats(profiler).stats.items():  # type: ignore[attr-defined]
        self_time = entry[2]
        name = component_of(filename)
        seconds[name] = seconds.get(name, 0.0) + self_time

    return ComponentProfile(page=page, total_seconds=sum(seconds.values()), seconds=seconds)


def profile_lines(profiles: Sequence[ComponentProfile]) -> Sequence[str]:
    """The component split of each profiled page, as a table."""
    if not profiles:
        return ()

    header = f"{'page':<26} {'component':<28} {'seconds':>9} {'share':>7}"
    lines = [header, "-" * len(header)]
    for profile in profiles:
        for index, (name, value, share) in enumerate(profile.ranked()):
            lines.append(
                f"{profile.page if index == 0 else '':<26} {name:<28} {value:>9.3f} "
                f"{share * 100:>6.1f}%"
            )
        lines.append(
            f"{'':<26} {'  ^ of which the harness':<28} {'':>9} "
            f"{profile.harness_share * 100:>6.1f}%"
        )
        lines.append("")
    return lines
