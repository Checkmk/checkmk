import time
from typing import Any, MutableMapping, Optional, Tuple

from ..agent_based_api.v1 import check_levels, render, Result, State
from ..agent_based_api.v1.type_defs import CheckResult


def store_sync_time(value_store: MutableMapping[str, Any], sync_time: float) -> None:
    value_store["time_server"] = sync_time


def _check_time_difference(
    sync_time: float,
    now: float,
    levels_upper: Optional[Tuple[float, float]],
    label: str,
    notice_only: bool,
) -> CheckResult:

    time_difference = now - sync_time
    if time_difference < 0:
        yield Result(
            state=State.CRIT,
            summary="Cannot reasonably calculate time since last synchronization "
            "(hosts time is running ahead)",
        )
        return

    yield from check_levels(
        value=time_difference,
        levels_upper=levels_upper,
        render_func=render.timespan,
        label=label,
        notice_only=notice_only,
    )


def tolerance_check(
    *,
    sync_time: Optional[float],
    levels_upper: Optional[Tuple[float, float]],
    value_store: MutableMapping[str, Any],
    notice_only: bool = False,
) -> CheckResult:

    label = "Time since last sync"
    now = time.time()

    if sync_time is None:
        if (last_sync := value_store.get("time_server")) is None:
            store_sync_time(value_store, now)

            if notice_only:
                yield Result(state=State.OK, notice=f"{label}: N/A (started monitoring)")
            else:
                yield Result(state=State.OK, summary=f"{label}: N/A (started monitoring)")
            return

        yield from _check_time_difference(
            last_sync,
            now,
            levels_upper,
            label,
            notice_only,
        )
    else:
        store_sync_time(value_store, sync_time)

        yield from _check_time_difference(
            sync_time,
            now,
            levels_upper,
            label,
            notice_only,
        )
