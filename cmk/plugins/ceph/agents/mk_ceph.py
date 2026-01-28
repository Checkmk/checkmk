#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

import json
import os
import os.path
import socket
import sys
from typing import Any

__version__ = "2.6.0b1"


def _bail_out_missing_dependency() -> int:
    pip = "pip3" if sys.version_info.major == 3 else "pip"
    error = (
        "Error: mk_ceph requires the library 'rados'."
        " Please install it on the monitored system (%s install rados)." % pip
    )
    sys.stdout.write("<<<cephstatus:sep(0)>>>\n%s\n" % json.dumps({"deployment_error": error}))
    # exit successfully s.t. the agent won't discard stdout
    return 0


def _output_json_section(name, data):
    sys.stdout.write(f"<<<{name}:sep(0)>>>\n{json.dumps(data)}\n")


class RadosCMD:
    def __init__(self, client: Any) -> None:
        self.client = client

    def command_mon(self, cmd, params=None):
        data = {"prefix": cmd, "format": "json"}
        if params:
            data.update(params)
        return self.client.mon_command(json.dumps(data), b"", timeout=5)

    def command_mgr(self, cmd):
        return self.client.mgr_command(
            json.dumps({"prefix": cmd, "format": "json"}), b"", timeout=5
        )

    def command_osd(self, osdid, cmd):
        return self.client.osd_command(
            osdid, json.dumps({"prefix": cmd, "format": "json"}), b"", timeout=5
        )

    def command_pg(self, pgid, cmd):
        return self.client.pg_command(
            pgid, json.dumps({"prefix": cmd, "format": "json"}), b"", timeout=5
        )


def _load_plugin_config(mk_confdir: str) -> tuple[str, str]:
    ceph_config = "/etc/ceph/ceph.conf"
    ceph_client = "client.admin"

    try:
        with open(os.path.join(mk_confdir, "ceph.cfg")) as config:
            content = config.readlines()
    except FileNotFoundError:
        return ceph_config, ceph_client

    for line in content:
        if "=" not in line:
            continue
        key, value = line.strip().split("=")
        if key == "CONFIG":
            ceph_config = value
        if key == "CLIENT":
            ceph_client = value

    return ceph_config, ceph_client


def _make_bluefs_section(raw, hostname, fqdn, fsid):
    # type: (str, str, str, str) -> tuple[dict, list]
    localosds = []
    out = {"end": {}}  # type: dict
    for osd in json.loads(raw):
        if osd.get("hostname") in [hostname, fqdn]:
            localosds.append(osd["id"])
            if "container_hostname" in osd:
                adminsocket = "/run/ceph/%s/ceph-osd.%d.asok" % (fsid, osd["id"])
            else:
                adminsocket = "/run/ceph/ceph-osd.%d.asok" % osd["id"]
            if os.path.exists(adminsocket):
                chunks: list[bytes] = []
                try:
                    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    sock.connect(adminsocket)
                    sock.sendall(b'{"prefix": "perf dump"}\n')
                    sock.shutdown(socket.SHUT_WR)
                    while len(chunks) == 0 or chunks[-1] != b"":
                        chunks.append(sock.recv(4096))
                    sock.close()
                    chunks[0] = chunks[0][4:]
                except Exception:
                    chunks = [b'{"bluefs": {}}']
                out[osd["id"]] = {"bluefs": json.loads(b"".join(chunks))["bluefs"]}
    return out, localosds


def _make_osd_section(raw_df, raw_perf, localosds):
    # type: (str, str, list) -> dict
    osddf = json.loads(raw_df)
    osdperf = json.loads(raw_perf)
    osds = []
    for osd in osddf["nodes"]:
        if osd["id"] in localosds:
            osds.append(osd)
    perfs = []
    if "osd_perf_infos" in osdperf:
        for osd in osdperf["osd_perf_infos"]:
            if osd["id"] in localosds:
                perfs.append(osd)
    if "osdstats" in osdperf and "osd_perf_infos" in osdperf["osdstats"]:
        for osd in osdperf["osdstats"]["osd_perf_infos"]:
            if osd["id"] in localosds:
                perfs.append(osd)

    return {"df": {"nodes": osds}, "perf": {"osd_perf_infos": perfs}}


def main() -> int:
    try:
        # We must not exit (not even successfully) upon import in case
        # we're importing this module for testing purposes.
        # I guess the right thing to do would be to add 'rados' as a dev
        # dependency and write *actual* tests.
        from rados import Rados  # type: ignore[import-not-found]
    except ImportError:
        return _bail_out_missing_dependency()

    ceph_config, ceph_client = _load_plugin_config(os.environ["MK_CONFDIR"])

    cluster = RadosCMD(Rados(conffile=ceph_config, name=ceph_client))
    cluster.client.connect()

    hostname = socket.gethostname().split(".", 1)[0]
    fqdn = socket.getfqdn()

    res = cluster.command_mon("status")
    if res[0] != 0:
        fsid = ""
    else:
        status = json.loads(res[1])
        fsid = status.get("fsid", "")
        # only on MON hosts
        mons = status.get("quorum_names", [])
        if hostname in mons or fqdn in mons:
            _output_json_section("cephstatus", status)

            res = cluster.command_mon("df", params={"detail": "detail"})
            if res[0] == 0:
                _output_json_section("cephdf", json.loads(res[1]))

    res = cluster.command_mon("osd metadata")
    if res[0] == 0:
        section, localosds = _make_bluefs_section(res[1], hostname, fqdn, fsid)
        _output_json_section("cephosdbluefs", section)
    else:
        localosds = []

    osddf_raw = cluster.command_mon("osd df")
    osdperf_raw = cluster.command_mon("osd perf")
    if osddf_raw[0] == 0 and osdperf_raw[0] == 0:
        _output_json_section("cephosd", _make_osd_section(osddf_raw[1], osdperf_raw[1], localosds))

    return 0


if __name__ == "__main__":
    sys.exit(main())
