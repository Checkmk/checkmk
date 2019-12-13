# coding=utf-8
# yapf: disable
import pytest

from checktestlib import assertCheckResultsEqual, CheckResult

KILO = 1024

MEGA = KILO**2

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
        # POSITIVE ABSOLUTE levels of OK, WARN, CRIT
        ((43, 43), MEMINFO_MINI, [
            (0, TEXT_MINI, [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 43, 43, 0, 42.0),
            ]),
        ]),
        ({"levels": (20, 43)}, MEMINFO_MINI, [
            (1, TEXT_MINI + ", warn/crit at 20.00 MB/43.00 MB used", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 20, 43, 0, 42.0),
            ]),
        ]),
        ({"levels": (20, 20)}, MEMINFO_MINI, [
            (2, TEXT_MINI + ", warn/crit at 20.00 MB/20.00 MB used", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 20, 20, 0, 42.0),
            ]),
        ]),
        # NEGATIVE ABSOLUTE levels OK, WARN, CRIT
        ((-4, -3), MEMINFO_MINI, [
            (0, TEXT_MINI, [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 38.0, 39.0, 0, 42.0),
            ]),
        ]),
        ((-43, -3), MEMINFO_MINI, [
            (1, TEXT_MINI + ", warn/crit below 43.00 MB/3.00 MB free", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, -1.00, 39.0, 0, 42.0),
            ]),
        ]),
        ((-41, -41), MEMINFO_MINI, [
            (2, TEXT_MINI + ", warn/crit below 41.00 MB/41.00 MB free", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 1.0, 1.0, 0, 42.0),
            ]),
        ]),
        # POSITIVE Percentage levels OK, WARN, CRIT
        ((80.0, 90.0), MEMINFO_MINI, [
            (0, TEXT_MINI, [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 33.6, 37.800000000000004, 0, 42.0),  # sorry
            ]),
        ]),
        ((10.0, 90.0), MEMINFO_MINI, [
            (1, TEXT_MINI + ", warn/crit at 10.0%/90.0% used", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 4.2, 37.800000000000004, 0, 42.0),
            ]),
        ]),
        ((10.0, 10.0), MEMINFO_MINI, [
            (2, TEXT_MINI + ", warn/crit at 10.0%/10.0% used", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 4.2, 4.2, 0, 42.0),
            ]),
        ]),
        # NEGATIVE Percentage levels OK, WARN, CRIT
        ((-10.0, -10.0), MEMINFO_MINI, [
            (0, TEXT_MINI, [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 37.8, 37.8, 0, 42.0),
            ]),
        ]),
        ((-90.0, -10.0), MEMINFO_MINI, [
            (1, TEXT_MINI + ", warn/crit below 90.0%/10.0% free", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 4.199999999999996, 37.8, 0, 42.0),
            ]),
        ]),
        ((-90.0, -80.0), MEMINFO_MINI, [
            (2, TEXT_MINI + ", warn/crit below 90.0%/80.0% free", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 4.199999999999996, 8.399999999999999, 0, 42.0),
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
            (1, TEXT_SWAP + ", warn/crit at 23.00 MB/43.00 MB used", [
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 21.0, None, None, 0, 42.0),
                ('memused', 42.0, 23, 43, 0, 84.0),
            ]),
        ]),
        ({"levels": (23, 23)}, MEMINFO_SWAP, [
            (2, TEXT_SWAP + ", warn/crit at 23.00 MB/23.00 MB used", [
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
                ('pagetables', 7),
                ('ramused', 14.0, None, None, 0, 42.0),
                ('swapused', 21.0, None, None, 0, 42.0),
                ('memused', 42.0, 43, 43, 0, 84.0),
            ]),
        ]),
        # averaging
        ({"average": 3, "levels": (43, 43)}, MEMINFO_MINI, [
            (0, TEXT_MINI + ", 3 min average 50.0%", [
                ('memusedavg', 21.0, None, None, None, None),
                ('ramused', 21.0, None, None, 0, 42.0),
                ('swapused', 0, None, None, 0, 0),
                ('memused', 21.0, 43, 43, 0, 42.0),
            ]),
        ]),
        # Mapped
        ((150.0, 190.0), MEMINFO_PAGE_MAPPED, [
            (0, TEXT_PAGE + ", 12.00 MB mapped, 3.00 MB committed, 1.00 MB shared", [
                ('pagetables', 7),
                ('ramused', 14.0, None, None, 0, 42.0),
                ('swapused', 21, None, None, 0, 42.0),
                ('memused', 42.0, 63.0, 79.8, 0, 84.0),
                ('mapped', 12),
                ('committed_as', 3),
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



TEXT_MM_50 = "50.0% used (21.00 MB of 42.00 MB)"

@pytest.mark.parametrize(
    "params,data,base,expected",
    [
        # invalid
        ({}, {}, KILO, [
            (3, "Invalid data: missing mem_total", []),
        ]),
        ({}, {'mem_total': 42 * KILO**2}, KILO, [
            (3, "Invalid data: missing mem_used or mem_avail sizes", []),
        ]),
        # no levels
        ({}, {'mem_total': 42 * KILO**2, 'mem_avail': 21 * KILO**2}, KILO, [
            (0, TEXT_MM_50, [
                ('memused', 22020096, None, None, 0, 44040192),
            ]),
        ]),
        ({}, {'mem_total': 42 * KILO**2, 'mem_used': 21 * KILO**2}, KILO, [
            (0, TEXT_MM_50, [
                ('memused', 22020096, None, None, 0, 44040192),
            ]),
        ]),
        # decimal base
        ({}, {'mem_total': 42 * 1000**2, 'mem_used': 21 * 1000**2}, 1000, [
            (0, TEXT_MM_50, [
                ('memused', 21000000, None, None, 0, 42000000),
            ]),
        ]),
        # with some levels
        ({'levels': (40.0, 60.0)}, {'mem_total': 42 * MEGA, 'mem_used': 21 * MEGA}, KILO, [
            (1, TEXT_MM_50 + " (warn/crit at 16.80 MB/25.20 MB)", [  # FIXME
                ('memused', 22020096, 17616076, 26424115, 0, 44040192),
            ]),
        ]),
        ({'levels': (1024, 2048)}, {'mem_total': 42 * MEGA, 'mem_used': 21 * MEGA}, KILO, [
            (2, TEXT_MM_50 + " (warn/crit at 1.00 kB/2.00 kB)", [
                ('memused', 22020096, 1024.0, 2048.0, 0, 44040192),
            ]),
        ]),
        # not yet working:
        #({'levels': (None, None)}, {'mem_total': 42 * MEGA, 'mem_used': 21 * MEGA}, KILO, [
        #    (0, TEXT_MM_50, [
        #        ('memused', 22020096, None, None, 0, 44040192),
        #    ]),
        #]),
    ],
)
def test_check_memory_multiitem(check_manager, params, data, base, expected):
    check_memory_multiitem = check_manager.get_check("ucd_mem").context["check_memory_multiitem"]
    result = check_memory_multiitem(params, data, base=base)
    assertCheckResultsEqual(CheckResult(result), CheckResult(expected))


TEXT_MS_50 = "Usage: 50.0% (Used: 21.00 MB, Total: 42.00 MB)"

@pytest.mark.parametrize(
    "params,used,total,expected",
    [
        ({}, 21 * MEGA, 42 * MEGA, [
            (0, TEXT_MS_50, [
                ('memory_used', 21 * MEGA, None, None, 0, 42 * MEGA),
            ]),
        ]),
        ((), 21 * MEGA, 42 * MEGA, [
            (0, TEXT_MS_50, [
                ('memory_used', 21 * MEGA, None, None, 0, 42 * MEGA),
            ]),
        ]),
        ((100, 100), 21 * MEGA, 42 * MEGA, [
            (0, TEXT_MS_50, [
                ('memory_used', 21 * MEGA, 42 * MEGA, 42 * MEGA, 0, 42 * MEGA),
            ]),
        ]),
        ({"levels": "ignore"}, 21 * MEGA, 42 * MEGA, [
            (0, TEXT_MS_50, [
                ('memory_used', 21 * MEGA, None, None, 0, 42 * MEGA),
            ]),
        ]),
        ({"levels": ("perc_used", (45, 54))}, 21 * MEGA, 42 * MEGA, [
            (1, TEXT_MS_50 + " (warn/crit at 45.0%/54.0% used)", [
                ('memory_used', 21 * MEGA, 19818086.400000002, 23781703.68, 0, 42 * MEGA),
            ]),
        ]),
        ({"levels": ("abs_free", (90 * MEGA, 80 * MEGA))}, 21 * MEGA, 42 * MEGA, [
            (2, TEXT_MS_50 + " (warn/crit below 90.00 MB/80.00 MB free)", [
                ('memory_used', 21 * MEGA, -50331648, -39845888, 0, 42 * MEGA),  # FIXME
            ]),
        ]),
    ],
)
def test_check_memory_simple(check_manager, params, used, total, expected):
    check_memory_simple = check_manager.get_check("ucd_mem").context["check_memory_simple"]
    result = check_memory_simple(used, total, params)
    assertCheckResultsEqual(CheckResult(result), CheckResult(expected))
