#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Dict, List, Mapping, NamedTuple, Optional

from .agent_based_api.v1 import get_value_store, IgnoreResults, register, render, Result, Service
from .agent_based_api.v1 import State as state
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.df import df_check_filesystem_single

# future todos in checkcode
# - RAC: 1 of 3 nodes has a DISMOUNTED DG. This is not a CRIT!

# Example output from asmcmd lsdg:
# State    Type    Rebal  Sector  Block       AU  Total_MB  Free_MB  Req_mir_free_MB  Usable_file_MB  Offline_disks  Voting_files  Name
# MOUNTED  NORMAL  N         512   4096  1048576    512000    92888                0           46444              0             N  DATA/
# MOUNTED  NORMAL  N         512   4096  1048576      3072     2146              309             918              0             Y  OCR_VOTE/
# DISMOUNTED  N 0 0 0 0 0 0 0 0 N DB_DG1/
# DISMOUNTED  N 0 4096 0 0 0 0 0 0 N ABC/
# MOUNTED EXTERN N 512 4096 1048576 2047984 163379 0 163379 0 N XYZ/
# MOUNTED EXTERN N 512 4096 1048576 307092 291710 0 291710 0 N HUHU/
# DISMOUNTED  N 0 4096 0 0 0 0 0 0 N FOO/
# DISMOUNTED  N 0 4096 0 0 0 0 0 0 N BAR/

# The agent section <<<oracle_asm_diskgroup>>> does not output the header line

# new format with Failuregroup details:
# state type dgname block au req_mir_free_mb total_mb free_mb fg_name voting_files fg_type offline_disks fg_min_repair_time fg_disks
#
# MOUNTED|EXTERN|FRA|4096|4194304|0|10236|4468|FRA01|N|REGULAR|0|8640000|1
# MOUNTED|EXTERN|GRID|4096|4194304|0|5112|5016|GRID01|N|REGULAR|0|8640000|1
# MOUNTED|NORMAL|DATA|4096|4194304|102396|614376|476280|NS1|N|REGULAR|0|8640000|3
# MOUNTED|NORMAL|DATA|4096|4194304|102396|614376|476280|NS2|N|REGULAR|0|8640000|3

ASM_DISKGROUP_DEFAULT_LEVELS = {
    "levels": (80.0, 90.0),  # warn/crit in percent
    "magic_normsize": 20,  # Standard size if 20 GB
    "levels_low": (50.0, 60.0),  # Never move warn level below 50% due to magic factor
    "trend_range": 24,
    "trend_perfdata": True,  # do send performance data for trends
    "req_mir_free": False,  # Ignore Requirre mirror free space in DG
}


class Failgroup(NamedTuple):
    fg_name: str
    fg_voting_files: str
    fg_type: str
    fg_free_mb: int
    fg_total_mb: int
    fg_disks: int
    fg_min_repair_time: int


class Diskgroup(NamedTuple):
    dgstate: str
    dgtype: Optional[str]
    total_mb: Optional[int]
    free_mb: Optional[int]
    req_mir_free_mb: int
    offline_disks: int
    voting_files: str
    fail_groups: List[Failgroup]


class Section(NamedTuple):
    diskgroups: Mapping[str, Diskgroup]
    found_deprecated_agent_output: bool = False


def _is_deprecated_oracle_asm_plugin_from_1_2_6(repair_time: str, num_disks: str) -> bool:
    """
    >>> _is_deprecated_oracle_asm_plugin_from_1_2_6('N', 'DATAC1/')
    True
    >>> _is_deprecated_oracle_asm_plugin_from_1_2_6('', '2')
    False
    """
    return not num_disks.isnumeric() or repair_time == "N"


def _try_parse_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except ValueError:
        return None


def parse_oracle_asm_diskgroup(  # pylint: disable=too-many-branches
    string_table: StringTable,
) -> Section:
    tmp_section: Dict[str, Diskgroup] = {}
    found_deprecated_agent_output = False

    for line in string_table:
        # Filuregroups are usually REGULAR.
        # Other types are possible from Version 11.2 onwards
        fg_type = "REGULAR"

        try:
            dgstate = line[0]
        except IndexError:
            continue

        if dgstate == "DISMOUNTED":
            dgtype = None
            index = 1

            if len(line) == 14:

                # work arround for new format with '|'
                # => we get a clean output from agent. no need to correct it with index
                index = 2

        elif dgstate == "MOUNTED":
            dgtype = line[1]
            index = 2

        else:
            continue

        stripped_line = line[index:]

        if len(stripped_line) == 10:
            (
                _rebal,
                _sector,
                _block,
                _au,
                total_mb,
                free_mb,
                req_mir_free_mb,
                _usable_file_mb,
                offline_disks,
                dgname,
            ) = stripped_line
            voting_files = "N"

        elif len(stripped_line) == 11:
            (
                _rebal,
                _sector,
                _block,
                _au,
                total_mb,
                free_mb,
                req_mir_free_mb,
                _usable_file_mb,
                offline_disks,
                voting_files,
                dgname,
            ) = stripped_line

        elif len(stripped_line) == 12:
            # new format with Failuregroup details
            (
                dgname,
                _block,
                _au,
                req_mir_free_mb,
                total_mb,
                free_mb,
                fg_name,
                voting_files,
                fg_type,
                offline_disks,
                fg_min_repair_time,
                fg_disks,
            ) = stripped_line

            if _is_deprecated_oracle_asm_plugin_from_1_2_6(fg_min_repair_time, fg_disks):
                # We run in here in case the deprecated plugin "mk_oracle_asm" from 1.2.6 is still
                # executed on the server. Ignore this data but tell it later to the user
                found_deprecated_agent_output = True

                # We could also break here and stop parsing data, but we continue in order not to
                # ignore data from newer agent plugin.
                # And yes, the order should be deterministic but who knows... like this, we're safe.
                continue

        else:
            continue

        dgname = dgname.rstrip("/")
        if len(stripped_line) != 12:

            # old format without fg data
            tmp_section.setdefault(
                dgname,
                Diskgroup(
                    dgstate=dgstate,
                    dgtype=dgtype,
                    total_mb=int(total_mb),
                    free_mb=int(free_mb),
                    req_mir_free_mb=int(req_mir_free_mb),
                    offline_disks=int(offline_disks),
                    voting_files=voting_files,
                    fail_groups=[],
                ),
            )

        else:

            failgroups: List[Failgroup] = []
            if dgstate == "MOUNTED":
                this_failgroup = Failgroup(
                    fg_name=fg_name,
                    fg_voting_files=voting_files,
                    fg_type=fg_type,
                    fg_free_mb=int(free_mb),
                    fg_total_mb=int(total_mb),
                    fg_disks=int(fg_disks),
                    fg_min_repair_time=int(fg_min_repair_time),
                )

                if dgname in tmp_section:

                    # append entry to failgroups
                    tmp = tmp_section[dgname].fail_groups
                    failgroups = tmp
                    failgroups.append(this_failgroup)

                else:
                    failgroups.append(this_failgroup)

            tmp_section.setdefault(
                dgname,
                Diskgroup(
                    dgstate=dgstate,
                    dgtype=dgtype,
                    total_mb=_try_parse_int(total_mb),
                    free_mb=_try_parse_int(free_mb),
                    req_mir_free_mb=int(req_mir_free_mb),
                    offline_disks=int(offline_disks),
                    voting_files=voting_files,
                    fail_groups=failgroups,
                ),
            )
    return Section(
        found_deprecated_agent_output=found_deprecated_agent_output, diskgroups={**tmp_section}
    )


register.agent_section(
    name="oracle_asm_diskgroup",
    parse_function=parse_oracle_asm_diskgroup,
)


def discovery_oracle_asm_diskgroup(section: Section) -> DiscoveryResult:
    for asm_diskgroup_name, attrs in section.diskgroups.items():
        if attrs.dgstate in ["MOUNTED", "DISMOUNTED"]:
            yield Service(item=asm_diskgroup_name)


def check_oracle_asm_diskgroup(  # pylint: disable=too-many-branches
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    if item not in section.diskgroups:
        # In case of missing information we assume that the ASM-Instance is
        # checked at a later time.
        # This reduce false notifications for not running ASM-Instances
        yield IgnoreResults("Diskgroup %s not found" % item)
        return

    data = section.diskgroups[item]

    if section.found_deprecated_agent_output:
        yield Result(
            state=state.WARN,
            summary="The deprecated Oracle Agent Plugin 'mk_oracle_asm' from Checkmk Version 1.2.6 "
            "is still executed on this host. The section 'oracle_asm_diskgroup' is now "
            "generated by the plugin 'mk_oracle'. Please remove the deprecated Plugin",
        )

    dgstate = data.dgstate
    dgtype = data.dgtype
    total_mb = 0
    free_mb = 0
    req_mir_free_mb = data.req_mir_free_mb
    offline_disks = data.offline_disks
    voting_files = data.voting_files

    if dgstate == "DISMOUNTED":
        yield Result(state=state.CRIT, summary="Diskgroup dismounted")
        return

    add_text = ""

    if data.fail_groups:

        # => New agentformat!

        fg_count = len(data.fail_groups)

        # dg_sizefactor depends on dg_type and fg_count

        if dgtype == "EXTERN":
            dg_sizefactor = 1

        elif dgtype == "NORMAL":

            if fg_count == 1:

                # we miss the 2nd required fg.
                # => factor is down from 2 to 1
                dg_sizefactor = 1

            else:
                dg_sizefactor = 2

        elif dgtype == "HIGH":

            if fg_count <= 3:

                # we are under the minimum required fgs for the dg.
                dg_sizefactor = fg_count

            else:
                dg_sizefactor = 3

        dg_votecount = 0
        dg_disks = 0

        # 100 days => no disk in repair time
        dg_min_repair = 100 * 24 * 60 * 60

        fg_uniform_size = True
        last_total = -1

        # check for some details against the failure groups
        for fgitem in data.fail_groups:

            # count number of disks over all fgs
            dg_disks += fgitem.fg_disks

            if fgitem.fg_voting_files == "Y":
                dg_votecount += 1

            dg_min_repair = min(dg_min_repair, fgitem.fg_min_repair_time)

            # this is the size without the dg_sizefactor
            free_mb += fgitem.fg_free_mb
            total_mb += fgitem.fg_total_mb

            # check uniform size of failure-groups. 5% difference is ok
            if last_total == -1:
                last_total = fgitem.fg_total_mb

            # ignore failure-groups with Voting-Files
            # => exadata use special failure-groups for Voting with different size
            # => Ignore QUORUM failure-groups. They cannot store regular data!
            elif (
                fgitem.fg_type == "REGULAR"
                and fgitem.fg_voting_files == "N"
                and fgitem.fg_total_mb * 0.95 <= last_total >= fgitem.fg_total_mb * 1.05
            ):
                fg_uniform_size = False

    else:

        # work on old agentformat

        # We're in state MOUNTED so we *should* have those values
        if not (data.total_mb and data.free_mb):
            raise ValueError("Expected values for Total and Free MB but received None.")
        total_mb = data.total_mb
        free_mb = data.free_mb

        # => some estimates with possible errors are expected. Use new agentformat for correct results
        if dgtype == "EXTERN":
            dg_sizefactor = 1

        elif dgtype in ("NORMAL", "HIGH"):

            # old plugin format has limitations when NORMAL or HIGH redundancy is found
            add_text += ", old plugin data, possible wrong used and free space"

            if dgtype == "NORMAL":
                if voting_files == "Y":
                    # NORMAL Redundancy Disk-Groups with Voting requires 3 Failgroups
                    dg_sizefactor = 3
                else:
                    dg_sizefactor = 2

            elif dgtype == "HIGH":
                if voting_files == "Y":
                    # HIGH Redundancy Disk-Groups with Voting requires 5 Failgroups
                    dg_sizefactor = 5
                else:
                    dg_sizefactor = 3

    total_mb = total_mb // dg_sizefactor
    free_space_mb = free_mb // dg_sizefactor

    if params.get("req_mir_free"):
        # requirred mirror free space could be negative!
        req_mir_free_mb = max(req_mir_free_mb, 0)

        add_text = ", required mirror free space used"

    result_list = list(
        df_check_filesystem_single(
            value_store=get_value_store(),
            mountpoint=item,
            size_mb=float(total_mb),
            avail_mb=free_space_mb,
            reserved_mb=0,
            inodes_total=None,
            inodes_avail=None,
            params=params,
        ),
    )
    yield from result_list
    aggregated_state = state.worst(
        *[elem.state for elem in result_list if isinstance(elem, Result)]
    )

    infotext = ""
    if dgtype is not None:
        infotext += "%s redundancy" % dgtype.lower()

        if data.fail_groups:

            # => New agentformat!

            infotext += ", %i disks" % dg_disks

            if dgtype != "EXTERN":

                # EXTERN Redundancy has only 1 FG. => useless information
                infotext += " in %i failgroups" % fg_count

            if not fg_uniform_size:

                infotext += ", failgroups with unequal size"

            if dg_votecount > 0:
                votemarker = ""
                if dgtype == "HIGH" and dg_votecount < 5:

                    # HIGH redundancy allows a loss of 2 votes. => 1 is only a WARN
                    aggregated_state = state.best(aggregated_state, state.WARN)
                    votemarker = ", not enough votings, 5 expected (!)"

                elif (dgtype == "NORMAL" and dg_votecount < 3) or (
                    dgtype == "HIGH" and dg_votecount < 4
                ):

                    aggregated_state = state.CRIT
                    votemarker = ", not enough votings, 3 expected (!!)"

                infotext += ", %i votings" % dg_votecount
                infotext += votemarker

            if dg_min_repair < 8640000:

                # no need to set a state due to offline disks
                infotext += ", disk repair timer for offline disks at %s (!)" % render.timespan(
                    dg_min_repair
                )

    infotext += add_text

    if offline_disks > 0:
        aggregated_state = state.CRIT
        infotext += ", %d Offline disks found(!!)" % offline_disks

    yield Result(state=aggregated_state, summary=infotext)


def cluster_check_oracle_asm_diskgroup(
    item: str, params: Mapping[str, Any], section: Mapping[str, Optional[Section]]
) -> CheckResult:

    # only use data from 1. node in agent output
    # => later calculation of DG size is much easier

    # todo: RAC with mounted DG on 2 of 3 nodes. => Problem when first_node has the DISMOUNTED DG
    #       the old agent formats without '|' are really painful here, because we need the DG at this
    #       point to find a possible node with mounted DG.

    for node_section in section.values():
        if node_section is None:
            continue
        yield from check_oracle_asm_diskgroup(item, params, node_section)
        return


register.check_plugin(
    name="oracle_asm_diskgroup",
    service_name="ASM Diskgroup %s",
    discovery_function=discovery_oracle_asm_diskgroup,
    check_function=check_oracle_asm_diskgroup,
    check_default_parameters=ASM_DISKGROUP_DEFAULT_LEVELS,
    check_ruleset_name="asm_diskgroup",
    cluster_check_function=cluster_check_oracle_asm_diskgroup,
)
