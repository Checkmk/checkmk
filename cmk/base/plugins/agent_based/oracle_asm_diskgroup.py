#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import (
    Any,
    Dict,
    Union,
    List,
    Mapping,
)
from .agent_based_api.v1 import (
    register,
    Service,
    Result,
    IgnoreResults,
    State as state,
    get_value_store,
    render,
)

from .agent_based_api.v1.type_defs import (
    DiscoveryResult,
    AgentStringTable,
    CheckResult,
    Parameters,
)
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


def parse_oracle_asm_diskgroup(string_table: AgentStringTable):
    section: Dict[str, Dict[str, Union[str, List, None]]] = {}

    for line in string_table:
        # Filuregroups are usually REGULAR.
        # Other types are possible from Version 11.2 onwards
        fg_type = 'REGULAR'

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
            _rebal, _sector, _block, _au, total_mb, free_mb, req_mir_free_mb, \
                _usable_file_mb, offline_disks, dgname = stripped_line
            voting_files = "N"

        elif len(stripped_line) == 11:
            _rebal, _sector, _block, _au, total_mb, free_mb, req_mir_free_mb, \
                _usable_file_mb, offline_disks, voting_files, dgname = stripped_line

        elif len(stripped_line) == 12:
            # new format with Failuregroup details
            dgname, _block, _au, req_mir_free_mb, total_mb, free_mb, \
                fg_name, voting_files, fg_type, offline_disks, fg_min_repair_time, fg_disks = stripped_line

        else:
            continue

        dgname = dgname.rstrip("/")

        if len(stripped_line) != 12:

            # old format without fg data
            section.setdefault(
                dgname, {
                    "dgstate": dgstate,
                    "dgtype": dgtype,
                    "total_mb": total_mb,
                    "free_mb": free_mb,
                    "req_mir_free_mb": req_mir_free_mb,
                    "offline_disks": offline_disks,
                    "voting_files": voting_files,
                })

        else:

            if dgstate == "DISMOUNTED":

                # we don't have any detail data for the fg
                # => add dummy fg for format detection in check
                this_failgroup = {}

            else:

                this_failgroup = {
                    "fg_name": fg_name,
                    "fg_voting_files": voting_files,
                    "fg_type": fg_type,
                    "fg_free_mb": int(free_mb),
                    "fg_total_mb": int(total_mb),
                    "fg_disks": int(fg_disks),
                    "fg_min_repair_time": int(fg_min_repair_time),
                }

            failgroups: List[Dict] = []

            if dgname in section:

                # append entry to failgroups
                tmp = section[dgname]["failgroups"]
                assert isinstance(tmp, list)
                failgroups = tmp
                failgroups.append(this_failgroup)

            else:
                failgroups.append(this_failgroup)

            section.setdefault(
                dgname, {
                    "dgstate": dgstate,
                    "dgtype": dgtype,
                    "total_mb": total_mb,
                    "free_mb": free_mb,
                    "req_mir_free_mb": req_mir_free_mb,
                    "offline_disks": offline_disks,
                    "voting_files": voting_files,
                    "failgroups": failgroups,
                })
    return section


register.agent_section(
    name="oracle_asm_diskgroup",
    parse_function=parse_oracle_asm_diskgroup,
)


def discovery_oracle_asm_diskgroup(section: Dict[str, Any]) -> DiscoveryResult:
    for asm_diskgroup_name, attrs in section.items():
        if attrs["dgstate"] in ["MOUNTED", "DISMOUNTED"]:
            yield Service(item=asm_diskgroup_name)


def check_oracle_asm_diskgroup(item: str, params: Parameters, section: Dict[str,
                                                                            Any]) -> CheckResult:
    if item not in section:
        # In case of missing information we assume that the ASM-Instance is
        # checked at a later time.
        # This reduce false notifications for not running ASM-Instances
        yield IgnoreResults("Diskgroup %s not found" % item)
        return

    data = section[item]

    dgstate = data["dgstate"]
    dgtype = data["dgtype"]
    total_mb = 0
    free_mb = 0
    req_mir_free_mb = data["req_mir_free_mb"]
    offline_disks = data["offline_disks"]
    voting_files = data["voting_files"]

    if dgstate == "DISMOUNTED":
        yield Result(state=state.CRIT, summary="Diskgroup dismounted")
        return

    add_text = ""

    if "failgroups" in data:

        # => New agentformat!

        fg_count = len(data["failgroups"])

        # dg_sizefactor depends on dg_type and fg_count

        if dgtype == 'EXTERN':
            dg_sizefactor = 1

        elif dgtype == 'NORMAL':

            if fg_count == 1:

                # we miss the 2nd requirred fg.
                # => factor is down from 2 to 1
                dg_sizefactor = 1

            else:
                dg_sizefactor = 2

        elif dgtype == 'HIGH':

            if fg_count <= 3:

                # we are under the minimum requirred fgs for the dg.
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
        for fgitem in data["failgroups"]:

            # count number of disks over all fgs
            dg_disks += fgitem["fg_disks"]

            if fgitem['fg_voting_files'] == 'Y':
                dg_votecount += 1

            dg_min_repair = min(dg_min_repair, fgitem['fg_min_repair_time'])

            # this is the size without the dg_sizefactor
            free_mb += fgitem["fg_free_mb"]
            total_mb += fgitem["fg_total_mb"]

            # check uniform size of failure-groups. 5% difference is ok
            if last_total == -1:
                last_total = fgitem["fg_total_mb"]

            # ignore failure-groups with Voting-Files
            # => exadata use special failure-groups for Voting with different size
            # => Ignore QUORUM failure-groups. They cannot store regular data!
            elif fgitem['fg_type'] == 'REGULAR' and fgitem['fg_voting_files'] == 'N' \
                   and fgitem["fg_total_mb"]*0.95 <= last_total >= fgitem["fg_total_mb"]*1.05:
                fg_uniform_size = False

    else:

        # work on old agentformat

        total_mb = data["total_mb"]
        free_mb = data["free_mb"]

        # => some estimates with possible errors are expected. Use new agentformat for correct results
        if dgtype == 'EXTERN':
            dg_sizefactor = 1

        elif dgtype in ('NORMAL', 'HIGH'):

            # old plugin format has limitations when NORMAL or HIGH redundancy is found
            add_text += ', old plugin data, possible wrong used and free space'

            if dgtype == 'NORMAL':
                if voting_files == 'Y':
                    # NORMAL Redundancy Disk-Groups with Voting requires 3 Failgroups
                    dg_sizefactor = 3
                else:
                    dg_sizefactor = 2

            elif dgtype == 'HIGH':
                if voting_files == 'Y':
                    # HIGH Redundancy Disk-Groups with Voting requires 5 Failgroups
                    dg_sizefactor = 5
                else:
                    dg_sizefactor = 3

    total_mb = int(total_mb) // dg_sizefactor
    free_space_mb = int(free_mb) // dg_sizefactor

    if params.get('req_mir_free'):
        req_mir_free_mb = int(req_mir_free_mb)
        if req_mir_free_mb < 0:
            # requirred mirror free space could be negative!
            req_mir_free_mb = 0

        add_text = ', required mirror free space used'

    result_list = list(
        df_check_filesystem_single(value_store=get_value_store(),
                                   check="oracle_asm_diskgroup",
                                   mountpoint=item,
                                   size_mb=float(total_mb),
                                   avail_mb=free_space_mb,
                                   reserved_mb=0,
                                   inodes_total=None,
                                   inodes_avail=None,
                                   params=params))
    yield from result_list
    aggregated_state = state.worst(
        *[elem.state for elem in result_list if isinstance(elem, Result)])

    infotext = ""
    if dgtype is not None:
        infotext += '%s redundancy' % dgtype.lower()

        if "failgroups" in data:

            # => New agentformat!

            infotext += ', %i disks' % dg_disks

            if dgtype != 'EXTERN':

                # EXTERN Redundancy has only 1 FG. => useless information
                infotext += ' in %i failgroups' % fg_count

            if not fg_uniform_size:

                infotext += ', failgroups with unequal size'

            if dg_votecount > 0:
                votemarker = ''
                if (dgtype == 'HIGH' and dg_votecount < 5):

                    # HIGH redundancy allows a loss of 2 votes. => 1 is only a WARN
                    aggregated_state = state.best(aggregated_state, state.WARN)
                    votemarker = ', not enough votings, 5 expected (!)'

                elif (dgtype == 'NORMAL' and dg_votecount < 3) \
                  or (dgtype == 'HIGH' and dg_votecount < 4):

                    aggregated_state = state.CRIT
                    votemarker = ', not enough votings, 3 expected (!!)'

                infotext += ', %i votings' % dg_votecount
                infotext += votemarker

            if dg_min_repair < 8640000:

                # no need to set a state due to offline disks
                infotext += ', disk repair timer for offline disks at %s (!)' % render.timespan(
                    dg_min_repair)

    infotext += add_text

    offline_disks = int(offline_disks)
    if offline_disks > 0:
        aggregated_state = state.CRIT
        infotext += ', %d Offline disks found(!!)' % offline_disks

    yield Result(state=aggregated_state, summary=infotext)


def cluster_check_oracle_asm_diskgroup(item: str, params: Parameters,
                                       section: Mapping[str, Dict[str, Any]]) -> CheckResult:

    # only use data from 1. node in agent output
    # => later calculation of DG size is much easier

    # todo: RAC with mounted DG on 2 of 3 nodes. => Problem when first_node has the DISMOUNTED DG
    #       the old agent formats without '|' are really painful here, because we need the DG at this
    #       point to find a possible node with mounted DG.

    for node_section in section.values():
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
