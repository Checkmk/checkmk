#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import abc
import itertools
import sys
from collections.abc import Callable, Iterator, Mapping
from logging import DEBUG, Logger
from typing import Any, Final

__all__ = [
    "ABCResourceObserver",
    "AbstractMemoryObserver",
    "FetcherMemoryObserver",
    "vm_size",
]


class ABCResourceObserver(abc.ABC):
    __slots__ = ["_logger", "_num_check_cycles", "_hint"]

    def __init__(self, logger: Logger) -> None:
        super().__init__()
        self._logger = logger
        self._num_check_cycles = 0
        self._hint = "<unknown>"

    def _register_check(self, hint: str | None) -> None:
        self._num_check_cycles += 1
        if hint is not None:
            self._hint = hint

    @abc.abstractmethod
    def check_resources(self, hint: str | None) -> None:
        """hint should provide reasonable additional information useful for analysis.
        Good examples are hostname, service name or raw command."""
        raise NotImplementedError()

    def config_has_changed(self) -> None:
        pass

    def _context(self) -> str:
        return f'[cycle {self._num_check_cycles}, host "{self._hint}"]'

    def _warning(self, message: str) -> None:
        self._logger.warning("%s %s", self._context(), message)

    def _error(self, message: str) -> None:
        self._logger.error("%s %s", self._context(), message)

    def _verbose_output_enabled(self) -> bool:
        return self._logger.isEnabledFor(DEBUG)


def vm_size() -> int:
    with open("/proc/self/statm") as f:  # see: man proc(5).
        return int(f.read().split()[0]) * 4096


class AbstractMemoryObserver(ABCResourceObserver):
    """Observes usage of the memory by the current process. Excessive memory usage by
    process is defined as (initial VM size)*self._allowed_growth/100.
    Initial VM size is stored at 5-th call of check_resources().
    """

    __slots__ = [
        "_memory_usage",
        "_hard_limit_percentage",
        "_steady_cycle_num",
        "_get_vm_size",
        "_config_cache_dump_sizes",
    ]

    def __init__(
        self,
        logger: Logger,
        allowed_growth: int,
        get_vm_size: Callable[[], int],
        config_cache_dump_sizes: Callable[[], Mapping[str, int]],
    ) -> None:
        """allowed_growth is the permitted increase of the VM size measured in percents.
        get_vm_size is callback returning the RAM size used by the fetcher"""
        super().__init__(logger)
        self._hard_limit_percentage: Final = allowed_growth
        self._steady_cycle_num: Final = 5  # checked in test as a business rule
        self._get_vm_size: Final = get_vm_size
        self._config_cache_dump_sizes = config_cache_dump_sizes

        self._memory_usage = 0

    def memory_usage(self) -> int:
        return self._memory_usage

    def hard_limit(self) -> int:
        return int(self._hard_limit_percentage / 100 * self._memory_usage)

    def _validate_size(self) -> bool:
        """Determines whether RAM limit was exceeded.
        Registers (once) memory status when steady state is achieved.
        """

        # We should have reached a steady state after 5 check cycles.
        if self._num_check_cycles < self._steady_cycle_num:
            return True

        # We observe every cycle after reaching the steady state.
        # This is OK performance-wise: ~7 microseconds per observation.
        new_memory_usage = self._get_vm_size()
        if self._num_check_cycles == self._steady_cycle_num:
            if self._verbose_output_enabled():
                self._print_global_memory_usage()
            self._memory_usage = new_memory_usage
            return True

        return new_memory_usage <= self.hard_limit()

    def _print_global_memory_usage(self) -> None:
        storage = dict(globals())  # to be sure that globals will not be changed

        globals_sizes = {varname: _total_size(value) for (varname, value) in storage.items()}
        self._dump("APPROXIMATE SIZES: GLOBALS TOP 50", globals_sizes, 50)
        for title, dump_sizes in [
            ("CONFIG CACHE", self._config_cache_dump_sizes),
        ]:
            self._dump("APPROXIMATE SIZES: %s" % title, dump_sizes(), None)

    def _dump(self, header: str, sizes: Mapping[str, int], limit: int | None) -> None:
        self._warning("=== %s ====" % header)
        for varname, size_bytes in sorted(sizes.items(), key=lambda x: x[1], reverse=True)[:limit]:
            self._warning("%10s %s" % (_fmt_bytes(size_bytes), varname))


class FetcherMemoryObserver(AbstractMemoryObserver):
    """Controls usage of the memory by the Fetcher.
    Call sys.exit(14) if during call of check_resources() memory is overloaded.
    The Micro Core is responsible for restart of Fetcher.
    """

    def __init__(
        self,
        *,
        logger: Logger,
        allowed_growth: int,
        get_vm_size: Callable[[], int],
        config_cache_dump_sizes: Callable[[], Mapping[str, int]],
    ) -> None:
        super().__init__(logger, allowed_growth, get_vm_size, config_cache_dump_sizes)

    def _context(self) -> str:
        return f'[cycle {self._num_check_cycles}, command "{self._hint}"]'

    def check_resources(self, hint: str | None, verbose: bool = True) -> None:
        self._register_check(hint)

        if not self._validate_size():
            if verbose:
                self._log_verbose_info()
            sys.exit(14)

    def _log_verbose_info(self):
        self._print_global_memory_usage()
        self._error(
            "memory usage increased from %s to %s, exiting"
            % (_fmt_bytes(self.memory_usage()), _fmt_bytes(self._get_vm_size()))
        )


def _fmt_bytes(v: float) -> str:
    for prefix in ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"):
        if abs(v) < 1024:
            return f"{v:.2f} {prefix}"
        v /= 1024
    return f"{v:.2f} YiB"


def _total_size(o: object) -> int:
    """Returns the approximate memory footprint an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses:  tuple, list, dict, set and frozenset.
    """
    all_handlers: dict[type[Any], Callable[[Any], Iterator[object]]] = {
        tuple: iter,
        list: iter,
        dict: lambda d: itertools.chain.from_iterable(d.items()),
        set: iter,
        frozenset: iter,
    }
    seen: set[int] = set()
    default_size = sys.getsizeof(0)  # estimate sizeof object without __sizeof__

    def sizeof(o: object) -> int:
        if id(o) in seen:  # do not double count the same object
            return 0
        seen.add(id(o))
        s = sys.getsizeof(o, default_size)

        for typ, handler in all_handlers.items():
            if isinstance(o, typ):
                s += sum(map(sizeof, handler(o)))
                break
        return s

    return sizeof(o)
