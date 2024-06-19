#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#   .--output--------------------------------------------------------------.
#   |                               _               _                      |
#   |                    ___  _   _| |_ _ __  _   _| |_                    |
#   |                   / _ \| | | | __| '_ \| | | | __|                   |
#   |                  | (_) | |_| | |_| |_) | |_| | |_                    |
#   |                   \___/ \__,_|\__| .__/ \__,_|\__|                   |
#   |                                  |_|                                 |
#   '----------------------------------------------------------------------'

# Example output from agent:
# <<<zfs_arc_cache>>>
# hits                      = 106259988004
# misses                    = 27664604758
# demand_data_hits          = 23694052185
# demand_data_misses        = 2806853416
# demand_metadata_hits      = 73187550363
# demand_metadata_misses    = 1557349557
# prefetch_data_hits        = 3100882779
# prefetch_data_misses      = 21062611239
# prefetch_metadata_hits    = 6277502677
# prefetch_metadata_misses  = 2237790546
# mru_hits                  = 44007947284
# mru_ghost_hits            = 2418664836
# mfu_hits                  = 52875478045
# mfu_ghost_hits            = 1458768458
# deleted                   = 25139978315
# recycle_miss              = 3965481664
# mutex_miss                = 323199589
# evict_skip                = 2543918629307
# evict_l2_cached           =         0
# evict_l2_eligible         = 253548767148544
# evict_l2_ineligible       = 36185885241856
# hash_elements             =    182514
# hash_elements_max         =    388216
# hash_collisions           = 6825894732
# hash_chains               =     14194
# hash_chain_max            =         8
# p                         =       914 MB
# c                         =      2010 MB
# c_min                     =      2010 MB
# c_max                     =       320 MB
# size                      =      1554 MB
# hdr_size                  =  36128904
# data_size                 = 951095808
# other_size                = 642656472
# l2_hits                   =         0
# l2_misses                 =         0
# l2_feeds                  =         0
# l2_rw_clash               =         0
# l2_read_bytes             =         0
# l2_write_bytes            =         0
# l2_writes_sent            =         0
# l2_writes_done            =         0
# l2_writes_error           =         0
# l2_writes_hdr_miss        =         0
# l2_evict_lock_retry       =         0
# l2_evict_reading          =         0
# l2_free_on_write          =         0
# l2_abort_lowmem           =         0
# l2_cksum_bad              =         0
# l2_io_error               =         0
# l2_size                   =         0
# l2_hdr_size               =         0
# memory_throttle_count     =    439874
# arc_no_grow               =         1
# arc_tempreserve           =         0 MB
# arc_meta_used             =      1322 MB
# arc_meta_limit            =        80 MB
# arc_meta_max              =      2077 MB

# newer output under solaris 11.3 with old agent
# <<<zfs_arc_cache>>>
# size                      =        46751 MB
# target size (c)           =      1027788 MB
# target mru_size (p)       =        64236 MB
# c_min                     =         4018 MB
# c_max                     =      1027788 MB
# buf_size                  =          605 MB
# data_size                 =        43123 MB
# other_size                =         2988 MB
# rawdata_size              =            0 MB
# meta_used                 =         3628 MB
# meta_max                  =         3628 MB
# meta_limit                =            0 MB
# memory_throttle_count     =            0
# arc_no_grow               =            0
# arc_tempreserve           =            0 MB
# mfu_size                  =        30605 MB
# mru_size                  =        11601 MB

# newer output under solaris 11.3 with updated agent
# <<<zfs_arc_cache>>>
# buf_size = 742832600
# c = 48841615704
# c_max = 1077714329600
# c_min = 4214015904
# class = misc
# crtime = 6389056,11403263
# data_freed = 2633453157248
# data_size = 45014421888
# deleted = 9360622
# demand_data_hits = 645028929
# demand_data_misses = 9656913
# demand_metadata_hits = 3819285336
# demand_metadata_misses = 1934895
# evict_l2_cached = 0
# evict_l2_eligible = 0
# evict_l2_ineligible = 607708484608
# evict_prefetch = 977715200
# evicted_mfu = 44603686912
# evicted_mru = 563104797696
# hash_chain_max = 5
# hash_chains = 70415
# hash_collisions = 2812966
# hash_elements = 1585475
# hash_elements_max = 1810662
# hits = 4467022475
# l2_abort_lowmem = 0
# l2_cksum_bad = 0
# l2_feeds = 0
# l2_hdr_size = 0
# l2_hits = 0
# l2_imports = 0
# l2_io_error = 0
# l2_misses = 7259729
# l2_persistence_hits = 0
# l2_read_bytes = 0
# l2_rw_clash = 0
# l2_size = 0
# l2_write_bytes = 0
# l2_writes_done = 0
# l2_writes_error = 0
# l2_writes_sent = 0
# memory_throttle_count = 0
# meta_limit = 0
# meta_max = 4519225600
# meta_used = 3836680704
# mfu_ghost_hits = 27965
# mfu_hits = 4444241817
# misses = 11591808
# mru_ghost_hits = 499269
# mru_hits = 47780363
# mutex_miss = 46709
# other_size = 3058023880
# p = 15479322529
# prefetch_behind_prefetch = 429897
# prefetch_data_hits = 1849310
# prefetch_joins = 1305700
# prefetch_meta_size = 35824224
# prefetch_metadata_hits = 858900
# prefetch_reads = 3616694
# prefetch_size = 9486336
# rawdata_size = 0
# size = 48851102592
# snaptime = 6646791,81811455

# <<<zfs_arc_cache>>>
# hits                      = 97798158981
# misses                    = 29159034052
# demand_data_hits          = 21894170403
# demand_data_misses        = 6555284601
# demand_metadata_hits      = 67915356653
# demand_metadata_misses    = 2138181167
# prefetch_data_hits        = 6162208911
# prefetch_data_misses      = 19200459846
# prefetch_metadata_hits    = 1826423014
# prefetch_metadata_misses  = 1265108438
# mru_hits                  = 32456530155
# mru_ghost_hits            = 2084134895
# mfu_hits                  = 57357428725
# mfu_ghost_hits            = 1416265946
# deleted                   = 26434603017
# recycle_miss              = 2014989945
# mutex_miss                = 548212067
# evict_skip                = 1758367956525
# evict_l2_cached           =         0
# evict_l2_eligible         = 236579643061760
# evict_l2_ineligible       = 68829096635392
# hash_elements             =    235200
# hash_elements_max         =    441047
# hash_collisions           = 5893650106
# hash_chains               =     22800
# hash_chain_max            =         8
# p                         =       242 MB
# c                         =      2048 MB
# c_min                     =      2010 MB
# c_max                     =      2048 MB
# size                      =      1658 MB
# hdr_size                  =  76639184
# data_size                 = 998181888
# other_size                = 664157400
# l2_hits                   =         0
# l2_misses                 =         0
# l2_feeds                  =         0
# l2_rw_clash               =         0
# l2_read_bytes             =         0
# l2_write_bytes            =         0
# l2_writes_sent            =         0
# l2_writes_done            =         0
# l2_writes_error           =         0
# l2_writes_hdr_miss        =         0
# l2_evict_lock_retry       =         0
# l2_evict_reading          =         0
# l2_free_on_write          =         0
# l2_abort_lowmem           =         0
# l2_cksum_bad              =         0
# l2_io_error               =         0
# l2_size                   =         0
# l2_hdr_size               =         0
# memory_throttle_count     =   1014537
# arc_no_grow               =         0
# arc_tempreserve           =         0 MB
# arc_meta_used             =      1196 MB
# arc_meta_limit            =       512 MB
# arc_meta_max              =      2132 MB

# .

# parses agent output in a structure like
# {'arc_meta_limit': 80,
#  'arc_meta_max': 2077,
#  'arc_meta_used': 1322,
# [...]
# }

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, int]


def parse_zfs_arc_cache(string_table: StringTable) -> Section:
    parsed = {}
    for line in string_table:
        if not (len(line) >= 3 and line[1] == "=" and line[2].isdigit()):
            continue

        factor = 1
        if len(line) == 4:
            if line[3].lower() == "mb":
                factor = 1024**2
            elif line[3].lower() == "kb":
                factor = 1024
        parsed[line[0]] = int(line[2]) * factor
    return parsed


agent_section_zfs_arc_cache = AgentSection(
    name="zfs_arc_cache",
    parse_function=parse_zfs_arc_cache,
)


#   .--cache---------------------------------------------------------------.
#   |                                     _                                |
#   |                       ___ __ _  ___| |__   ___                       |
#   |                      / __/ _` |/ __| '_ \ / _ \                      |
#   |                     | (_| (_| | (__| | | |  __/                      |
#   |                      \___\__,_|\___|_| |_|\___|                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_zfs_arc_cache(section: Section) -> DiscoveryResult:
    if section.get("hits") and section.get("misses"):
        yield Service()


def check_zfs_arc_cache(section: Section) -> CheckResult:
    # Solaris >= 11.3 do not provide these data pretech_*data
    for key in ["", "prefetch_data_", "prefetch_metadata_"]:
        if "%shits" % key in section and "%smisses" % key in section:
            total_hits_misses = section["%shits" % key] + section["%smisses" % key]
            human_key = key.replace("_", " ")

            if total_hits_misses:
                hit_ratio = float(section["%shits" % key]) / total_hits_misses * 100
                yield Result(
                    state=State.OK, summary=f"{human_key.title()}Hit Ratio: {hit_ratio:0.2f}%"
                )
                yield Metric("%shit_ratio" % key, hit_ratio, boundaries=(0, 100))

            else:
                yield Result(state=State.OK, summary="No %sHits or Misses" % human_key)

    # size
    if "size" in section:
        size_bytes = section["size"]
        size_readable = render.bytes(size_bytes)
        yield Result(state=State.OK, summary="Cache size: %s" % size_readable)
        yield Metric("size", float(size_bytes), boundaries=(0, None))

    # arc_meta
    # these values may be missing, this is ok too
    # in this case just do not report these values
    if "arc_meta_used" in section and "arc_meta_limit" in section and "arc_meta_max" in section:
        yield Result(
            state=State.OK,
            summary="Arc Meta {} used, Limit {}, Max {}".format(
                render.bytes(section["arc_meta_used"]),
                render.bytes(section["arc_meta_limit"]),
                render.bytes(section["arc_meta_max"]),
            ),
        )
        yield Metric("arc_meta_used", float(section["arc_meta_used"]), boundaries=(0, None))
        yield Metric("arc_meta_limit", float(section["arc_meta_limit"]), boundaries=(0, None))
        yield Metric("arc_meta_max", float(section["arc_meta_max"]), boundaries=(0, None))


check_plugin_zfs_arc_cache = CheckPlugin(
    name="zfs_arc_cache",
    service_name="ZFS arc cache",
    discovery_function=inventory_zfs_arc_cache,
    check_function=check_zfs_arc_cache,
)

# .
#   .--L2 cache------------------------------------------------------------.
#   |               _     ____                   _                         |
#   |              | |   |___ \    ___ __ _  ___| |__   ___                |
#   |              | |     __) |  / __/ _` |/ __| '_ \ / _ \               |
#   |              | |___ / __/  | (_| (_| | (__| | | |  __/               |
#   |              |_____|_____|  \___\__,_|\___|_| |_|\___|               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_zfs_arc_cache_l2(section: Section) -> DiscoveryResult:
    # if l2_size == 0 there is no l2 cache available at all
    if "l2_size" in section and section["l2_size"] > 0:
        yield Service()


def check_zfs_arc_cache_l2(section: Section) -> CheckResult:
    # hit ratio
    if "l2_hits" in section and "l2_misses" in section:
        l2_hit_ratio = float(section["l2_hits"]) / (section["l2_hits"] + section["l2_misses"]) * 100
        yield Result(state=State.OK, summary="L2 hit ratio: %0.2f%%" % l2_hit_ratio)
        yield Metric("l2_hit_ratio", l2_hit_ratio, boundaries=(0, 100))
    else:
        yield Result(state=State.UNKNOWN, summary="No info about L2 hit ratio available")

    # size
    if "l2_size" in section:
        yield Result(state=State.OK, summary="L2 size: %s" % render.bytes(section["l2_size"]))
        yield Metric("l2_size", float(section["l2_size"]), boundaries=(0, None))
    else:
        yield Result(state=State.UNKNOWN, summary="No info about L2 size available")


check_plugin_zfs_arc_cache_l2 = CheckPlugin(
    name="zfs_arc_cache_l2",
    service_name="ZFS arc cache L2",
    sections=["zfs_arc_cache"],
    discovery_function=inventory_zfs_arc_cache_l2,
    check_function=check_zfs_arc_cache_l2,
)
