#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
r"""Check_MK Agent Plugin: mk_docker.py

This plugin is configured using an ini-style configuration file,
i.e. a file with lines of the form 'key: value'.
At 'agents/cfg_examples/mk_docker.cfg' (relative to the check_mk
source code directory ) you should find some example configuration
files. For more information on possible configurations refer to the
file docker.cfg in said directory.
The docker library must be installed on the system executing the
plugin ("pip install docker").

This plugin it will be called by the agent without any arguments.
"""

from __future__ import with_statement

__version__ = "2.1.0"

# this file has to work with both Python 2 and 3
# pylint: disable=super-with-arguments

# N O T E:
# docker is available for python versions from 2.6 / 3.3

import argparse
import configparser
import functools
import json
import logging
import multiprocessing
import os
import pathlib
import struct
import sys
import time

try:
    from typing import Dict, Tuple, Union
except ImportError:
    pass


def which(prg):
    for path in os.environ["PATH"].split(os.pathsep):
        if os.path.isfile(os.path.join(path, prg)) and os.access(os.path.join(path, prg), os.X_OK):
            return os.path.join(path, prg)
    return None


# The "import docker" checks below result in agent sections being created. This
# is a way to end the plugin in case it is being executed on a non docker host
if (
    not os.path.isfile("/var/lib/docker")
    and not os.path.isfile("/var/run/docker")
    and not which("docker")
):
    sys.stderr.write("mk_docker.py: Does not seem to be a docker host. Terminating.\n")
    sys.exit(1)

try:
    import docker  # type: ignore[import]
except ImportError:
    sys.stdout.write(
        "<<<docker_node_info:sep(124)>>>\n"
        "@docker_version_info|{}\n"
        '{"Critical": "Error: mk_docker requires the docker library.'
        ' Please install it on the monitored system (%s install docker)."}\n'
        % ("pip3" if sys.version_info.major == 3 else "pip")
    )
    sys.exit(0)

if int(docker.__version__.split(".", 1)[0]) < 2:
    sys.stdout.write(
        "<<<docker_node_info:sep(124)>>>\n"
        "@docker_version_info|{}\n"
        '{"Critical": "Error: mk_docker requires the docker library >= 2.0.0.'
        ' Please install it on the monitored system (%s install docker)."}\n'
        % ("pip3" if sys.version_info.major == 3 else "pip")
    )
    sys.exit(0)

DEBUG = "--debug" in sys.argv[1:]

VERSION = "0.1"

DEFAULT_CFG_FILE = os.path.join(os.getenv("MK_CONFDIR", ""), "docker.cfg")

DEFAULT_CFG_SECTION = {
    "base_url": "unix://var/run/docker.sock",
    "skip_sections": "",
    "container_id": "short",
}

LOGGER = logging.getLogger(__name__)


def parse_arguments(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    prog, descr, epilog = __doc__.split("\n\n")
    parser = argparse.ArgumentParser(prog=prog, description=descr, epilog=epilog)
    parser.add_argument(
        "--debug", action="store_true", help="""Debug mode: raise Python exceptions"""
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="""Verbose mode (for even more output use -vvv)""",
    )
    parser.add_argument(
        "-c",
        "--config-file",
        default=DEFAULT_CFG_FILE,
        help="""Read config file (default: $MK_CONFDIR/docker.cfg)""",
    )

    args = parser.parse_args(argv)

    fmt = "%%(levelname)5s: %s%%(message)s"
    if args.verbose == 0:
        LOGGER.propagate = False
    elif args.verbose == 1:
        logging.basicConfig(level=logging.INFO, format=fmt % "")
    else:
        logging.basicConfig(level=logging.DEBUG, format=fmt % "(line %(lineno)3d) ")
    if args.verbose < 3:
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    LOGGER.debug("parsed args: %r", args)
    return args


def get_config(cfg_file):
    config = configparser.ConfigParser(DEFAULT_CFG_SECTION)
    LOGGER.debug("trying to read %r", cfg_file)
    files_read = config.read(cfg_file)
    LOGGER.info("read configration file(s): %r", files_read)
    section_name = "DOCKER" if config.sections() else "DEFAULT"
    conf_dict = dict(config.items(section_name))  # type: Dict[str, Union[str, Tuple]]
    skip_sections = conf_dict.get("skip_sections", "")
    if isinstance(skip_sections, str):
        skip_list = skip_sections.split(",")
        conf_dict["skip_sections"] = tuple(n.strip() for n in skip_list)

    return conf_dict


class Section(list):
    """a very basic agent section class"""

    _OUTPUT_LOCK = multiprocessing.Lock()

    version_info = {
        "PluginVersion": VERSION,
        "DockerPyVersion": docker.version,
    }

    # Should we need to parallelize one day, change this to be
    # more like the Section class in agent_azure, for instance
    def __init__(self, name=None, piggytarget=None):
        super(Section, self).__init__()
        if piggytarget is not None:
            self.append("<<<<%s>>>>" % piggytarget)
        if name is not None:
            self.append("<<<docker_%s:sep(124)>>>" % name)
            version_json = json.dumps(Section.version_info)
            self.append("@docker_version_info|%s" % version_json)
            self.append("<<<docker_%s:sep(0)>>>" % name)

    def write(self):
        if self[0].startswith("<<<<"):
            self.append("<<<<>>>>")
        with self._OUTPUT_LOCK:
            for line in self:
                sys.stdout.write("%s\n" % line)
            sys.stdout.flush()


def report_exception_to_server(exc, location):
    LOGGER.info("handling exception: %s", exc)
    msg = "Plugin exception in %s: %s" % (location, exc)
    sec = Section("node_info")
    sec.append(json.dumps({"Unknown": msg}))
    sec.write()


class ParallelDfCall:
    """handle parallel calls of super().df()

    The Docker API will only allow one super().df() call at a time.
    This leads to problems when the plugin is executed multiple times
    in parallel.
    """

    def __init__(self, call):
        self._call = call
        self._vardir = pathlib.Path(os.getenv("MK_VARDIR", ""))
        self._spool_file = self._vardir / "mk_docker_df.spool"
        self._tmp_file_templ = "mk_docker_df.tmp.%s"
        self._my_tmp_file = self._vardir / (self._tmp_file_templ % os.getpid())

    def __call__(self):
        try:
            self._my_tmp_file.touch()
            data = self._new_df_result()
        except docker.errors.APIError as exc:
            LOGGER.debug("df API call failed: %s", exc)
            data = self._spool_df_result()
        else:
            # the API call succeeded, no need for any tmp files
            for file_ in self._iter_tmp_files():
                self._unlink(file_)
        finally:
            # what ever happens: remove my tmp file
            self._unlink(self._my_tmp_file)

        return data

    def _new_df_result(self):
        data = self._call()
        self._write_df_result(data)
        return data

    def _iter_tmp_files(self):
        return self._vardir.glob(self._tmp_file_templ % "*")

    @staticmethod
    def _unlink(file_):
        try:
            file_.unlink()
        except OSError:
            pass

    def _spool_df_result(self):
        # check every 0.1 seconds
        tick = 0.1
        # if the df command takes more than 60 seconds, you probably want to
        # execute the plugin asynchronously. This should cover a majority of cases.
        timeout = 60
        for _ in range(int(timeout / tick)):
            time.sleep(tick)
            if not any(self._iter_tmp_files()):
                break

        return self._read_df_result()

    def _write_df_result(self, data):
        with self._my_tmp_file.open("wb") as file_:
            file_.write(json.dumps(data).encode("utf-8"))
        self._my_tmp_file.rename(self._spool_file)

    def _read_df_result(self):
        """read from the spool file

        Don't handle FileNotFound - the plugin can deal with it, and it's easier to debug.
        """
        with self._spool_file.open() as file_:
            return json.loads(file_.read())


class MKDockerClient(docker.DockerClient):
    """a docker.DockerClient that caches containers and node info"""

    API_VERSION = "auto"
    _DEVICE_MAP_LOCK = multiprocessing.Lock()

    def __init__(self, config):
        super(MKDockerClient, self).__init__(config["base_url"], version=MKDockerClient.API_VERSION)
        all_containers = self.containers.list(all=True)
        if config["container_id"] == "name":
            self.all_containers = {c.attrs["Name"].lstrip("/"): c for c in all_containers}
        elif config["container_id"] == "long":
            self.all_containers = {c.attrs["Id"]: c for c in all_containers}
        else:
            self.all_containers = {c.attrs["Id"][:12]: c for c in all_containers}
        self._env = {"REMOTE": os.getenv("REMOTE", "")}
        self._container_stats = {}
        self._device_map = None
        self.node_info = self.info()

        self._df_caller = ParallelDfCall(call=super(MKDockerClient, self).df)

    def df(self):
        return self._df_caller()

    def device_map(self):
        with self._DEVICE_MAP_LOCK:
            if self._device_map is not None:
                return self._device_map

            self._device_map = {}
            for device in os.listdir("/sys/block"):
                with open("/sys/block/%s/dev" % device) as handle:
                    self._device_map[handle.read().strip()] = device

        return self._device_map

    @staticmethod
    def iter_socket(sock, descriptor):
        """iterator to recv data from container socket"""
        header = docker.utils.socket.read(sock, 8)
        while header:
            actual_descriptor, length = struct.unpack(">BxxxL", header)
            while length:
                data = docker.utils.socket.read(sock, length)
                length -= len(data)
                LOGGER.debug("Received data: %r", data)
                if actual_descriptor == descriptor:
                    yield data.decode("UTF-8")
            header = docker.utils.socket.read(sock, 8)

    def get_stdout(self, exec_return_val):
        """read stdout from container process"""
        if isinstance(exec_return_val, tuple):
            # it's a tuple since version 3.0.0
            exit_code, sock = exec_return_val
            if exit_code not in (0, None):
                return ""
        else:
            sock = exec_return_val

        return "".join(self.iter_socket(sock, 1))

    def run_agent(self, container):
        """run checkmk agent in container"""
        result = container.exec_run(["check_mk_agent"], environment=self._env, socket=True)
        return self.get_stdout(result)

    def get_container_stats(self, container_key):
        """return cached container stats"""
        try:
            return self._container_stats[container_key]
        except KeyError:
            pass

        container = self.all_containers[container_key]
        if not container.status == "running":
            return self._container_stats.setdefault(container_key, None)

        stats = container.stats(stream=False)
        return self._container_stats.setdefault(container_key, stats)


def time_it(func):
    """Decorator to time the function"""

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        before = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            LOGGER.info("%r took %ss", func.__name__, time.time() - before)

    return wrapped


@time_it
def set_version_info(client):
    data = client.version()
    LOGGER.debug(data)
    Section.version_info["ApiVersion"] = data.get("ApiVersion")


# .
#   .--Sections------------------------------------------------------------.
#   |                  ____            _   _                               |
#   |                 / ___|  ___  ___| |_(_) ___  _ __  ___               |
#   |                 \___ \ / _ \/ __| __| |/ _ \| '_ \/ __|              |
#   |                  ___) |  __/ (__| |_| | (_) | | | \__ \              |
#   |                 |____/ \___|\___|\__|_|\___/|_| |_|___/              |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def is_disabled_section(config, section_name):
    """Skip the section, if configured to do so"""
    if section_name in config["skip_sections"]:
        LOGGER.info("skipped section: %s", section_name)
        return True
    return False


@time_it
def section_node_info(client):
    LOGGER.debug(client.node_info)
    section = Section("node_info")
    section.append(json.dumps(client.node_info))
    section.write()


@time_it
def section_node_disk_usage(client):
    """docker system df"""
    section = Section("node_disk_usage")
    try:
        data = client.df()
    except docker.errors.APIError as exc:
        if DEBUG:
            raise
        section.write()
        LOGGER.exception(exc)
        return
    LOGGER.debug(data)

    def get_row(type_, instances, is_inactive, key="Size"):
        inactive = [i for i in instances if is_inactive(i)]
        item_data = {
            "type": type_,
            "size": sum(i.get(key, 0) for i in instances),
            "reclaimable": sum(i.get(key, 0) for i in inactive),
            "count": len(instances),
            "active": len(instances) - len(inactive),
        }
        return json.dumps(item_data)

    # images:
    images = data.get("Images") or []
    row = get_row("images", images, lambda i: i["Containers"] == 0)
    section.append(row)

    # containers:
    containers = data.get("Containers") or []
    row = get_row("containers", containers, lambda c: c["State"] != "running", key="SizeRw")
    section.append(row)

    # volumes
    volumes = [v.get("UsageData", {}) for v in data.get("Volumes") or []]
    if not any(-1 in v.values() for v in volumes):
        row = get_row("volumes", volumes, lambda v: v.get("RefCount", 0) == 0)
        section.append(row)

    # build_cache:
    build_cache = data.get("BuildCache") or []
    row = get_row("buildcache", build_cache, lambda b: b.get("InUse"))
    section.append(row)

    section.write()


@time_it
def section_node_images(client):
    """in subsections list [[[images]]] and [[[containers]]]"""
    section = Section("node_images")

    images = client.images.list()
    LOGGER.debug(images)
    section.append("[[[images]]]")
    for image in images:
        section.append(json.dumps(image.attrs))

    LOGGER.debug(client.all_containers)
    section.append("[[[containers]]]")
    for container in client.all_containers.values():
        section.append(json.dumps(container.attrs))

    section.write()


@time_it
def section_node_network(client):
    networks = client.networks.list(filters={"driver": "bridge"})
    section = Section("node_network")
    section += [json.dumps(n.attrs) for n in networks]
    section.write()


def section_container_node_name(client, container_id):
    node_name = client.node_info.get("Name")
    section = Section("container_node_name", piggytarget=container_id)
    section.append(json.dumps({"NodeName": node_name}))
    section.write()


def section_container_status(client, container_id):
    container = client.all_containers[container_id]
    status = container.attrs.get("State", {})

    healthcheck = container.attrs.get("Config", {}).get("Healthcheck")
    if healthcheck:
        status["Healthcheck"] = healthcheck
    restart_policy = container.attrs.get("HostConfig", {}).get("RestartPolicy")
    if restart_policy:
        status["RestartPolicy"] = restart_policy

    try:
        status["ImageTags"] = container.image.tags
    except docker.errors.ImageNotFound:
        # image has been removed while container is still running
        pass
    status["NodeName"] = client.node_info.get("Name")

    section = Section("container_status", piggytarget=container_id)
    section.append(json.dumps(status))
    section.write()


def section_container_labels(client, container_id):
    container = client.all_containers[container_id]
    section = Section("container_labels", piggytarget=container_id)
    section.append(json.dumps(container.labels))
    section.write()


def section_container_network(client, container_id):
    container = client.all_containers[container_id]
    network = container.attrs.get("NetworkSettings", {})
    section = Section("container_network", piggytarget=container_id)
    section.append(json.dumps(network))
    section.write()


def section_container_agent(client, container_id):
    container = client.all_containers[container_id]
    if container.status != "running":
        return True
    result = client.run_agent(container)
    success = "<<<check_mk>>>" in result
    if success:
        LOGGER.debug("running check_mk_agent in container %s: ok", container_id)
        section = Section(piggytarget=container_id)
        section.append(result)
        section.write()
    else:
        LOGGER.warning("running check_mk_agent in container %s failed: %s", container_id, result)
    return success


def section_container_mem(client, container_id):
    stats = client.get_container_stats(container_id)
    if stats is None:  # container not running
        return
    container_mem = stats["memory_stats"]
    section = Section("container_mem", piggytarget=container_id)
    section.append(json.dumps(container_mem))
    section.write()


def section_container_cpu(client, container_id):
    stats = client.get_container_stats(container_id)
    if stats is None:  # container not running
        return
    container_cpu = stats["cpu_stats"]
    section = Section("container_cpu", piggytarget=container_id)
    section.append(json.dumps(container_cpu))
    section.write()


def section_container_diskstat(client, container_id):
    stats = client.get_container_stats(container_id)
    if stats is None:  # container not running
        return
    container_blkio = stats["blkio_stats"]
    container_blkio["time"] = time.time()
    container_blkio["names"] = client.device_map()
    section = Section("container_diskstat", piggytarget=container_id)
    section.append(json.dumps(container_blkio))
    section.write()


NODE_SECTIONS = (
    ("docker_node_info", section_node_info),
    ("docker_node_disk_usage", section_node_disk_usage),
    ("docker_node_images", section_node_images),
    ("docker_node_network", section_node_network),
)

CONTAINER_API_SECTIONS = (
    ("docker_container_node_name", section_container_node_name),
    ("docker_container_status", section_container_status),
    ("docker_container_labels", section_container_labels),
    ("docker_container_network", section_container_network),
)

CONTAINER_API_SECTIONS_NO_AGENT = (
    ("docker_container_mem", section_container_mem),
    ("docker_container_cpu", section_container_cpu),
    ("docker_container_diskstat", section_container_diskstat),
)


def call_node_sections(client, config):
    for name, section in NODE_SECTIONS:
        if is_disabled_section(config, name):
            continue
        try:
            section(client)
        except Exception as exc:
            if DEBUG:
                raise
            report_exception_to_server(exc, section.__name__)


def call_container_sections(client, config):
    jobs = []
    for container_id in client.all_containers:
        job = multiprocessing.Process(
            target=_call_single_containers_sections, args=(client, config, container_id)
        )
        job.start()
        jobs.append(job)

    for job in jobs:
        job.join()


def _call_single_containers_sections(client, config, container_id):
    LOGGER.info("container id: %s", container_id)
    for name, section in CONTAINER_API_SECTIONS:
        if is_disabled_section(config, name):
            continue
        try:
            section(client, container_id)
        except Exception as exc:
            if DEBUG:
                raise
            report_exception_to_server(exc, section.__name__)

    agent_success = False
    if not is_disabled_section(config, "docker_container_agent"):
        try:
            agent_success = section_container_agent(client, container_id)
        except Exception as exc:
            if DEBUG:
                raise
            report_exception_to_server(exc, "section_container_agent")
    if agent_success:
        return

    for name, section in CONTAINER_API_SECTIONS_NO_AGENT:
        if is_disabled_section(config, name):
            continue
        try:
            section(client, container_id)
        except Exception as exc:
            if DEBUG:
                raise
            report_exception_to_server(exc, section.__name__)


# .
#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def main():

    args = parse_arguments()
    config = get_config(args.config_file)

    try:  # first calls by docker-daemon: report failure
        client = MKDockerClient(config)
    except Exception as exc:
        if DEBUG:
            raise
        report_exception_to_server(exc, "MKDockerClient.__init__")
        sys.exit(0)

    set_version_info(client)

    call_node_sections(client, config)

    call_container_sections(client, config)


if __name__ == "__main__":
    main()
