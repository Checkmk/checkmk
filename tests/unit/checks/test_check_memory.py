# coding=utf-8
# yapf: disable
import pytest

from checktestlib import assertCheckResultsEqual, CheckResult

KILO = 1024

MEMINFO_MINI = {  # minimal not failing case
    "MemTotal": 42 * KILO,  # value in kB, this means 42 MB.
    "MemFree": 21* KILO,
    "SwapTotal": 0,  # must be present, but may be zero
    "SwapFree": 0,
}

TEXT_MINI = "21.00 MB used (this is 50.0% of 42.00 MB RAM)"


MEMINFO_SWAP = {
    "MemTotal": 42 * KILO,
    "MemFree": 21* KILO,
    "SwapTotal": 42 * KILO,
    "SwapFree": 21 * KILO,
}


MEMINFO_SWAP_CACHED = {
    "MemTotal": 42 * KILO,
    "MemFree": 14 * KILO,
    "SwapTotal": 42 * KILO,
    "SwapFree": 21 * KILO,
    "Cached": 7 * KILO,  # should cancel out with decreased MemFree -> easier testing
}


MEMINFO_SWAP_BUFFERS = {
    "MemTotal": 42 * KILO,
    "MemFree": 14 * KILO,
    "SwapTotal": 42 * KILO,
    "SwapFree": 21 * KILO,
    "Buffers": 7 * KILO,  # should cancel out with decreased MemFree -> easier testing
}


TEXT_SWAP = "42.00 MB used (21.00 MB RAM + 21.00 MB SWAP, this is 100.0% of 42.00 MB RAM + 42.00 MB SWAP)"


MEMINFO_PAGE = {
    "MemTotal": 42 * KILO,
    "MemFree": 28 * KILO,
    "SwapTotal": 42 * KILO,
    "SwapFree": 21 * KILO,
    "PageTables": 7 * KILO,  # should cancel out with increased MemFree -> easier testing
}


MEMINFO_PAGE_MAPPED = {
    "MemTotal": 42 * KILO,
    "MemFree": 28 * KILO,
    "SwapTotal": 42 * KILO,
    "SwapFree": 21 * KILO,
    "PageTables": 7 * KILO,
    "Mapped": 12 * KILO,
    "Committed_AS": 3 * KILO,
    "Shmem": 1 * KILO,
}


TEXT_PAGE = (
    "42.00 MB used (14.00 MB RAM + 21.00 MB SWAP + 7.00 MB Pagetables,"
    " this is 100.0% of 42.00 MB RAM + 42.00 MB SWAP)"
)


# The following test is just added to nail down the current behaviour.
# I am making no statement about whether it needs to be this way.
@pytest.mark.parametrize(
    "params,meminfo,fail_with_exception",
    [
        # The following inputs and outputs are expected to succeed
        # as no levels are checked, or the levels are OK.
        ((80., 90.), {}, KeyError),
        ({}, MEMINFO_MINI, KeyError),
        ((80., 90.), {"MemTotal": 42 * KILO, "MemFree": 28 * KILO}, KeyError),
    ],
)
def test_check_memory_fails(check_manager, params, meminfo, fail_with_exception):
    check_memory = check_manager.get_check("mem.used").context["check_memory"]
    with pytest.raises(fail_with_exception):
        check_memory(params, meminfo)

@pytest.mark.parametrize(
    "params,meminfo,expected",
    [
        # ABSOLUTE levels of OK, WARN, CRIT
        ((43, 43), MEMINFO_MINI, [
            (0, TEXT_MINI, [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 43, 43, 0, 42.0),
            ]),
        ]),
        ({"levels": (20, 43)}, MEMINFO_MINI, [
            (1, TEXT_MINI + ", warning at 0.02 GB used", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 20, 43, 0, 42.0),
            ]),
        ]),
        ({"levels": (20, 20)}, MEMINFO_MINI, [
            (2, TEXT_MINI + ", critical at 0.02 GB used", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 20, 20, 0, 42.0),
            ]),
        ]),
        # NEGATIVE levels OK, WARN, CRIT
        ((-4, -3), MEMINFO_MINI, [
            (0, TEXT_MINI, [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, -4, -3, 0, 42.0),  # FIXME
            ]),
        ]),
        ((-43, -3), MEMINFO_MINI, [
            (1, TEXT_MINI + ", warning at 0.04 GB free", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, -43, -3, 0, 42.0),  # FIXME
            ]),
        ]),
        ((-43, -43), MEMINFO_MINI, [
            (2, TEXT_MINI + ", critical at 0.04 GB free", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, -43, -43, 0, 42.0),  # FIXME
            ]),
        ]),
        # Percentage levels OK, WARN, CRIT
        ((80.0, 90.0), MEMINFO_MINI, [
            (0, TEXT_MINI, [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 33, 37, 0, 42.0),
            ]),
        ]),
        ((10.0, 90.0), MEMINFO_MINI, [
            (1, TEXT_MINI + ", warning at 10.0% used", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 4, 37, 0, 42.0),
            ]),
        ]),
        ((10.0, 10.0), MEMINFO_MINI, [
            (2, TEXT_MINI + ", critical at 10.0% used", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 4, 4, 0, 42.0),
            ]),
        ]),
        # now with swap != 0
        ((43, 43), MEMINFO_SWAP, [
            (0, TEXT_SWAP, [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 21.0, None, None, 0, 42.0),
                ('memused', 42.0, 43, 43, 0, 84.0),
            ]),
        ]),
        ({"levels": (23, 43)}, MEMINFO_SWAP, [
            (1, TEXT_SWAP + ", warning at 0.02 GB used", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 21.0, None, None, 0, 42.0),
                ('memused', 42.0, 23, 43, 0, 84.0),
            ]),
        ]),
        ({"levels": (23, 23)}, MEMINFO_SWAP, [
            (2, TEXT_SWAP + ", critical at 0.02 GB used", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 21.0, None, None, 0, 42.0),
                ('memused', 42.0, 23, 23, 0, 84.0),
            ]),
        ]),
        # Buffer + Cached
        ((43, 43), MEMINFO_SWAP_BUFFERS, [
            (0, TEXT_SWAP, [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 21.0, None, None, 0, 42.0),
                ('memused', 42.0, 43, 43, 0, 84.0),
            ]),
        ]),
        ((43, 43), MEMINFO_SWAP_CACHED, [
            (0, TEXT_SWAP, [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 21.0, None, None, 0, 42.0),
                ('memused', 42.0, 43, 43, 0, 84.0),
            ]),
        ]),
        # page tables
        ((43, 43), MEMINFO_PAGE, [
            (0, TEXT_PAGE, [
                ('ramused', 14.0, None, None, 0, 42.0),
                ('swapused', 21.0, None, None, 0, 42.0),
                ('memused', 42.0, 43, 43, 0, 84.0),  # TODO: why no pagetables?
            ]),
        ]),
        # averaging
        ({"average": 3, "levels": (43, 43)}, MEMINFO_MINI, [
            (0, TEXT_MINI + ", 3 min average 50.0%", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 43, 43, 0, 42.0),
                ('memusedavg', 21.0, None, None, None, None),
            ]),
        ]),
        # Mapped
        ((150.0, 190.0), MEMINFO_PAGE_MAPPED, [
            (0, TEXT_PAGE + ", 0.0 mapped, 0.0 committed, 0.0 shared", [
                ('ramused', 14.0, None, None, 0, 42.0),
                ('swapused', 21, None, None, 0, 42.0),
                ('memused', 42.0, 63, 79, 0, 84.0),
                ('mapped', 12),
                ('committed_as', 3),
                ('pagetables', 7),
                ('shared', 1),
            ]),
        ]),
    ],
)
def test_check_memory(check_manager, params, meminfo, expected):
    check_memory = check_manager.get_check("mem.used").context["check_memory"]
    copy_info = meminfo.copy()
    result = check_memory(params, meminfo)

    assertCheckResultsEqual(CheckResult(result), CheckResult(expected))
    assert copy_info == meminfo
