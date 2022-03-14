from typing import Any, MutableMapping, Optional, Tuple

from ..agent_based_api.v1 import check_levels, render, Result, State
from ..agent_based_api.v1.type_defs import CheckResult


def tolerance_check(
    *,
    set_sync_time: Optional[float],
    levels_upper: Optional[Tuple[float, float]],
    notice_only: bool = False,
    now: float,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    if set_sync_time is not None:
        value_store["time_server"] = set_sync_time
        return

    label = "Time since last sync"
    last_sync = value_store.get("time_server")
    if last_sync is None:
        value_store["time_server"] = now
        if notice_only:
            yield Result(state=State.OK, notice=f"{label}: N/A (started monitoring)")
        else:
            yield Result(state=State.OK, summary=f"{label}: N/A (started monitoring)")
        return

    if now - last_sync < 0:
        yield Result(
            state=State.CRIT,
            summary="Cannot reasonably calculate time since last synchronization "
            "(hosts time is running ahead)",
        )
        return

    yield from check_levels(
        value=now - last_sync,
        levels_upper=levels_upper,
        render_func=render.timespan,
        label=label,
        notice_only=notice_only,
    )
