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

# mypy: disable-error-code="comparison-overlap"

# mypy: disable-error-code="possibly-undefined"
# mypy: disable-error-code="type-arg"

import os
import select
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import assert_never, cast, Literal, NewType, Self, TypedDict

import cmk.ccc.debug
from cmk.ccc import tty
from cmk.ccc.crash_reporting import (
    ABCCrashReport,
    BaseDetails,
    CrashInfo,
    CrashReportStore,
    make_crash_report_base_path,
    VersionInfo,
)
from cmk.ccc.hostaddress import HostName
from cmk.ccc.version import get_general_version_infos
from cmk.utils import paths
from cmk.utils.log import console
from cmk.utils.metrics import MetricName
from cmk.utils.misc import pnp_cleanup

from ._fs import (
    rrd_cmc_host_dir,
    rrd_cmc_host_path,
    rrd_pnp_custom_path,
    rrd_pnp_host_dir,
    rrd_pnp_host_path,
    rrd_pnp_xml_path,
    Storage,
)
from .config import RRDConfig, RRDObjectConfig
from .interface import RRDInterface

_Seconds = NewType("_Seconds", int)

_RRDFormat = Literal["cmc_single", "pnp_multiple"]
_RRDHeartbeat = NewType("_RRDHeartbeat", int)
_RRAConfig = list[str]
_RRDFileConfigWithFormat = tuple[_RRDFormat, _RRAConfig, _Seconds, _RRDHeartbeat]
_RRDInfoValue = str | list[str]
RRDInfo = dict[str, _RRDInfoValue]
_RRDServiceName = str

_default_rrd_format: _RRDFormat = "pnp_multiple"


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
    config: RRDConfig, servicedesc: _RRDServiceName = "_HOST_"
) -> _RRDFileConfigWithFormat:
    if servicedesc == "_HOST_":
        rrdconf: RRDObjectConfig | None = config.rrd_config()
    else:
        rrdconf = config.rrd_config_of_service(servicedesc)

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


def _read_existing_metrics(info_file_path: Path) -> list[MetricName]:
    metrics = _parse_cmc_rrd_info(info_file_path)["metrics"]
    if not isinstance(metrics, list):
        raise TypeError()
    return metrics


def _parse_cmc_rrd_info(info_file_path: Path) -> RRDInfo:
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


def _create_rrd(
    rrd_interface: RRDInterface, config: RRDConfig, spec: RRDSpec, log: Callable[[str], None]
) -> Storage:
    """Create a new RRD. Automatically reuses data from an existing RRD if the
    type is CMC SINGLE. This mode is for extending existing RRDs by new metrics."""
    # We get the configured rrd_format here as well. But we rather trust what CMC
    # specifies.
    _unused_configured_rrd_format, rra_config, step, heartbeat = _get_rrd_conf(config, spec.service)

    match spec.format:
        case "pnp_multiple":
            storage = rrd_pnp_host_path(spec.host, spec.service, metric=spec.metric_names[0])
        case "cmc_single":
            storage = rrd_cmc_host_path(spec.host, spec.service)
        case _:
            assert_never(spec.format)

    base_file_name = storage.get_path()
    if base_file_name is None:
        _report_create_denied(f"rrd {spec.format}", spec.host, spec.service)
        return storage
    rrd_file_name = base_file_name.with_suffix(".rrd")

    migration_arguments = []  # List[str]
    migration_mapping = {}
    if os.path.exists(rrd_file_name):
        if spec.format == "pnp_multiple":
            raise Exception("Tried to create %s, but this RRD exists." % rrd_file_name)

        # Need to migrate data from existing RRD
        existing_metrics = _read_existing_metrics(base_file_name.with_suffix(".info"))
        migration_arguments = ["--source", str(rrd_file_name)]
        for nr, varname in enumerate(existing_metrics, 1):
            migration_mapping[varname] = nr

    if not os.path.exists(base_file_name.parent):
        os.makedirs(base_file_name.parent)

    if config.cmc_log_rrdcreation():
        log(f"Creating {rrd_file_name}")
        if config.cmc_log_rrdcreation() == "full":
            for entry in rra_config:
                log(f"    {entry}")

    args = [str(rrd_file_name), "--step", str(step)]
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
    rrd_interface.create(*args)

    if spec.format == "cmc_single":
        _create_cmc_rrd_info_file(spec)

    return storage


# Create information file for CMC format RRDs. Problem is that RRD
# limits variable names to 19 characters and to just alphanumeric
# characters. We cannot savely put our variablenames into the RRDs.
# So we do it like PNP and use 1, 2, 3... as DS names and keep the
# actual real names in a separate file with the extension ".info"
def _create_cmc_rrd_info_file(spec: RRDSpec) -> None:
    base_file_name = rrd_cmc_host_path(spec.host, spec.service).get_path()
    if base_file_name is None:
        _report_create_denied("info", spec.host, spec.service)
        return
    with open(base_file_name.with_suffix(".info"), "w") as fid:
        fid.write(
            f"HOST {spec.host}\nSERVICE {spec.service}\nMETRICS {';'.join(spec.metric_names)}\n"
        )


####################################################################################################
# CONVERT RRDS
####################################################################################################

_RRDFileConfig = tuple[_RRAConfig, _Seconds, _RRDHeartbeat]
_RRDServices = Mapping[_RRDServiceName, list[_RRDFormat]]


class DataSource(TypedDict):
    name: str
    rrdfile: str
    ds: str
    rrd_storage_type: str


class RRDXMLInfo(TypedDict):
    ds: Sequence[DataSource]
    host: str
    service: str
    rrdfile: str


class RRDConverter:
    def __init__(self, rrd_interface: RRDInterface, hostname: HostName):
        self._rrd_interface = rrd_interface
        self._hostname = hostname

    def convert_rrds_of_host(self, config: RRDConfig, *, split: bool, delete: bool) -> None:
        console.verbose(f"{tty.bold}{tty.yellow}{self._hostname}{tty.normal}:")

        try:
            existing_rrds = self._find_host_rrd_services()
            self._convert_cmc_versus_pnp(config, existing_rrds, delete=delete)
            self._convert_pnp_rrds(config, existing_rrds, split=split)
            self._convert_cmc_rrds(config, existing_rrds)
        except Exception as e:
            if cmk.ccc.debug.enabled():
                raise
            console.verbose(f"  HOST: {self._hostname}", file=sys.stderr)
            console.error(f"      {tty.red}{tty.bold}ERROR: {e}{tty.normal}", file=sys.stderr)

        console.verbose("")

    def _find_host_rrd_services(self) -> _RRDServices:
        rrd_services: dict[_RRDServiceName, list[_RRDFormat]] = {}
        for service in self._find_pnp_rrds():
            rrd_services.setdefault(service, []).append("pnp_multiple")
        for service in self._find_cmc_rrds():
            rrd_services.setdefault(service, []).append("cmc_single")
        return rrd_services

    def _convert_cmc_versus_pnp(
        self,
        config: RRDConfig,
        existing_rrds: _RRDServices,
        *,
        delete: bool,
    ) -> None:
        # Find services with RRDs in the two possible formats "cmc" and "pnp". "_HOST_" means
        # host metrics.
        for servicedesc, existing_rrd_formats in existing_rrds.items():
            target_rrdconf = _get_rrd_conf(config, servicedesc)
            target_rrd_format = target_rrdconf[0]
            if target_rrd_format not in existing_rrd_formats:
                if target_rrd_format == "pnp_multiple":
                    _write_line(
                        f"WARNING: Converting RRD format CMC into PNP not implemented ({self._hostname}/{servicedesc})"
                    )
                    # convert_cmc_to_pnp(hostname, servicedesc)
                else:
                    self._convert_pnp_to_cmc(config, servicedesc)
                    existing_rrd_formats.append(target_rrd_format)

            if len(existing_rrd_formats) > 1:
                if delete:
                    for rrd_format in existing_rrd_formats:
                        if rrd_format != target_rrd_format:
                            self._delete_rrds(servicedesc, rrd_format)
                    existing_rrd_formats[:] = [target_rrd_format]
                else:
                    _write_line(
                        f"WARNING: Duplicate RRDs for {self._hostname}/{servicedesc}. Use --delete-rrds for cleanup."
                    )

    def _convert_pnp_rrds(
        self,
        config: RRDConfig,
        existing_rrds: _RRDServices,
        *,
        split: bool,
    ) -> None:
        host_dir = rrd_pnp_host_dir(self._hostname)
        for servicedesc, existing_rrd_formats in existing_rrds.items():
            if "pnp_multiple" in existing_rrd_formats:
                console.verbose(f"  {servicedesc} ({tty.bold}{tty.cyan}PNP{tty.normal})...")
                xmlinfo = self._read_pnp_xml_for(servicedesc)
                if xmlinfo is None:
                    _report_read_denied("xml", self._hostname, servicedesc)
                    continue
                target_rrdconf = _get_rrd_conf(config, servicedesc)[1:]
                self._convert_pnp_rrds_of(
                    servicedesc,
                    host_dir,
                    xmlinfo,
                    pnp_cleanup(servicedesc),
                    target_rrdconf,
                    split=split,
                )

    def _convert_cmc_rrds(self, config: RRDConfig, existing_rrds: _RRDServices) -> None:
        for servicedesc, existing_rrd_formats in existing_rrds.items():
            if "cmc_single" in existing_rrd_formats:
                console.verbose_no_lf(f"  {servicedesc} ({tty.bold}{tty.bold}CMC{tty.normal})...")
                base_path = rrd_cmc_host_path(self._hostname, servicedesc).get_path()
                if base_path is None:
                    _report_read_denied("info", self._hostname, servicedesc)
                    continue
                existing_metrics = _read_existing_metrics(base_path.with_suffix(".info"))
                target_rrdconf = _get_rrd_conf(config, servicedesc)[1:]
                rrd_file_path = base_path.with_suffix(".rrd")
                self._convert_cmc_rrd_of(
                    config,
                    RRDSpec(
                        "cmc_single",
                        self._hostname,
                        servicedesc,
                        [(name, None) for name in existing_metrics],
                    ),
                    rrd_file_path,
                    target_rrdconf,
                )

    def _find_pnp_rrds(self) -> Iterator[_RRDServiceName]:
        host_dir = rrd_pnp_host_dir(self._hostname)
        if not os.path.exists(host_dir):
            return

        if os.path.exists(host_dir / "_HOST_.xml"):
            yield "_HOST_"

        for xml_file in sorted(os.listdir(host_dir)):
            if xml_file.endswith(".xml") and xml_file != "_HOST_.xml":
                xmlinfo = _parse_pnp_xml_file(host_dir / xml_file)
                servicedesc = xmlinfo["service"]
                yield servicedesc

    def _find_cmc_rrds(self) -> Iterator[_RRDServiceName]:
        host_dir = rrd_cmc_host_dir(self._hostname)
        if not os.path.exists(host_dir):
            return
        for info_file in sorted(os.listdir(host_dir)):
            if info_file.endswith(".info"):
                service = _parse_cmc_rrd_info(host_dir / info_file)["service"]
                if not isinstance(service, str):
                    raise TypeError()
                yield service

    def _convert_pnp_to_cmc(self, config: RRDConfig, servicedesc: _RRDServiceName) -> None:
        console.verbose_no_lf(
            f"   {servicedesc} {tty.bold}{tty.cyan}PNP{tty.normal} -> {tty.bold}CMC{tty.normal}"
        )

        # We get the configured rrd_format here as well. But we rather trust what CMC
        # specifies.
        rra_config, step, heartbeat = _get_rrd_conf(config, servicedesc)[1:]

        base_file_name = rrd_cmc_host_path(self._hostname, servicedesc).get_path()
        if base_file_name is None:
            _report_create_denied("rrd", self._hostname, servicedesc)
            return
        rrd_file_name = base_file_name.with_suffix(".rrd")

        args = [str(rrd_file_name), "--step", str(step)]
        xml_info = self._read_pnp_xml_for(servicedesc)
        metric_names = []
        if xml_info is None:
            _report_read_denied("xml", self._hostname, servicedesc)
        else:
            for nr, ds in enumerate(xml_info["ds"], 1):
                varname = ds["name"]
                metric_names.append(varname)
                source_file = rrd_pnp_host_path(
                    self._hostname, servicedesc, metric=varname
                ).get_path()
                if source_file is None:
                    _report_read_denied("rrd", self._hostname, servicedesc)
                    continue
                pnp_rrd_filename = source_file.with_suffix(".rrd")

                if not os.path.exists(pnp_rrd_filename):
                    _write_line(
                        f"WARNING: XML {rrd_pnp_xml_path(self._hostname, servicedesc)} refers to not existing RRD {pnp_rrd_filename}. "
                        "Nothing to convert. Cleanup the XML file manually in case this is OK."
                    )
                    continue

                args += [
                    "--source",
                    str(pnp_rrd_filename),
                    f"DS:{nr}=1[{nr}]:GAUGE:{heartbeat}:U:U",
                ]

        if not os.path.exists(base_file_name.parent):
            os.makedirs(base_file_name.parent)

        args += rra_config

        # Note: rrdtool.create bails out with a Bus error if the disk is full. There
        # is no way to handle this here. Or can we catch the signal 6? In any case it does not
        # make sense to check the size of the RRD for 0 after this command since our process
        # will not exist anymore by then...
        self._rrd_interface.create(*args)

        # Create information file for CMC format RRDs. Problem is that RRD
        # limits variable names to 19 characters and to just alphanumeric
        # characters. We cannot savely put our variablenames into the RRDs.
        # So we do it like PNP and use 1, 2, 3... as DS names and keep the
        # actual real names in a separate file with the extension ".info"
        _create_cmc_rrd_info_file(
            RRDSpec("cmc_single", self._hostname, servicedesc, [(n, None) for n in metric_names])
        )
        console.verbose(f"..{tty.bold}{tty.green}converted.{tty.normal}")
        console.debug(f"    (rrdtool create {' '.join(args)})")

    def _read_pnp_xml_for(self, servicedesc: _RRDServiceName) -> RRDXMLInfo | None:
        xml_file = rrd_pnp_xml_path(self._hostname, servicedesc).get_path()
        if xml_file is None:
            _report_read_denied("xml", self._hostname, servicedesc)
            return None
        return _parse_pnp_xml_file(xml_file)

    def _delete_rrds(self, servicedesc: _RRDServiceName, rrd_format: _RRDFormat) -> None:
        def try_delete(path: Path | None, suffix: str) -> None:
            if path is None:
                return
            try:
                os.remove(path.with_suffix(suffix))
                console.verbose(f"Deleted {path}")
            except OSError:
                pass

        if rrd_format == "cmc_single":
            base_file_name = rrd_cmc_host_path(self._hostname, servicedesc).get_path()
            try_delete(base_file_name, ".rrd")
            try_delete(base_file_name, ".info")
        else:
            host_dir = rrd_pnp_host_dir(self._hostname)
            base_file_name = rrd_cmc_host_path(self._hostname, servicedesc).get_path()
            try_delete(base_file_name, ".xml")
            for filename in sorted(os.listdir(host_dir)):
                if filename.startswith(pnp_cleanup(servicedesc) + "_"):
                    try_delete(host_dir / filename, "")

    def _convert_pnp_rrds_of(
        self,
        servicedesc: _RRDServiceName,
        host_dir: Path,
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
            if not os.path.exists(old_rrd_path):
                _write_line(
                    f"WARNING: XML {rrd_pnp_xml_path(self._hostname, servicedesc)} refers to not existing RRD {old_rrd_path}. "
                    "Nothing to convert. Cleanup the XML file manually in case this is OK."
                )
                continue

            base_file_name = rrd_pnp_custom_path(
                host_dir, file_prefix, metric=ds["name"]
            ).get_path()
            if base_file_name is None:
                _report_create_denied("rrd", self._hostname, servicedesc)
                continue
            new_rrd_path = base_file_name.with_suffix(".rrd")

            need_split = ds["rrd_storage_type"] == "SINGLE"
            old_size = float(os.stat(old_rrd_path).st_size)
            if need_split:
                old_size /= len(xmlinfo["ds"])

                if not split:
                    console.verbose(f"    old: {old_rrd_path}")
                    console.verbose(f"    new: {new_rrd_path}")
                    raise Exception("storage type single, use --split-rrds to split this up.")

            console.verbose_no_lf(f"    - {ds['name']}{'(split)' if need_split else ''}..")
            result = self._convert_pnp_rrd(
                Path(old_rrd_path),
                new_rrd_path=new_rrd_path,
                old_ds_name=old_ds_name,
                new_rrdconf=rrdconf,
            )
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
            _fixup_pnp_xml_file((host_dir / file_prefix).with_suffix(".xml"))
            os.remove(old_rrd_path)
            console.verbose(f"    deleted {old_rrd_path}")

    def _convert_cmc_rrd_of(
        self,
        config: RRDConfig,
        spec: RRDSpec,
        rrd_file_path: Path,
        target_rrdconf: _RRDFileConfig,
    ) -> None:
        old_rrdconf = self._get_old_rrd_config(rrd_file_path, "1")
        if old_rrdconf == target_rrdconf:
            console.verbose(f"..{tty.blue}{tty.bold}uptodate{tty.normal}")
        else:
            try:
                old_size = os.stat(rrd_file_path).st_size
                _create_rrd(self._rrd_interface, config, spec, _write_line)
                new_size = os.stat(rrd_file_path).st_size
                console.verbose(
                    f"..{tty.green}{tty.bold}converted{tty.normal}, {_render_rrd_size(old_size)} -> {_render_rrd_size(new_size)}"
                )
            except Exception:
                if cmk.ccc.debug.enabled():
                    raise
                console.verbose(f"..{tty.red}{tty.bold}failed{tty.normal}")

    def _convert_pnp_rrd(
        self,
        old_rrd_path: Path,
        *,
        new_rrd_path: Path,
        old_ds_name: MetricName,
        new_rrdconf: _RRDFileConfig,
    ) -> bool | None:
        if not os.path.exists(old_rrd_path):
            raise Exception("RRD %s is missing" % old_rrd_path)

        # Our problem here: We must not convert files that already
        # have the correct configuration. We we try to extract
        # the existing configuration and compare with the new one.
        try:
            old_rrdconf = self._get_old_rrd_config(old_rrd_path, old_ds_name)
            if old_rrdconf is None:
                return None  # DS not contained in old RRD

        except Exception as e:
            if cmk.ccc.debug.enabled():
                raise
            raise Exception(f"Existing RRD {old_rrd_path} is incompatible: {e}")

        # Beware: we use /opt/omd always because of bug in rrdcached
        if str(old_rrd_path).startswith("/omd"):
            old_rrd_path = Path("/opt") / old_rrd_path

        if old_rrdconf == new_rrdconf and old_rrd_path == new_rrd_path:
            return False  # Nothing to do

        new_rra_config, new_step, new_heartbeat = new_rrdconf
        args = [
            str(new_rrd_path),
            "--step",
            str(new_step),
            "DS:1=%s:GAUGE:%d:U:U" % (old_ds_name, new_heartbeat),
            "--source",
            str(old_rrd_path),
        ] + new_rra_config
        try:
            self._rrd_interface.create(*args)
        except Exception as e:
            if cmk.ccc.debug.enabled():
                console.error(f"COMMAND: rrdtool create {' '.join(args)}", file=sys.stderr)
                raise
            raise Exception(f"Error on running rrdtool create {' '.join(args)}: {e}")
        return True

    def _get_old_rrd_config(
        self, rrd_file_path: Path, old_ds_name: MetricName
    ) -> _RRDFileConfig | None:
        old_config_raw = self._rrd_interface.info(str(rrd_file_path))
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
                f"({tty.red}missing {rrd_file_path.name}:{old_ds_name}{tty.normal})"
            )
            return None
        return rra_config, _Seconds(step), _RRDHeartbeat(heartbeat)


def _parse_pnp_xml_file(xml_path: Path) -> RRDXMLInfo:
    if (root := ET.parse(xml_path).getroot()) is None:
        raise TypeError()
    return RRDXMLInfo(
        ds=[
            DataSource(
                name=_text_attr(child, "NAME"),
                rrdfile=_text_attr(child, "RRDFILE"),
                ds=_text_attr(child, "DS"),
                rrd_storage_type=_text_attr(child, "RRD_STORAGE_TYPE"),
            )
            for child in root.iter("DATASOURCE")
        ],
        host=_text_attr(root, "NAGIOS_AUTH_HOSTNAME"),
        service=_text_attr(root, "NAGIOS_AUTH_SERVICEDESC"),
        rrdfile=_text_attr(root, "NAGIOS_RRDFILE"),
    )


def _text_attr(node: ET.Element, attr_name: str) -> str:
    if (attr := node.find(attr_name)) is None:
        raise AttributeError()
    return "" if attr.text is None else attr.text


def _render_rrd_size(x: int | float) -> str:
    return str(round(x / 1024)) + " KB"


def _fixup_pnp_xml_file(xml_path: Path) -> None:
    """Convert a PNP XML file from SINGLE to MULTIPLE"""
    root = ET.parse(xml_path).getroot()
    for metric in root.iter("DATASOURCE"):
        metric_name = _text_attr(metric, "NAME")
        if metric_name is None:
            raise TypeError()
        ds_name = pnp_cleanup(metric_name)

        orig_rrd_file = _text_attr(metric, "RRDFILE")
        if orig_rrd_file is None:
            raise TypeError()
        rrdfile = orig_rrd_file.replace(".rrd", "_" + ds_name + ".rrd")

        _set_text_attr(metric, "RRDFILE", rrdfile)
        _set_text_attr(metric, "DS", "1")
        _set_text_attr(metric, "RRD_STORAGE_TYPE", "MULTIPLE")
    _set_text_attr(root, "NAGIOS_RRDFILE", "")
    _write_xml(root, xml_path)


def _write_xml(element: ET.Element, filepath: Path) -> None:
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


####################################################################################################
# CREATE RRDS
####################################################################################################


class RRDCreator:
    def __init__(self, rrd_interface: RRDInterface):
        self._rrd_interface = rrd_interface
        self._rrd_helper_output_buffer = b""

    def create_rrds_keepalive(self, config_class: type[RRDConfig]) -> None:
        input_buffer = b""
        self._rrd_helper_output_buffer = b""
        job_queue = list[bytes]()
        console.verbose("Started Check_MK RRD creator.")
        try:
            # We read asynchronously from stdin and put the jobs into a queue.
            # That way the cmc main process will not be blocked by IO wait.
            while True:
                readable, writeable = select.select(
                    [0],
                    [1] if self._rrd_helper_output_buffer else [],
                    [],
                    0 if job_queue else None,
                )[:-1]

                if 1 in writeable:
                    self._write_rrd_helper_response()

                if 0 in readable:
                    try:
                        new_bytes = os.read(0, 4096)
                    except Exception:
                        new_bytes = b""
                    if not new_bytes and not job_queue:
                        console.verbose("Core closed stdin, all jobs finished. Exiting.")
                        break
                    parts = (input_buffer + new_bytes).split(b"\n")
                    job_queue += parts[:-1]
                    input_buffer = parts[-1]

                # Create *one* RRD file
                if job_queue:
                    self._handle_job(job_queue[0].decode("utf-8"), config_class)
                    del job_queue[0]

        except Exception:
            if cmk.ccc.debug.enabled():
                raise
            create_crash_report()
            self._queue_rrd_helper_response(
                f"Check_MK RRD creator failed: {traceback.format_exc()}"
            )

        console.verbose("Stopped Check_MK RRD creator.")

    def _write_rrd_helper_response(self) -> None:
        size = min(4096, len(self._rrd_helper_output_buffer))
        written = os.write(1, self._rrd_helper_output_buffer[:size])
        self._rrd_helper_output_buffer = self._rrd_helper_output_buffer[written:]

    def _handle_job(self, spec: str, config_class: type[RRDConfig]) -> None:
        parsed_spec = RRDSpec.parse(spec)
        config = config_class(parsed_spec.host)
        try:
            self._create_rrd_from_spec(config, parsed_spec)
        except self._rrd_interface.OperationalError as exc:
            self._queue_rrd_helper_response(f"Error creating RRD: {exc!s}")
        except OSError as exc:
            self._queue_rrd_helper_response(f"Error creating RRD: {exc.strerror}")
        except Exception as e:
            if cmk.ccc.debug.enabled():
                raise
            create_crash_report()
            self._queue_rrd_helper_response(
                f"Error creating RRD for {spec}: {str(e) or traceback.format_exc()}"
            )

    def _create_rrd_from_spec(self, config: RRDConfig, spec: RRDSpec) -> None:
        rrd_file_name = _create_rrd(
            self._rrd_interface, config, spec, self._queue_rrd_helper_response
        )

        # Do first update right now
        now = time.time()

        args = [
            str(rrd_file_name.get_expected_path(".rrd")),
            "%d:%s"
            % (
                now,
                ":".join(
                    [_float_or_nan(first_value) for (_unused_varname, first_value) in spec.metrics]
                ),
            ),
        ]
        self._rrd_interface.update(*args)

        self._queue_rrd_helper_response(
            f"CREATED {spec.format} {spec.host};{spec.service};{';'.join(spec.metric_names)}",
        )

    def _queue_rrd_helper_response(self, response: str) -> None:
        self._rrd_helper_output_buffer += (response + "\n").encode("utf-8")


def create_crash_report() -> None:
    CrashReportStore().save(
        CMKBaseCrashReport(
            crash_report_base_path=make_crash_report_base_path(paths.omd_root),
            crash_info=CMKBaseCrashReport.make_crash_info(
                get_general_version_infos(paths.omd_root)
            ),
        )
    )


def _float_or_nan(s: str | None) -> str:
    if s is None:
        return "U"
    try:
        float(s)
        return s
    except ValueError:
        return "U"


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


def _report_create_denied(note: str, host: HostName, service: _RRDServiceName) -> None:
    console.verbose(
        f"WARNING: Can't create {note} file for {host} {service} because path is too long or invalid."
    )


def _report_read_denied(note: str, host: HostName, service: _RRDServiceName) -> None:
    console.verbose(
        f"WARNING: Can't read {note} file for {host} {service} because path is too long or invalid."
    )
