#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Dict, List, Mapping, NamedTuple, Optional, Sequence, Tuple

from .agent_based_api.v1 import get_value_store, regex, register, Result, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_LEVELS

_MEGA = 1024.0**2


class Quota(NamedTuple):
    name: str
    fs: str
    limit: str
    used: int


class Section(NamedTuple):
    fs_sizes: Dict[str, int]
    quotas: List[Quota]


def parse_vnx_quotas(string_table: StringTable) -> Section:
    """
    >>> from pprint import pprint as pp
    >>> section = parse_vnx_quotas([
    ...     ['[[[fs]]]'],
    ...     ['fv51_01', '806636,806636,0,0,825996248'],
    ...     ['fv51_02', '100774,100773,0,0,103193048'],
    ...     ['[[[quotas]]]'],
    ...     ['vdmfv51', 'fv51_01', '/hmtest', '0', '0'],
    ...     ['vdmfv51', 'fv51_01', '/BOEINT', '0', '1048576'],
    ... ])
    >>> pp(section.fs_sizes)
    {'fv51_01': 845820157952, 'fv51_02': 105669681152}
    >>> pp(section.quotas)
    [Quota(name='vdmfv51 /hmtest', fs='fv51_01', limit='0', used=0),
     Quota(name='vdmfv51 /BOEINT', fs='fv51_01', limit='1048576', used=0)]
    """

    section = Section(fs_sizes={}, quotas=[])
    subsection = None
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            subsection = line[0][3:-3]
            continue

        if subsection == "fs":
            fs_name = line[0].strip()
            fs_total_bytes = int(line[1].split(",")[4]) * 1024
            section.fs_sizes[fs_name] = fs_total_bytes

        elif subsection == "quotas":
            if len(line) != 5:
                continue

            dms, fs, mp, used_str, limit_str = line
            name = "%s %s" % (dms.strip(), mp.strip())
            section.quotas.append(
                Quota(
                    name=name,
                    fs=fs.strip(),
                    limit=limit_str,
                    used=int(used_str) * 1024,
                )
            )

    return section


register.agent_section(
    name="vnx_quotas",
    parse_function=parse_vnx_quotas,
)


def vnx_quotas_renaming(name: str, mappings: Sequence[Tuple[str, str]]) -> str:
    for match, substitution in mappings:
        if match.startswith("~"):
            num_perc_s = substitution.count("%s")
            reg = regex(match[1:])
            matchobj = reg.match(name)
            if matchobj:
                matches = [g and g or "" for g in matchobj.groups()]
                for num, group in enumerate(matches, start=1):
                    substitution = substitution.replace("%%%d" % num, group)
                substitution = substitution % tuple(matches[:num_perc_s])
                return substitution

        elif name == match:
            return substitution

    return name


def discover_vnx_quotas(params: List[Mapping[str, Any]], section: Section) -> DiscoveryResult:
    for quota in section.quotas:
        dms, mpt = quota.name.split(" ")
        if params and params[0]:
            dms = vnx_quotas_renaming(dms, params[0]["dms_names"])
            mpt = vnx_quotas_renaming(mpt, params[0]["mp_names"])
        yield Service(item="%s %s" % (dms, mpt), parameters={"pattern": quota.name})


def _get_quota(item: str, params: Mapping[str, Any], section: Section) -> Optional[Quota]:
    for quota in section.quotas:
        if quota.name in (item, params["pattern"]):
            return quota
    return None


def check_vnx_quotas(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    quota = _get_quota(item, params, section)
    if quota is None:
        return

    # Special case as customer said:
    # if BlockHardLimit == "0" or "NoLimit" then we take filesystem size
    use_fs = quota.limit in ("0", "NoLimit") and quota.fs in section.fs_sizes
    size_mb = section.fs_sizes[quota.fs] / _MEGA if use_fs else int(quota.limit) / 1024.0
    available_mb = size_mb - quota.used / _MEGA

    for element in df_check_filesystem_single(
        value_store=get_value_store(),
        mountpoint=item,
        size_mb=size_mb,
        avail_mb=available_mb,
        reserved_mb=0.0,
        inodes_total=None,
        inodes_avail=None,
        params=params,
        this_time=None,
    ):
        if not isinstance(element, Result):
            yield element
        else:
            yield Result(
                state=element.state,
                summary=element.summary.replace("filesystem", "quota"),
                details=element.details.replace("filesystem", "quota"),
            )


register.check_plugin(
    name="vnx_quotas",
    service_name="VNX Quota %s",
    discovery_function=discover_vnx_quotas,
    discovery_default_parameters={},
    discovery_ruleset_name="discovery_rules_vnx_quotas",
    discovery_ruleset_type=register.RuleSetType.ALL,
    check_function=check_vnx_quotas,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_LEVELS,
)
