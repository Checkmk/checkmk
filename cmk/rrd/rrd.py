#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
RRD creation is taking place via two entry points
1. called via CMC in keepalive mode
2. called via cmk --convert-rrds
This module does the following operations
- Creating new RRDs or extending existing RRDs with new metrics
- Splitting up old-school PNP SINGLE RRDs into PNP MULTIPLE
- Converting existing RRDs in format PNP MULTIPLE or CMC SINGLE to
  match a changed RRA configuration
- Converting existing RRDs in formatn PNP MULTIPLE into CMC SINGLE
"""

import os
import select
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import assert_never, cast, Literal, NewType, Protocol, Self, TypedDict

# NOTE: rrdtool is missing type hints
import rrdtool  # type: ignore[import-not-found]

import cmk.ccc.debug
import cmk.ccc.version as cmk_version
from cmk.ccc.crash_reporting import (
    ABCCrashReport,
    BaseDetails,
    crash_report_registry,
    CrashInfo,
    CrashReportStore,
    VersionInfo,
)

import cmk.utils
import cmk.utils.paths
from cmk.utils import tty
from cmk.utils.hostaddress import HostName
from cmk.utils.log import console
from cmk.utils.metrics import MetricName
from cmk.utils.servicename import ServiceName

_Seconds = NewType("_Seconds", int)

_RRDFormat = Literal["cmc_single", "pnp_multiple"]
_RRDHeartbeat = NewType("_RRDHeartbeat", int)
_RRAConfig = list[str]
_RRDFileConfigWithFormat = tuple[_RRDFormat, _RRAConfig, _Seconds, _RRDHeartbeat]
_RRDInfoValue = str | list[str]
RRDInfo = dict[str, _RRDInfoValue]
_RRDServiceName = str

_default_rrd_format: _RRDFormat = "pnp_multiple"


def _rrd_pnp_host_dir(hostname: HostName) -> str:
    # We need /opt here because of bug in rrdcached
    return str(cmk.utils.paths.rrd_multiple_dir / cmk.utils.pnp_cleanup(hostname))


class RRDObjectConfig(TypedDict):
    """RRDObjectConfig
    This typing might not be complete or even wrong, feel free to improve"""

    cfs: Iterable[Literal["MIN", "MAX", "AVERAGE"]]  # conceptually a Set[Literal[...]]
    rras: list[tuple[float, int, int]]
    step: int
    format: Literal["pnp_multiple", "cmc_single"]


class _RRDConfig(Protocol):
    def rrd_config(self, hostname: HostName) -> RRDObjectConfig | None: ...

    def rrd_config_of_service(
        self, hostname: HostName, description: ServiceName
    ) -> RRDObjectConfig | None: ...

    def cmc_log_rrdcreation(self) -> Literal["terse", "full"] | None: ...


@dataclass(frozen=True)
class RRDSpec:
    format: _RRDFormat
    host: HostName
    service: _RRDServiceName
    metrics: Sequence[tuple[str, str | None]]

    @property
    def metric_names(self) -> Sequence[str]:
        return tuple(e[0] for e in self.metrics)

    @classmethod
    def parse(cls, spec: str) -> Self:
        def parse_rrd_format(fmt: str) -> _RRDFormat:
            if fmt not in ("cmc_single", "pnp_multiple"):
                raise ValueError(fmt)
            return cast(_RRDFormat, fmt)

        parts = spec.split(";")
        format_ = parse_rrd_format(parts[0])
        host = HostName(parts[1])
        if len(parts) % 2 == 1:  # service
            service = parts[2]
            metric_specs = parts[3:]
        else:  # host
            service = "_HOST_"
            metric_specs = parts[2:]

        metrics = list(zip(metric_specs[::2], metric_specs[1::2]))
        return cls(format_, host, service, metrics)


rra_default_config = [
    "RRA:AVERAGE:0.50:1:2880",
    "RRA:AVERAGE:0.50:5:2880",
    "RRA:AVERAGE:0.50:30:4320",
    "RRA:AVERAGE:0.50:360:5840",
    "RRA:MAX:0.50:1:2880",
    "RRA:MAX:0.50:5:2880",
    "RRA:MAX:0.50:30:4320",
    "RRA:MAX:0.50:360:5840",
    "RRA:MIN:0.50:1:2880",
    "RRA:MIN:0.50:5:2880",
    "RRA:MIN:0.50:30:4320",
    "RRA:MIN:0.50:360:5840",
]

rrd_heartbeat = 8460


def _get_rrd_conf(
    config: _RRDConfig, hostname: HostName, servicedesc: _RRDServiceName = "_HOST_"
) -> _RRDFileConfigWithFormat:
    if servicedesc == "_HOST_":
        rrdconf: RRDObjectConfig | None = config.rrd_config(hostname)
    else:
        rrdconf = config.rrd_config_of_service(hostname, servicedesc)

    if rrdconf is not None:
        rra_config = sorted(
            [
                f"RRA:{cf}:{xfs / 100.0:.2f}:{step}:{rows}"
                for xfs, step, rows in rrdconf["rras"]
                for cf in rrdconf["cfs"]
            ]
        )
        step = rrdconf["step"]
        rrd_format = rrdconf.get("format", _default_rrd_format)
    else:
        rra_config = sorted(rra_default_config)
        step = 60
        rrd_format = _default_rrd_format

    return rrd_format, rra_config, _Seconds(step), _RRDHeartbeat(rrd_heartbeat)


def _rrd_cmc_host_dir(hostname: HostName) -> str:
    # We need /opt here because of bug in rrdcached
    return str(cmk.utils.paths.rrd_single_dir / cmk.utils.pnp_cleanup(hostname))


def _read_existing_metrics(info_file_path: str) -> list[MetricName]:
    metrics = _parse_cmc_rrd_info(info_file_path)["metrics"]
    if not isinstance(metrics, list):
        raise TypeError()
    return metrics


def _parse_cmc_rrd_info(info_file_path: str) -> RRDInfo:
    info: RRDInfo = {}
    try:
        with open(info_file_path) as fid:
            for line in fid:
                keyword, value = line.strip().split(None, 1)
                if keyword == "METRICS":
                    store_value: _RRDInfoValue = value.split(";")
                else:
                    store_value = value

                info[keyword.lower()] = store_value

        return info

    except Exception as e:
        if cmk.ccc.debug.enabled():
            raise
        raise Exception(f"Invalid RRD info file {info_file_path}: {e}")


def _create_rrd(config: _RRDConfig, spec: RRDSpec, log: Callable[[str], None]) -> str:
    """Create a new RRD. Automatically reuses data from an existing RRD if the
    type is CMC SINGLE. This mode is for extending existing RRDs by new metrics."""
    # We get the configured rrd_format here as well. But we rather trust what CMC
    # specifies.
    _unused_configured_rrd_format, rra_config, step, heartbeat = _get_rrd_conf(
        config, spec.host, spec.service
    )

    match spec.format:
        case "pnp_multiple":
            host_dir = _rrd_pnp_host_dir(spec.host)
            base_file_name = (
                host_dir
                + "/"
                + cmk.utils.pnp_cleanup(spec.service)
                + "_"
                + cmk.utils.pnp_cleanup(spec.metric_names[0])
            )
        case "cmc_single":
            host_dir = _rrd_cmc_host_dir(spec.host)
            base_file_name = host_dir + "/" + cmk.utils.pnp_cleanup(spec.service)
        case _:
            assert_never(spec.format)

    rrd_file_name = base_file_name + ".rrd"

    migration_arguments = []  # List[str]
    migration_mapping = {}
    if os.path.exists(rrd_file_name):
        if spec.format == "pnp_multiple":
            raise Exception("Tried to create %s, but this RRD exists." % rrd_file_name)

        # Need to migrate data from existing RRD
        existing_metrics = _read_existing_metrics(base_file_name + ".info")
        migration_arguments = ["--source", rrd_file_name]
        for nr, varname in enumerate(existing_metrics, 1):
            migration_mapping[varname] = nr

    if not os.path.exists(host_dir):
        os.makedirs(host_dir)

    if config.cmc_log_rrdcreation():
        log(f"Creating {rrd_file_name}")
        if config.cmc_log_rrdcreation() == "full":
            for entry in rra_config:
                log(f"    {entry}")

    args = [rrd_file_name, "--step", str(step)]
    for nr, varname in enumerate(spec.metric_names, 1):
        if varname in migration_mapping:
            source_spec = "=%d" % migration_mapping[varname]
        else:
            source_spec = ""
        args.append(f"DS:{nr}{source_spec}:GAUGE:{heartbeat}:U:U")
    args += rra_config
    args = migration_arguments + args

    # Note: rrdtool.create bails out with a Bus error if the disk is full. There
    # is no way to handle this here. Or can we catch the signal 6? In any case it does not
    # make sense to check the size of the RRD for 0 after this command since our process
    # will not exist anymore by then...
    rrdtool.create(*args)

    if spec.format == "cmc_single":
        _create_cmc_rrd_info_file(spec)

    return rrd_file_name


# Create information file for CMC format RRDs. Problem is that RRD
# limits variable names to 19 characters and to just alphanumeric
# characters. We cannot savely put our variablenames into the RRDs.
# So we do it like PNP and use 1, 2, 3... as DS names and keep the
# actual real names in a separate file with the extension ".info"
def _create_cmc_rrd_info_file(spec: RRDSpec) -> None:
    base_file_name = _rrd_cmc_host_dir(spec.host) + "/" + cmk.utils.pnp_cleanup(spec.service)
    with open(base_file_name + ".info", "w") as fid:
        fid.write(
            f"HOST {spec.host}\nSERVICE {spec.service}\nMETRICS {';'.join(spec.metric_names)}\n"
        )


####################################################################################################
# CONVERT RRDS
####################################################################################################

_RRDFileConfig = tuple[_RRAConfig, _Seconds, _RRDHeartbeat]
_RRDServices = Mapping[_RRDServiceName, list[_RRDFormat]]
RRDXMLInfo = dict


def convert_rrds_of_host(
    config: _RRDConfig, hostname: HostName, *, split: bool, delete: bool
) -> None:
    console.verbose(f"{tty.bold}{tty.yellow}{hostname}{tty.normal}:")

    try:
        existing_rrds = _find_host_rrd_services(hostname)
        _convert_cmc_versus_pnp(config, hostname, existing_rrds, delete=delete)
        _convert_pnp_rrds(config, hostname, existing_rrds, split=split)
        _convert_cmc_rrds(config, hostname, existing_rrds)
    except Exception as e:
        if cmk.ccc.debug.enabled():
            raise
        console.verbose(f"  HOST: {hostname}", file=sys.stderr)
        console.error(f"      {tty.red}{tty.bold}ERROR: {e}{tty.normal}", file=sys.stderr)

    console.verbose("")


def _find_host_rrd_services(hostname: HostName) -> _RRDServices:
    rrd_services: dict[_RRDServiceName, list[_RRDFormat]] = {}
    for service in _find_pnp_rrds(hostname):
        rrd_services.setdefault(service, []).append("pnp_multiple")
    for service in _find_cmc_rrds(hostname):
        rrd_services.setdefault(service, []).append("cmc_single")
    return rrd_services


def _convert_cmc_versus_pnp(
    config: _RRDConfig,
    hostname: HostName,
    existing_rrds: _RRDServices,
    *,
    delete: bool,
) -> None:
    # Find services with RRDs in the two possible formats "cmc" and "pnp". "_HOST_" means
    # host metrics.
    for servicedesc, existing_rrd_formats in existing_rrds.items():
        target_rrdconf = _get_rrd_conf(config, hostname, servicedesc)
        target_rrd_format = target_rrdconf[0]
        if target_rrd_format not in existing_rrd_formats:
            if target_rrd_format == "pnp_multiple":
                _write_line(
                    f"WARNING: Converting RRD format CMC into PNP not implemented ({hostname}/{servicedesc})"
                )
                # convert_cmc_to_pnp(hostname, servicedesc)
            else:
                _convert_pnp_to_cmc(config, hostname, servicedesc)
                existing_rrd_formats.append(target_rrd_format)

        if len(existing_rrd_formats) > 1:
            if delete:
                for rrd_format in existing_rrd_formats:
                    if rrd_format != target_rrd_format:
                        _delete_rrds(hostname, servicedesc, rrd_format)
                existing_rrd_formats[:] = [target_rrd_format]
            else:
                _write_line(
                    f"WARNING: Duplicate RRDs for {hostname}/{servicedesc}. Use --delete-rrds for cleanup."
                )


def _convert_pnp_rrds(
    config: _RRDConfig,
    hostname: HostName,
    existing_rrds: _RRDServices,
    *,
    split: bool,
) -> None:
    host_dir = _rrd_pnp_host_dir(hostname)
    for servicedesc, existing_rrd_formats in existing_rrds.items():
        if "pnp_multiple" in existing_rrd_formats:
            console.verbose(f"  {servicedesc} ({tty.bold}{tty.cyan}PNP{tty.normal})...")
            xmlinfo = _read_pnp_xml_for(hostname, servicedesc)
            target_rrdconf = _get_rrd_conf(config, hostname, servicedesc)[1:]
            _convert_pnp_rrds_of(
                hostname,
                servicedesc,
                host_dir,
                xmlinfo,
                cmk.utils.pnp_cleanup(servicedesc),
                target_rrdconf,
                split=split,
            )


def _convert_cmc_rrds(config: _RRDConfig, hostname: HostName, existing_rrds: _RRDServices) -> None:
    host_dir = _rrd_cmc_host_dir(hostname)
    for servicedesc, existing_rrd_formats in existing_rrds.items():
        if "cmc_single" in existing_rrd_formats:
            console.verbose_no_lf(f"  {servicedesc} ({tty.bold}{tty.bold}CMC{tty.normal})...")
            base_path = host_dir + "/" + cmk.utils.pnp_cleanup(servicedesc)
            existing_metrics = _read_existing_metrics(base_path + ".info")
            target_rrdconf = _get_rrd_conf(config, hostname, servicedesc)[1:]
            rrd_file_path = base_path + ".rrd"
            _convert_cmc_rrd_of(
                config,
                RRDSpec(
                    "cmc_single", hostname, servicedesc, [(name, None) for name in existing_metrics]
                ),
                rrd_file_path,
                target_rrdconf,
            )


def _find_pnp_rrds(hostname: HostName) -> Iterator[_RRDServiceName]:
    host_dir = _rrd_pnp_host_dir(hostname)
    if not os.path.exists(host_dir):
        return

    if os.path.exists(host_dir + "/_HOST_.xml"):
        yield "_HOST_"

    for xml_file in sorted(os.listdir(host_dir)):
        if xml_file.endswith(".xml") and xml_file != "_HOST_.xml":
            xmlinfo = _parse_pnp_xml_file(host_dir + "/" + xml_file)
            servicedesc = xmlinfo["service"]
            yield servicedesc


def _find_cmc_rrds(hostname: HostName) -> Iterator[_RRDServiceName]:
    host_dir = _rrd_cmc_host_dir(hostname)
    if not os.path.exists(host_dir):
        return
    for info_file in sorted(os.listdir(host_dir)):
        if info_file.endswith(".info"):
            service = _parse_cmc_rrd_info(host_dir + "/" + info_file)["service"]
            if not isinstance(service, str):
                raise TypeError()
            yield service


def _convert_pnp_to_cmc(
    config: _RRDConfig, hostname: HostName, servicedesc: _RRDServiceName
) -> None:
    console.verbose_no_lf(
        f"   {servicedesc} {tty.bold}{tty.cyan}PNP{tty.normal} -> {tty.bold}CMC{tty.normal}"
    )

    # We get the configured rrd_format here as well. But we rather trust what CMC
    # specifies.
    rra_config, step, heartbeat = _get_rrd_conf(config, hostname, servicedesc)[1:]

    host_dir = _rrd_cmc_host_dir(hostname)
    base_file_name = host_dir + "/" + cmk.utils.pnp_cleanup(servicedesc)
    rrd_file_name = base_file_name + ".rrd"

    args = [rrd_file_name, "--step", str(step)]
    xml_info = _read_pnp_xml_for(hostname, servicedesc)
    metric_names = []
    for nr, ds in enumerate(xml_info["ds"], 1):
        varname = ds["name"]
        metric_names.append(varname)
        pnp_rrd_filename = (
            _rrd_pnp_host_dir(hostname)
            + "/"
            + cmk.utils.pnp_cleanup(servicedesc)
            + "_"
            + cmk.utils.pnp_cleanup(varname)
            + ".rrd"
        )

        if not os.path.exists(pnp_rrd_filename):
            _write_line(
                f"WARNING: XML {_xml_path_for(hostname, servicedesc)} refers to not existing RRD {pnp_rrd_filename}. "
                "Nothing to convert. Cleanup the XML file manually in case this is OK."
            )
            continue

        args += [
            "--source",
            pnp_rrd_filename,
            f"DS:{nr}=1[{nr}]:GAUGE:{heartbeat}:U:U",
        ]

    if not os.path.exists(host_dir):
        os.makedirs(host_dir)

    args += rra_config

    # Note: rrdtool.create bails out with a Bus error if the disk is full. There
    # is no way to handle this here. Or can we catch the signal 6? In any case it does not
    # make sense to check the size of the RRD for 0 after this command since our process
    # will not exist anymore by then...
    rrdtool.create(*args)

    # Create information file for CMC format RRDs. Problem is that RRD
    # limits variable names to 19 characters and to just alphanumeric
    # characters. We cannot savely put our variablenames into the RRDs.
    # So we do it like PNP and use 1, 2, 3... as DS names and keep the
    # actual real names in a separate file with the extension ".info"
    _create_cmc_rrd_info_file(RRDSpec("cmc_single", hostname, servicedesc, metric_names))
    console.verbose(f"..{tty.bold}{tty.green}converted.{tty.normal}")
    console.debug(f"    (rrdtool create {' '.join(args)})")


def _read_pnp_xml_for(hostname: HostName, servicedesc: _RRDServiceName = "_HOST_") -> RRDXMLInfo:
    return _parse_pnp_xml_file(_xml_path_for(hostname, servicedesc))


def _xml_path_for(hostname: HostName, servicedesc: _RRDServiceName = "_HOST_") -> str:
    host_dir = _rrd_pnp_host_dir(hostname)
    return host_dir + "/" + cmk.utils.pnp_cleanup(servicedesc) + ".xml"


def _parse_pnp_xml_file(xml_path: str) -> RRDXMLInfo:
    root = ET.parse(xml_path).getroot()
    if root is None:
        raise TypeError()

    ds = [
        {
            "name": _text_attr(child, "NAME"),
            "rrdfile": _text_attr(child, "RRDFILE"),
            "ds": _text_attr(child, "DS"),
            "rrd_storage_type": _text_attr(child, "RRD_STORAGE_TYPE"),
        }
        for child in root.iter("DATASOURCE")
    ]

    return {
        "ds": ds,
        "host": _text_attr(root, "NAGIOS_AUTH_HOSTNAME"),
        "service": _text_attr(root, "NAGIOS_AUTH_SERVICEDESC"),
        "rrdfile": _text_attr(root, "NAGIOS_RRDFILE") or "",
    }


def _text_attr(node: ET.Element, attr_name: str) -> str | None:
    attr = node.find(attr_name)
    if attr is None:
        raise AttributeError()
    return attr.text


def _delete_rrds(hostname: HostName, servicedesc: _RRDServiceName, rrd_format: _RRDFormat) -> None:
    def try_delete(path: str) -> None:
        try:
            os.remove(path)
            console.verbose("Deleted {path}")
        except OSError:
            pass

    if rrd_format == "cmc_single":
        host_dir = _rrd_cmc_host_dir(hostname)
        base_file_name = host_dir + "/" + cmk.utils.pnp_cleanup(servicedesc)
        try_delete(base_file_name + ".rrd")
        try_delete(base_file_name + ".info")
    else:
        host_dir = _rrd_pnp_host_dir(hostname)
        base_file_name = host_dir + "/" + cmk.utils.pnp_cleanup(servicedesc)
        try_delete(base_file_name + ".xml")
        for filename in sorted(os.listdir(host_dir)):
            if filename.startswith(cmk.utils.pnp_cleanup(servicedesc) + "_"):
                try_delete(host_dir + "/" + filename)


def _convert_pnp_rrds_of(
    hostname: HostName,
    servicedesc: _RRDServiceName,
    host_dir: str,
    xmlinfo: RRDXMLInfo,
    file_prefix: str,
    rrdconf: _RRDFileConfig,
    *,
    split: bool,
) -> None:
    need_split = False
    for ds in xmlinfo["ds"]:
        old_ds_name = ds["ds"]
        old_rrd_path = ds["rrdfile"]
        if old_rrd_path.startswith("/opt/omd/"):
            old_rrd_path = old_rrd_path[4:]  # drop the /opt, otherwise conflict with new path
        new_rrd_path = (
            host_dir + "/" + file_prefix + "_" + cmk.utils.pnp_cleanup(ds["name"]) + ".rrd"
        )

        if not os.path.exists(old_rrd_path):
            _write_line(
                f"WARNING: XML {_xml_path_for(hostname, servicedesc)} refers to not existing RRD {old_rrd_path}. "
                "Nothing to convert. Cleanup the XML file manually in case this is OK."
            )
            continue

        need_split = ds["rrd_storage_type"] == "SINGLE"
        old_size = float(os.stat(old_rrd_path).st_size)
        if need_split:
            old_size /= len(xmlinfo["ds"])

            if not split:
                console.verbose(f"    old: {old_rrd_path}")
                console.verbose(f"    new: {new_rrd_path}")
                raise Exception("storage type single, use --split-rrds to split this up.")

        console.verbose_no_lf(f"    - {ds['name']}{'(split)' if need_split else ''}..")
        result = _convert_pnp_rrd(old_rrd_path, new_rrd_path, old_ds_name, rrdconf)
        if result is True:
            new_size = os.stat(new_rrd_path).st_size
            console.verbose(
                f"..{tty.green}{tty.bold}converted{tty.normal}, {_render_rrd_size(old_size)} -> {_render_rrd_size(new_size)}"
            )
        elif result is None:
            console.verbose(f"..{tty.red}{tty.bold}failed{tty.normal}")
        else:
            console.verbose(f"..{tty.blue}{tty.bold}uptodate{tty.normal}")

    if need_split:
        _fixup_pnp_xml_file(host_dir + "/" + file_prefix + ".xml")
        os.remove(old_rrd_path)
        console.verbose(f"    deleted {old_rrd_path}")


def _convert_cmc_rrd_of(
    config: _RRDConfig,
    spec: RRDSpec,
    rrd_file_path: str,
    target_rrdconf: _RRDFileConfig,
) -> None:
    old_rrdconf = _get_old_rrd_config(rrd_file_path, "1")
    if old_rrdconf == target_rrdconf:
        console.verbose(f"..{tty.blue}{tty.bold}uptodate{tty.normal}")
    else:
        try:
            old_size = os.stat(rrd_file_path).st_size
            _create_rrd(config, spec, _write_line)
            new_size = os.stat(rrd_file_path).st_size
            console.verbose(
                f"..{tty.green}{tty.bold}converted{tty.normal}, {_render_rrd_size(old_size)} -> {_render_rrd_size(new_size)}"
            )
        except Exception:
            if cmk.ccc.debug.enabled():
                raise
            console.verbose(f"..{tty.red}{tty.bold}failed{tty.normal}")


def _convert_pnp_rrd(
    old_rrd_path: str, new_rrd_path: str, old_ds_name: MetricName, new_rrdconf: _RRDFileConfig
) -> bool | None:
    if not os.path.exists(old_rrd_path):
        raise Exception("RRD %s is missing" % old_rrd_path)

    # Our problem here: We must not convert files that already
    # have the correct configuration. We we try to extract
    # the existing configuration and compare with the new one.
    try:
        old_rrdconf = _get_old_rrd_config(old_rrd_path, old_ds_name)
        if old_rrdconf is None:
            return None  # DS not contained in old RRD

    except Exception as e:
        if cmk.ccc.debug.enabled():
            raise
        raise Exception(f"Existing RRD {old_rrd_path} is incompatible: {e}")

    # Beware: we use /opt/omd always because of bug in rrdcached
    if old_rrd_path.startswith("/omd"):
        old_rrd_path = "/opt" + old_rrd_path

    if old_rrdconf == new_rrdconf and old_rrd_path == new_rrd_path:
        return False  # Nothing to do

    new_rra_config, new_step, new_heartbeat = new_rrdconf
    args = [
        new_rrd_path,
        "--step",
        str(new_step),
        "DS:1=%s:GAUGE:%d:U:U" % (old_ds_name, new_heartbeat),
        "--source",
        old_rrd_path,
    ] + new_rra_config
    try:
        rrdtool.create(*args)
    except Exception as e:
        if cmk.ccc.debug.enabled():
            console.error(f"COMMAND: rrdtool create {' '.join(args)}", file=sys.stderr)
            raise
        raise Exception(f"Error on running rrdtool create {' '.join(args)}: {e}")
    return True


def _render_rrd_size(x: int | float) -> str:
    return str(round(x / 1024)) + " KB"


def _fixup_pnp_xml_file(xml_path: str) -> None:
    """Convert a PNP XML file from SINGLE to MULTIPLE"""
    root = ET.parse(xml_path).getroot()
    for metric in root.iter("DATASOURCE"):
        metric_name = _text_attr(metric, "NAME")
        if metric_name is None:
            raise TypeError()
        ds_name = cmk.utils.pnp_cleanup(metric_name)

        orig_rrd_file = _text_attr(metric, "RRDFILE")
        if orig_rrd_file is None:
            raise TypeError()
        rrdfile = orig_rrd_file.replace(".rrd", "_" + ds_name + ".rrd")

        _set_text_attr(metric, "RRDFILE", rrdfile)
        _set_text_attr(metric, "DS", "1")
        _set_text_attr(metric, "RRD_STORAGE_TYPE", "MULTIPLE")
    _set_text_attr(root, "NAGIOS_RRDFILE", "")
    _write_xml(root, xml_path)


def _write_xml(element: ET.Element, filepath: str) -> None:
    Path(filepath).write_text(
        (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            + ET.tostring(element, method="html", encoding="unicode")
            + "\n"
        ),
        encoding="utf-8",
    )


def _set_text_attr(node: ET.Element, attr_name: str, value: str | None) -> None:
    attr = node.find(attr_name)
    if attr is None:
        raise AttributeError()
    attr.text = value


def _write_line(text: str) -> None:
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def _get_old_rrd_config(rrd_file_path: str, old_ds_name: MetricName) -> _RRDFileConfig | None:
    old_config_raw = rrdtool.info(rrd_file_path)
    rra_defs: dict = {}
    heartbeat = None
    step = None
    for varname, value in old_config_raw.items():
        if varname == "ds[%s].minimal_heartbeat" % old_ds_name:
            heartbeat = value
        elif varname.startswith("ds["):
            pass  # other values are not relevant
        elif varname == "step":
            step = value
        elif varname.startswith("rra["):
            conf_nr = int(varname[4:].split("]")[0])
            conf = rra_defs.setdefault(conf_nr, {})
            subvar = varname.split(".")[1]
            conf[subvar] = value

    rra_items = sorted(rra_defs.items())
    rra_config: _RRAConfig = []
    for _unused_nr, rra in rra_items:
        rra_config.append("RRA:%(cf)s:%(xff).2f:%(pdp_per_row)d:%(rows)d" % rra)

    rra_config.sort()
    if heartbeat is None or step is None:
        console.verbose_no_lf(
            f"({tty.red}missing {rrd_file_path.split('/')[-1]}:{old_ds_name}{tty.normal})"
        )
        return None
    return rra_config, step, heartbeat


####################################################################################################
# CREATE RRDS
####################################################################################################

_rrd_helper_output_buffer = b""


def create_rrds_keepalive(*, reload_config: Callable[[], _RRDConfig]) -> None:
    global _rrd_helper_output_buffer
    input_buffer = b""
    _rrd_helper_output_buffer = b""

    job_queue: list[bytes] = []

    console.verbose("Started Check_MK RRD creator.")
    config = reload_config()
    try:
        # We read asynchronously from stdin and put the jobs into a queue.
        # That way the cmc main process will not be blocked by IO wait.
        while True:
            if job_queue:
                timeout: int | None = 0
            else:
                timeout = None

            if _rrd_helper_output_buffer:
                wait_for_write = [1]
            else:
                wait_for_write = []

            readable, writeable = select.select([0], wait_for_write, [], timeout)[:-1]
            if 1 in writeable:
                _write_rrd_helper_response()

            if 0 in readable:
                try:
                    new_bytes = os.read(0, 4096)
                except Exception:
                    new_bytes = b""

                if not new_bytes and not job_queue:
                    console.verbose("Core closed stdin, all jobs finished. Exiting.")
                    break

                input_buffer += new_bytes
                parts: list[bytes] = input_buffer.split(b"\n")
                if parts[-1] != b"":  # last job not terminated
                    input_buffer = parts[-1]
                else:
                    input_buffer = b""

                parts = parts[:-1]
                job_queue += parts

            # Create *one* RRD file
            if job_queue:
                if job_queue[0] == b"*":
                    console.verbose("Reloading configuration.")
                    config = reload_config()
                else:
                    spec = job_queue[0].decode("utf-8")
                    try:
                        _create_rrd_from_spec(config, RRDSpec.parse(spec))
                    except rrdtool.OperationalError as exc:
                        _queue_rrd_helper_response(f"Error creating RRD: {exc!s}")
                    except OSError as exc:
                        _queue_rrd_helper_response(f"Error creating RRD: {exc.strerror}")
                    except Exception as e:
                        if cmk.ccc.debug.enabled():
                            raise
                        crash = CMKBaseCrashReport(
                            cmk.utils.paths.crash_dir,
                            CMKBaseCrashReport.make_crash_info(
                                cmk_version.get_general_version_infos(cmk.utils.paths.omd_root)
                            ),
                        )
                        CrashReportStore().save(crash)
                        _queue_rrd_helper_response(
                            f"Error creating RRD for {spec}: {str(e) or traceback.format_exc()}"
                        )
                del job_queue[0]

    except Exception:
        if cmk.ccc.debug.enabled():
            raise
        crash = CMKBaseCrashReport(
            cmk.utils.paths.crash_dir,
            CMKBaseCrashReport.make_crash_info(
                cmk_version.get_general_version_infos(cmk.utils.paths.omd_root)
            ),
        )
        CrashReportStore().save(crash)
        _queue_rrd_helper_response(f"Check_MK RRD creator failed: {traceback.format_exc()}")

    console.verbose("Stopped Check_MK RRD creator.")


def _write_rrd_helper_response() -> None:
    global _rrd_helper_output_buffer
    size = min(4096, len(_rrd_helper_output_buffer))
    written = os.write(1, _rrd_helper_output_buffer[:size])
    _rrd_helper_output_buffer = _rrd_helper_output_buffer[written:]


def _create_rrd_from_spec(config: _RRDConfig, spec: RRDSpec) -> None:
    rrd_file_name = _create_rrd(config, spec, _queue_rrd_helper_response)

    # Do first update right now
    now = time.time()

    args = [
        rrd_file_name,
        "%d:%s"
        % (
            now,
            ":".join(
                [_float_or_nan(first_value) for (_unused_varname, first_value) in spec.metrics]
            ),
        ),
    ]
    rrdtool.update(*args)

    _queue_rrd_helper_response(
        f"CREATED {spec.format} {spec.host};{spec.service};{';'.join(spec.metric_names)}",
    )


def _queue_rrd_helper_response(response: str) -> None:
    global _rrd_helper_output_buffer
    _rrd_helper_output_buffer += (response + "\n").encode("utf-8")


def _float_or_nan(s: str | None) -> str:
    if s is None:
        return "U"
    try:
        float(s)
        return s
    except ValueError:
        return "U"


@crash_report_registry.register
class CMKBaseCrashReport(ABCCrashReport[BaseDetails]):
    @classmethod
    def type(cls) -> str:
        return "base"

    @classmethod
    def make_crash_info(
        cls,
        version_info: VersionInfo,
        _details: BaseDetails | None = None,
    ) -> CrashInfo:
        # yurks
        details = BaseDetails(
            argv=sys.argv,
            env=dict(os.environ),
        )
        return super().make_crash_info(version_info, details)
