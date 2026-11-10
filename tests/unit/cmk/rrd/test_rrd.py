#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import itertools
import json
import socket
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Literal

import pytest
import rrdtool  # type: ignore[import-not-found]

from cmk.ccc.config_path import VersionedConfigPath
from cmk.ccc.hostaddress import HostName
from cmk.ccc.store import save_object_to_file
from cmk.rrd import (
    rrd_config_dir,
    rrd_config_hosts_dir,
    RRD_DEFAULT_CONFIG,
    RRD_HEARTBEAT,
    RRDConfig,
    RRDCreator,
    RRDInterface,
    RRDObjectConfig,
    RRDPaths,
    RRDSpec,
)
from cmk.rrd.convert_rrds import convert_rrds

HOST = HostName("heute")
SERVICE = "CPU load"
STEP = 60
SMALL_LAYOUT = ["RRA:AVERAGE:0.50:1:100"]

# Data in RRDs we set up ourselves lies well in the past, so it can never get in the way
# of the first update the creator does with the current time. It lies well within the
# 100 rows of our layouts, too, so that update doesn't push it out.
PAST = (int(time.time()) // STEP - 50) * STEP
UPDATES = 5


@pytest.fixture(name="opt_root")
def fixture_opt_root(tmp_path: Path) -> Path:
    opt_root = tmp_path / "opt/omd/sites/heute"
    opt_root.mkdir(parents=True)
    return opt_root


@pytest.fixture(name="omd_root")
def fixture_omd_root(tmp_path: Path, opt_root: Path) -> Path:
    """As in a real installation, the site directory can be reached below /opt, too"""
    omd_root = tmp_path / "omd/sites/heute"
    omd_root.parent.mkdir(parents=True)
    omd_root.symlink_to(opt_root)
    site_conf = omd_root / "etc/omd/site.conf"
    site_conf.parent.mkdir(parents=True)
    site_conf.write_text("CONFIG_CORE='cmc'\n")
    return omd_root


@pytest.fixture(name="rrd_paths")
def fixture_rrd_paths(omd_root: Path, opt_root: Path) -> RRDPaths:
    return RRDPaths(omd_root=omd_root, opt_root=opt_root, max_filename_length=255)


def object_config(
    *,
    cfs: Sequence[Literal["MIN", "MAX", "AVERAGE"]] = ("AVERAGE",),
    rras: Sequence[tuple[float, int, int]] = ((50.0, 1, 100),),
    step: int = STEP,
    rrd_format: Literal["pnp_multiple", "cmc_single"] = "cmc_single",
) -> RRDObjectConfig:
    return RRDObjectConfig(cfs=list(cfs), rras=list(rras), step=step, format=rrd_format)


def write_rrd_config(
    omd_root: Path,
    hostname: HostName = HOST,
    *,
    host: RRDObjectConfig | None = None,
    services: Mapping[str, RRDObjectConfig] | None = None,
) -> None:
    hosts_dir = rrd_config_hosts_dir(VersionedConfigPath.make_latest_path(omd_root))
    hosts_dir.mkdir(parents=True, exist_ok=True)
    save_object_to_file(hosts_dir / hostname, {"host": host, "services": services or {}})


def write_rrd_creation_logging(omd_root: Path, level: Literal["terse", "full"]) -> None:
    config_dir = rrd_config_dir(VersionedConfigPath.make_latest_path(omd_root))
    config_dir.mkdir(parents=True, exist_ok=True)
    save_object_to_file(config_dir / "cmc_log_rrdcreation", level)


def existing_path(path: Path | None) -> Path:
    assert path is not None
    return path


def make_rrd(path: Path, *, ds_values: Sequence[float], layout: Sequence[str]) -> None:
    """Create an RRD with one data source per value, each updated with its value a few times"""
    path.parent.mkdir(parents=True, exist_ok=True)
    rrdtool.create(
        str(path),
        "--start",
        str(PAST),
        "--step",
        str(STEP),
        *(f"DS:{nr}:GAUGE:{RRD_HEARTBEAT}:U:U" for nr in range(1, len(ds_values) + 1)),
        *layout,
    )
    for n in range(1, UPDATES + 1):
        rrdtool.update(str(path), ":".join([str(PAST + n * STEP), *map(str, ds_values)]))


def make_cmc_rrd(
    rrd_paths: RRDPaths, metrics: Mapping[str, float], *, hostname: HostName = HOST
) -> Path:
    storage = rrd_paths.cmc_storage(hostname, SERVICE)
    rrd = existing_path(storage.path(".rrd"))
    make_rrd(rrd, ds_values=list(metrics.values()), layout=SMALL_LAYOUT)
    existing_path(storage.path(".info")).write_text(
        f"HOST {hostname}\nSERVICE {SERVICE}\nMETRICS {';'.join(metrics)}\n"
    )
    return rrd


# Data PNP keeps in its XML files, too, but the conversion doesn't care about
PNP_TEMPLATE = "check_mk-cpu.loads"
PNP_XML_VERSION = "4"


def write_pnp_xml(
    path: Path,
    *,
    storage_type: Literal["SINGLE", "MULTIPLE"],
    datasources: Sequence[tuple[str, Path | None, str]],
    rrdfile: Path | None = None,
) -> None:
    datasources_xml = "".join(
        f"""
  <DATASOURCE>
    <TEMPLATE>{PNP_TEMPLATE}</TEMPLATE>
    <RRDFILE>{ds_rrdfile or ""}</RRDFILE>
    <RRD_STORAGE_TYPE>{storage_type}</RRD_STORAGE_TYPE>
    <DS>{ds}</DS>
    <NAME>{name}</NAME>
  </DATASOURCE>"""
        for name, ds_rrdfile, ds in datasources
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<NAGIOS>{datasources_xml}
  <NAGIOS_AUTH_HOSTNAME>{HOST}</NAGIOS_AUTH_HOSTNAME>
  <NAGIOS_AUTH_SERVICEDESC>{SERVICE}</NAGIOS_AUTH_SERVICEDESC>
  <NAGIOS_RRDFILE>{rrdfile or ""}</NAGIOS_RRDFILE>
  <XML>
   <VERSION>{PNP_XML_VERSION}</VERSION>
  </XML>
</NAGIOS>
"""
    )


def pnp_xml_file(rrd_paths: RRDPaths) -> Path:
    return existing_path(rrd_paths.pnp_xml_storage(HOST, SERVICE).path(".xml"))


def pnp_rrd_file(rrd_paths: RRDPaths, metric: str) -> Path:
    return existing_path(rrd_paths.pnp_storage(HOST, SERVICE, metric=metric).path(".rrd"))


def site_path(rrd_paths: RRDPaths, path: Path) -> Path:
    """The path below the site directory, the way PNP refers to RRDs in its XML files"""
    return rrd_paths.omd_root / path.relative_to(rrd_paths.opt_root)


def make_pnp_rrds(rrd_paths: RRDPaths, metrics: Mapping[str, float]) -> None:
    for metric, value in metrics.items():
        make_rrd(pnp_rrd_file(rrd_paths, metric), ds_values=[value], layout=SMALL_LAYOUT)
    write_pnp_xml(
        pnp_xml_file(rrd_paths),
        storage_type="MULTIPLE",
        datasources=[(metric, pnp_rrd_file(rrd_paths, metric), "1") for metric in metrics],
    )


def single_pnp_rrd_file(rrd_paths: RRDPaths) -> Path:
    return existing_path(rrd_paths.pnp_xml_storage(HOST, SERVICE).path(".rrd"))


def make_single_pnp_rrd(rrd_paths: RRDPaths, metrics: Mapping[str, float]) -> None:
    """Only PNP writes RRDs in storage type SINGLE"""
    rrd = single_pnp_rrd_file(rrd_paths)
    make_rrd(rrd, ds_values=list(metrics.values()), layout=SMALL_LAYOUT)
    write_pnp_xml(
        pnp_xml_file(rrd_paths),
        storage_type="SINGLE",
        datasources=[
            (metric, site_path(rrd_paths, rrd), str(nr)) for nr, metric in enumerate(metrics, 1)
        ],
        rrdfile=site_path(rrd_paths, rrd),
    )


def layout(rrd: Path) -> tuple[int, list[str]]:
    info = rrdtool.info(str(rrd))
    rras = [
        f"RRA:{info[f'rra[{nr}].cf']}:{info[f'rra[{nr}].xff']:.2f}"
        f":{info[f'rra[{nr}].pdp_per_row']}:{info[f'rra[{nr}].rows']}"
        for nr in itertools.takewhile(lambda nr: f"rra[{nr}].cf" in info, itertools.count())
    ]
    return info["step"], sorted(rras)


def data_sources(rrd: Path) -> list[str]:
    return sorted(
        {key[3 : key.index("]")] for key in rrdtool.info(str(rrd)) if key.startswith("ds[")}
    )


def last_value(rrd: Path, ds: str) -> str:
    value: str = rrdtool.info(str(rrd))[f"ds[{ds}].last_ds"]
    return value


def past_data(rrd: Path) -> dict[str, list[float | None]]:
    """The values of the intervals make_rrd() has updated"""
    _time_range, names, rows = rrdtool.fetch(
        str(rrd), "AVERAGE", "--start", str(PAST), "--end", str(PAST + UPDATES * STEP)
    )
    return {name: [row[nr] for row in rows[:UPDATES]] for nr, name in enumerate(names)}


def crash_reports(omd_root: Path) -> list[Mapping[str, object]]:
    return [
        json.loads(crash_info.read_text())
        for crash_info in (omd_root / "var/check_mk/crashes").glob("*/*/crash.info")
    ]


def create_rrds(
    rrd_paths: RRDPaths,
    *jobs: str | bytes,
    config_factory: Callable[[HostName], RRDConfig] | None = None,
    rrd_interface: RRDInterface = rrdtool,
) -> list[str]:
    """Feed the jobs to the RRD creator like the core does and return its answers

    The core uses one end of a socket pair as the creator's stdin and stdout, and so do we.
    """
    core, helper = socket.socketpair()
    with core, helper:
        core.sendall(
            b"".join((job if isinstance(job, bytes) else job.encode()) + b"\n" for job in jobs)
        )
        core.shutdown(socket.SHUT_WR)
        RRDCreator(
            rrd_interface, rrd_paths, input_fd=helper.fileno(), output_fd=helper.fileno()
        ).create_rrds_keepalive(
            config_factory or (lambda hostname: RRDConfig(hostname, rrd_paths.omd_root)),
        )
        helper.close()
        with core.makefile("rb") as answers:
            return answers.read().decode().splitlines()


def convert(
    rrd_paths: RRDPaths,
    *hostnames: HostName,
    split: bool = False,
    delete: bool = False,
) -> None:
    convert_rrds(rrdtool, hostnames, split, delete, rrd_paths=rrd_paths)


####################################################################################################
# RRDSpec
####################################################################################################


def test_service_spec_lists_the_metrics_with_their_values() -> None:
    spec = RRDSpec.parse("cmc_single;heute;Check_MK;execution_time;0.141;user_time;0.020")

    assert spec == RRDSpec(
        "cmc_single",
        HostName("heute"),
        "Check_MK",
        [("execution_time", "0.141"), ("user_time", "0.020")],
    )


def test_host_spec_is_for_the_host_service() -> None:
    spec = RRDSpec.parse("pnp_multiple;heute;rta;0.141")

    assert spec == RRDSpec("pnp_multiple", HostName("heute"), "_HOST_", [("rta", "0.141")])


@pytest.mark.parametrize(
    "spec, reason",
    [
        pytest.param("rrd_magic;heute;rta;0.141", "rrd_magic", id="unknown format"),
        pytest.param("cmc_single;he ute;rta;0.141", "invalid host address", id="invalid host"),
    ],
)
def test_invalid_spec_is_rejected(spec: str, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        RRDSpec.parse(spec)


####################################################################################################
# RRD creation
####################################################################################################


def test_each_job_is_answered_in_order(rrd_paths: RRDPaths) -> None:
    responses = create_rrds(
        rrd_paths,
        "cmc_single;heute;CPU load;load1;0.5;load5;0.7",
        "pnp_multiple;heute;rta;0.1",
    )

    assert responses == [
        "CREATED cmc_single heute;CPU load;load1;load5",
        "CREATED pnp_multiple heute;_HOST_;rta",
    ]


def test_cmc_rrd_has_a_data_source_per_metric(rrd_paths: RRDPaths) -> None:
    create_rrds(rrd_paths, "cmc_single;heute;CPU load;load1;0.5;load5;0.7")

    assert data_sources(existing_path(rrd_paths.cmc_storage(HOST, SERVICE).path(".rrd"))) == [
        "1",
        "2",
    ]


def test_cmc_rrd_info_file_names_the_metrics(rrd_paths: RRDPaths) -> None:
    create_rrds(rrd_paths, "cmc_single;heute;CPU load;load1;0.5;load5;0.7")

    assert existing_path(rrd_paths.cmc_storage(HOST, SERVICE).path(".info")).read_text() == (
        "HOST heute\nSERVICE CPU load\nMETRICS load1;load5\n"
    )


def test_pnp_rrd_is_created_for_the_metric(rrd_paths: RRDPaths) -> None:
    create_rrds(rrd_paths, "pnp_multiple;heute;CPU load;load1;0.5")

    assert pnp_rrd_file(rrd_paths, "load1").exists()


@pytest.mark.parametrize(
    "value, stored",
    [
        pytest.param("0.5", "0.5", id="number"),
        pytest.param("abc", "U", id="not a number"),
        pytest.param("", "U", id="empty"),
    ],
)
def test_first_update_stores_the_values_from_the_job(
    rrd_paths: RRDPaths, value: str, stored: str
) -> None:
    create_rrds(rrd_paths, f"cmc_single;heute;CPU load;load1;{value};load5;0.7")

    rrd = existing_path(rrd_paths.cmc_storage(HOST, SERVICE).path(".rrd"))
    assert [last_value(rrd, "1"), last_value(rrd, "2")] == [stored, "0.7"]


def test_service_rrd_gets_the_configured_layout(omd_root: Path, rrd_paths: RRDPaths) -> None:
    write_rrd_config(
        omd_root,
        services={
            SERVICE: object_config(
                cfs=("AVERAGE", "MAX"), rras=((50.0, 1, 100), (50.0, 5, 50)), step=30
            )
        },
    )

    create_rrds(rrd_paths, "cmc_single;heute;CPU load;load1;0.5")

    assert layout(existing_path(rrd_paths.cmc_storage(HOST, SERVICE).path(".rrd"))) == (
        30,
        [
            "RRA:AVERAGE:0.50:1:100",
            "RRA:AVERAGE:0.50:5:50",
            "RRA:MAX:0.50:1:100",
            "RRA:MAX:0.50:5:50",
        ],
    )


def test_host_rrd_gets_the_configured_layout(omd_root: Path, rrd_paths: RRDPaths) -> None:
    write_rrd_config(omd_root, host=object_config(cfs=("MIN",), rras=((30.0, 2, 50),), step=30))

    create_rrds(rrd_paths, "cmc_single;heute;rta;0.1")

    assert layout(existing_path(rrd_paths.cmc_storage(HOST, "_HOST_").path(".rrd"))) == (
        30,
        ["RRA:MIN:0.30:2:50"],
    )


def test_rrd_without_configuration_gets_the_default_layout(rrd_paths: RRDPaths) -> None:
    create_rrds(rrd_paths, "cmc_single;heute;CPU load;load1;0.5")

    assert layout(existing_path(rrd_paths.cmc_storage(HOST, SERVICE).path(".rrd"))) == (
        60,
        sorted(RRD_DEFAULT_CONFIG),
    )


def test_new_metric_keeps_the_data_of_the_existing_ones(
    omd_root: Path, rrd_paths: RRDPaths
) -> None:
    write_rrd_config(omd_root, services={SERVICE: object_config()})
    rrd = make_cmc_rrd(rrd_paths, {"load1": 10.0, "load5": 20.0})

    create_rrds(rrd_paths, "cmc_single;heute;CPU load;load15;0.1;load5;0.7;load1;0.5")

    assert {ds: values for ds, values in past_data(rrd).items() if ds != "1"} == {
        "2": [20.0] * UPDATES,
        "3": [10.0] * UPDATES,
    }


class RRDToolFailingUnexpectedly:
    """rrdtool, but creating an RRD fails with an error nobody expects"""

    OperationalError = rrdtool.OperationalError

    def create(self, *_args: str) -> None:
        raise RuntimeError("something unexpected")

    def update(self, *args: str) -> None:
        rrdtool.update(*args)

    def info(self, *args: str) -> Mapping[str, int]:
        info: Mapping[str, int] = rrdtool.info(*args)
        return info


def test_unexpected_error_is_reported(rrd_paths: RRDPaths) -> None:
    job = "cmc_single;heute;CPU load;load1;0.5"

    responses = create_rrds(rrd_paths, job, rrd_interface=RRDToolFailingUnexpectedly())

    assert responses == [f"Error creating RRD for {job}: something unexpected"]


def test_unexpected_error_writes_a_crash_report(omd_root: Path, rrd_paths: RRDPaths) -> None:
    create_rrds(
        rrd_paths, "cmc_single;heute;CPU load;load1;0.5", rrd_interface=RRDToolFailingUnexpectedly()
    )

    assert [report["exc_value"] for report in crash_reports(omd_root)] == ["something unexpected"]


def make_corrupt_cmc_rrd(rrd_paths: RRDPaths) -> Path:
    storage = rrd_paths.cmc_storage(HOST, SERVICE)
    rrd = existing_path(storage.path(".rrd"))
    rrd.parent.mkdir(parents=True)
    rrd.write_bytes(b"garbage")
    existing_path(storage.path(".info")).write_text(
        f"HOST {HOST}\nSERVICE {SERVICE}\nMETRICS load1\n"
    )
    return rrd


def test_rrdtool_error_is_reported(rrd_paths: RRDPaths) -> None:
    rrd = make_corrupt_cmc_rrd(rrd_paths)

    responses = create_rrds(rrd_paths, "cmc_single;heute;CPU load;load1;0.5;load5;0.7")

    assert responses == [f"Error creating RRD: Cannot open source RRD {rrd}"]


def test_rrdtool_error_writes_no_crash_report(omd_root: Path, rrd_paths: RRDPaths) -> None:
    make_corrupt_cmc_rrd(rrd_paths)

    create_rrds(rrd_paths, "cmc_single;heute;CPU load;load1;0.5;load5;0.7")

    assert crash_reports(omd_root) == []


def test_os_error_is_reported(rrd_paths: RRDPaths) -> None:
    rrd_paths.rrd_single_dir.parent.mkdir(parents=True)
    rrd_paths.rrd_single_dir.write_text("not a directory")

    responses = create_rrds(rrd_paths, "cmc_single;heute;CPU load;load1;0.5")

    assert responses == ["Error creating RRD: Not a directory"]


def test_rrd_with_too_long_path_is_skipped(rrd_paths: RRDPaths) -> None:
    short_rrd_paths = dataclasses.replace(rrd_paths, max_filename_length=10)

    responses = create_rrds(short_rrd_paths, "cmc_single;heute;CPU load;load1;0.5")

    assert responses == [
        "SKIPPED Can't create rrd file for heute CPU load because path is too long or invalid.",
        "CREATED cmc_single heute;CPU load;load1",
    ]


def test_rrd_creation_is_logged_tersely(omd_root: Path, rrd_paths: RRDPaths) -> None:
    write_rrd_creation_logging(omd_root, "terse")

    responses = create_rrds(rrd_paths, "cmc_single;heute;CPU load;load1;0.5")

    assert responses == [
        f"Creating {rrd_paths.cmc_storage(HOST, SERVICE).path('.rrd')}",
        "CREATED cmc_single heute;CPU load;load1",
    ]


def test_rrd_creation_is_logged_with_layout(omd_root: Path, rrd_paths: RRDPaths) -> None:
    write_rrd_config(omd_root, services={SERVICE: object_config()})
    write_rrd_creation_logging(omd_root, "full")

    responses = create_rrds(rrd_paths, "cmc_single;heute;CPU load;load1;0.5")

    assert responses == [
        f"Creating {rrd_paths.cmc_storage(HOST, SERVICE).path('.rrd')}",
        "    RRA:AVERAGE:0.50:1:100",
        "CREATED cmc_single heute;CPU load;load1",
    ]


def test_failed_job_does_not_stop_later_ones(rrd_paths: RRDPaths) -> None:
    rrd = make_corrupt_cmc_rrd(rrd_paths)

    responses = create_rrds(
        rrd_paths,
        "cmc_single;heute;CPU load;load1;0.5;load5;0.7",
        "pnp_multiple;heute;CPU load;load5;0.7",
    )

    assert responses == [
        f"Error creating RRD: Cannot open source RRD {rrd}",
        "CREATED pnp_multiple heute;CPU load;load5",
    ]


####################################################################################################
# RRD conversion
####################################################################################################


def test_cmc_rrd_with_configured_layout_is_left_alone(omd_root: Path, rrd_paths: RRDPaths) -> None:
    write_rrd_config(omd_root, services={SERVICE: object_config()})
    rrd = make_cmc_rrd(rrd_paths, {"load1": 10.0})
    inode = rrd.stat().st_ino

    convert(rrd_paths, HOST)

    assert rrd.stat().st_ino == inode


def test_cmc_rrd_gets_the_configured_layout(omd_root: Path, rrd_paths: RRDPaths) -> None:
    write_rrd_config(
        omd_root,
        services={SERVICE: object_config(cfs=("AVERAGE", "MAX"), rras=((50.0, 1, 200),))},
    )
    rrd = make_cmc_rrd(rrd_paths, {"load1": 10.0})

    convert(rrd_paths, HOST)

    assert layout(rrd) == (60, ["RRA:AVERAGE:0.50:1:200", "RRA:MAX:0.50:1:200"])


def test_cmc_rrd_keeps_its_data_when_converted(omd_root: Path, rrd_paths: RRDPaths) -> None:
    write_rrd_config(omd_root, services={SERVICE: object_config(rras=((50.0, 1, 200),))})
    rrd = make_cmc_rrd(rrd_paths, {"load1": 10.0, "load5": 20.0})

    convert(rrd_paths, HOST)

    assert past_data(rrd) == {"1": [10.0] * UPDATES, "2": [20.0] * UPDATES}


def test_pnp_rrd_with_configured_layout_is_left_alone(omd_root: Path, rrd_paths: RRDPaths) -> None:
    write_rrd_config(omd_root, services={SERVICE: object_config(rrd_format="pnp_multiple")})
    make_pnp_rrds(rrd_paths, {"load1": 10.0})
    inode = pnp_rrd_file(rrd_paths, "load1").stat().st_ino

    convert(rrd_paths, HOST)

    assert pnp_rrd_file(rrd_paths, "load1").stat().st_ino == inode


def test_pnp_rrd_gets_the_configured_layout(omd_root: Path, rrd_paths: RRDPaths) -> None:
    write_rrd_config(
        omd_root,
        services={
            SERVICE: object_config(
                cfs=("AVERAGE", "MAX"), rras=((50.0, 1, 200),), rrd_format="pnp_multiple"
            )
        },
    )
    make_pnp_rrds(rrd_paths, {"load1": 10.0})

    convert(rrd_paths, HOST)

    assert layout(pnp_rrd_file(rrd_paths, "load1")) == (
        60,
        ["RRA:AVERAGE:0.50:1:200", "RRA:MAX:0.50:1:200"],
    )


def test_pnp_rrd_keeps_its_data_when_converted(omd_root: Path, rrd_paths: RRDPaths) -> None:
    write_rrd_config(
        omd_root,
        services={SERVICE: object_config(rras=((50.0, 1, 200),), rrd_format="pnp_multiple")},
    )
    make_pnp_rrds(rrd_paths, {"load1": 10.0})

    convert(rrd_paths, HOST)

    assert past_data(pnp_rrd_file(rrd_paths, "load1")) == {"1": [10.0] * UPDATES}


def test_single_pnp_rrd_is_left_alone_without_split(omd_root: Path, rrd_paths: RRDPaths) -> None:
    write_rrd_config(omd_root, services={SERVICE: object_config(rrd_format="pnp_multiple")})
    make_single_pnp_rrd(rrd_paths, {"load1": 10.0, "load5": 20.0})
    host_dir = rrd_paths.pnp_host_dir(HOST)
    files = {path: path.read_bytes() for path in host_dir.iterdir()}

    convert(rrd_paths, HOST)

    assert {path: path.read_bytes() for path in host_dir.iterdir()} == files


def test_single_pnp_rrd_without_split_points_to_split_option(
    omd_root: Path, rrd_paths: RRDPaths, capsys: pytest.CaptureFixture[str]
) -> None:
    write_rrd_config(omd_root, services={SERVICE: object_config(rrd_format="pnp_multiple")})
    make_single_pnp_rrd(rrd_paths, {"load1": 10.0, "load5": 20.0})

    convert(rrd_paths, HOST)

    assert "storage type single, use --split-rrds to split this up." in capsys.readouterr().err


def test_split_moves_each_metric_into_its_own_rrd(omd_root: Path, rrd_paths: RRDPaths) -> None:
    write_rrd_config(omd_root, services={SERVICE: object_config(rrd_format="pnp_multiple")})
    make_single_pnp_rrd(rrd_paths, {"load1": 10.0, "load5": 20.0})

    convert(rrd_paths, HOST, split=True)

    assert {
        metric: past_data(pnp_rrd_file(rrd_paths, metric)) for metric in ("load1", "load5")
    } == {"load1": {"1": [10.0] * UPDATES}, "load5": {"1": [20.0] * UPDATES}}


def test_split_points_the_xml_file_to_the_new_rrds(omd_root: Path, rrd_paths: RRDPaths) -> None:
    write_rrd_config(omd_root, services={SERVICE: object_config(rrd_format="pnp_multiple")})
    make_single_pnp_rrd(rrd_paths, {"load1": 10.0, "load5": 20.0})

    convert(rrd_paths, HOST, split=True)

    root = ET.parse(pnp_xml_file(rrd_paths)).getroot()
    assert {
        "datasources": [
            {tag: datasource.findtext(tag) for tag in ("NAME", "RRDFILE", "DS", "RRD_STORAGE_TYPE")}
            for datasource in root.iter("DATASOURCE")
        ],
        "rrdfile": root.findtext("NAGIOS_RRDFILE"),
    } == {
        "datasources": [
            {
                "NAME": "load1",
                "RRDFILE": str(site_path(rrd_paths, pnp_rrd_file(rrd_paths, "load1"))),
                "DS": "1",
                "RRD_STORAGE_TYPE": "MULTIPLE",
            },
            {
                "NAME": "load5",
                "RRDFILE": str(site_path(rrd_paths, pnp_rrd_file(rrd_paths, "load5"))),
                "DS": "1",
                "RRD_STORAGE_TYPE": "MULTIPLE",
            },
        ],
        "rrdfile": "",
    }


def test_split_keeps_the_other_pnp_data_in_the_xml_file(
    omd_root: Path, rrd_paths: RRDPaths
) -> None:
    write_rrd_config(omd_root, services={SERVICE: object_config(rrd_format="pnp_multiple")})
    make_single_pnp_rrd(rrd_paths, {"load1": 10.0, "load5": 20.0})

    convert(rrd_paths, HOST, split=True)

    root = ET.parse(pnp_xml_file(rrd_paths)).getroot()
    assert {
        "templates": [datasource.findtext("TEMPLATE") for datasource in root.iter("DATASOURCE")],
        "version": root.findtext("XML/VERSION"),
    } == {"templates": [PNP_TEMPLATE, PNP_TEMPLATE], "version": PNP_XML_VERSION}


def test_split_removes_the_single_rrd(omd_root: Path, rrd_paths: RRDPaths) -> None:
    write_rrd_config(omd_root, services={SERVICE: object_config(rrd_format="pnp_multiple")})
    make_single_pnp_rrd(rrd_paths, {"load1": 10.0, "load5": 20.0})

    convert(rrd_paths, HOST, split=True)

    assert not single_pnp_rrd_file(rrd_paths).exists()


def test_pnp_rrds_are_converted_to_cmc_rrd(omd_root: Path, rrd_paths: RRDPaths) -> None:
    write_rrd_config(omd_root, services={SERVICE: object_config()})
    make_pnp_rrds(rrd_paths, {"load1": 10.0, "load5": 20.0})

    convert(rrd_paths, HOST)

    assert past_data(existing_path(rrd_paths.cmc_storage(HOST, SERVICE).path(".rrd"))) == {
        "1": [10.0] * UPDATES,
        "2": [20.0] * UPDATES,
    }


def test_cmc_rrd_converted_from_pnp_names_the_metrics(omd_root: Path, rrd_paths: RRDPaths) -> None:
    write_rrd_config(omd_root, services={SERVICE: object_config()})
    make_pnp_rrds(rrd_paths, {"load1": 10.0, "load5": 20.0})

    convert(rrd_paths, HOST)

    assert existing_path(rrd_paths.cmc_storage(HOST, SERVICE).path(".info")).read_text() == (
        "HOST heute\nSERVICE CPU load\nMETRICS load1;load5\n"
    )


def test_pnp_rrds_left_after_conversion_are_reported(
    omd_root: Path, rrd_paths: RRDPaths, capsys: pytest.CaptureFixture[str]
) -> None:
    write_rrd_config(omd_root, services={SERVICE: object_config()})
    make_pnp_rrds(rrd_paths, {"load1": 10.0})

    convert(rrd_paths, HOST)

    assert (
        "WARNING: Duplicate RRDs for heute/CPU load. Use --delete-rrds for cleanup."
        in capsys.readouterr().out
    )


def test_pnp_rrds_are_deleted_after_conversion_on_request(
    omd_root: Path, rrd_paths: RRDPaths
) -> None:
    write_rrd_config(omd_root, services={SERVICE: object_config()})
    make_pnp_rrds(rrd_paths, {"load1": 10.0, "load5": 20.0})

    convert(rrd_paths, HOST, delete=True)

    assert list(rrd_paths.pnp_host_dir(HOST).iterdir()) == []


def test_conversion_of_cmc_rrd_to_pnp_is_reported_as_unsupported(
    omd_root: Path, rrd_paths: RRDPaths, capsys: pytest.CaptureFixture[str]
) -> None:
    write_rrd_config(omd_root, services={SERVICE: object_config(rrd_format="pnp_multiple")})
    make_cmc_rrd(rrd_paths, {"load1": 10.0})

    convert(rrd_paths, HOST)

    assert (
        "WARNING: Converting RRD format CMC into PNP not implemented (heute/CPU load)"
        in capsys.readouterr().out
    )


def test_xml_file_referring_to_missing_rrd_is_reported(
    omd_root: Path, rrd_paths: RRDPaths, capsys: pytest.CaptureFixture[str]
) -> None:
    write_rrd_config(omd_root, services={SERVICE: object_config(rrd_format="pnp_multiple")})
    missing_rrd = site_path(rrd_paths, pnp_rrd_file(rrd_paths, "load1"))
    write_pnp_xml(
        pnp_xml_file(rrd_paths), storage_type="MULTIPLE", datasources=[("load1", missing_rrd, "1")]
    )

    convert(rrd_paths, HOST)

    assert (
        f"WARNING: XML {pnp_xml_file(rrd_paths)} refers to not existing RRD {missing_rrd}."
        " Nothing to convert. Cleanup the XML file manually in case this is OK."
    ) in capsys.readouterr().out


def test_data_source_without_rrd_does_not_stop_conversion_of_others(
    omd_root: Path, rrd_paths: RRDPaths
) -> None:
    write_rrd_config(
        omd_root,
        services={SERVICE: object_config(rras=((50.0, 1, 200),), rrd_format="pnp_multiple")},
    )
    rrd = pnp_rrd_file(rrd_paths, "load5")
    make_rrd(rrd, ds_values=[20.0], layout=SMALL_LAYOUT)
    write_pnp_xml(
        pnp_xml_file(rrd_paths),
        storage_type="MULTIPLE",
        datasources=[("load1", None, "1"), ("load5", rrd, "1")],
    )

    convert(rrd_paths, HOST)

    assert layout(rrd) == (60, ["RRA:AVERAGE:0.50:1:200"])


def test_broken_host_does_not_stop_conversion_of_others(
    omd_root: Path, rrd_paths: RRDPaths
) -> None:
    broken = HostName("broken")
    broken_info = rrd_paths.cmc_host_dir(broken) / "Broken.info"
    broken_info.parent.mkdir(parents=True)
    broken_info.write_text("garbage\n")
    write_rrd_config(omd_root, services={SERVICE: object_config(rras=((50.0, 1, 200),))})
    rrd = make_cmc_rrd(rrd_paths, {"load1": 10.0})

    convert(rrd_paths, broken, HOST)

    assert layout(rrd) == (60, ["RRA:AVERAGE:0.50:1:200"])


def test_all_hosts_with_rrd_configuration_are_converted_by_default(
    omd_root: Path, rrd_paths: RRDPaths
) -> None:
    hostnames = [HostName("heute"), HostName("morgen")]
    for hostname in hostnames:
        write_rrd_config(omd_root, hostname, services={SERVICE: object_config(step=30)})
    rrds = [make_cmc_rrd(rrd_paths, {"load1": 10.0}, hostname=hostname) for hostname in hostnames]

    convert(rrd_paths)

    assert [layout(rrd)[0] for rrd in rrds] == [30, 30]
