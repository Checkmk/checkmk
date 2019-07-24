#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2018             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
r"""Check_MK Agent Plugin: mk_docker.py

This plugin is configured using an ini-style configuration file,
i.e. a file with lines of the form 'key: value'.
At 'agents/cfg_examples/mk_docker.cfg' (relative to the check_mk
source code directory ) you should find some example configuration
files. For more information on possible configurations refer to the
file docker.cfg in said directory.
The docker-py library must be installed on the system executing the
plugin ("pip install docker").

This plugin it will be called by the agent without any arguments.
"""
# N O T E:
# docker-py is available for python verisons from 2.6 / 3.3

import os
import sys
import time
import json
import struct
import argparse
import functools
import subprocess
import logging

try:
    import ConfigParser as configparser
except ImportError:  # Python3
    import configparser

try:
    import docker
except ImportError:
    sys.stdout.write('<<<docker_node_info:sep(124)>>>\n'
                     '@docker_version_info|{}\n'
                     '{"Critical": "Error: mk_docker requires the docker library.'
                     ' Please install it on the monitored system (pip install docker)."}\n')
    sys.exit(1)

DEBUG = "--debug" in sys.argv[1:]

VERSION = "0.1"

DEFAULT_CFG_FILE = os.path.join(os.getenv('MK_CONFDIR', ''), "docker.cfg")

DEFAULT_CFG_SECTION = {
    "base_url": "unix://var/run/docker.sock",
    "skip_sections": "",
    "container_id": "short",
}

LOGGER = logging.getLogger(__name__)


def parse_arguments(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    prog, descr, epilog = __doc__.split('\n\n')
    parser = argparse.ArgumentParser(prog=prog, description=descr, epilog=epilog)
    parser.add_argument("--debug",
                        action="store_true",
                        help='''Debug mode: raise Python exceptions''')
    parser.add_argument("-v",
                        "--verbose",
                        action="count",
                        default=0,
                        help='''Verbose mode (for even more output use -vvv)''')
    parser.add_argument("-c",
                        "--config-file",
                        default=DEFAULT_CFG_FILE,
                        help='''Read config file (default: $MK_CONFDIR/docker.cfg)''')

    args = parser.parse_args(argv)

    fmt = "%%(levelname)5s: %s%%(message)s"
    if args.verbose == 0:
        LOGGER.propagate = False
    elif args.verbose == 1:
        logging.basicConfig(level=logging.INFO, format=fmt % "")
    else:
        logging.basicConfig(level=logging.DEBUG, format=fmt % "(line %(lineno)3d) ")
    if args.verbose < 3:
        logging.getLogger('urllib3').setLevel(logging.WARNING)

    LOGGER.debug("parsed args: %r", args)
    return args


def get_config(cfg_file):
    config = configparser.ConfigParser(DEFAULT_CFG_SECTION)
    LOGGER.debug("trying to read %r", cfg_file)
    files_read = config.read(cfg_file)
    LOGGER.info("read configration file(s): %r", files_read)
    section_name = "DOCKER" if config.sections() else "DEFAULT"
    conf_dict = dict(config.items(section_name))

    skip_list = conf_dict.get("skip_sections", "").split(',')
    conf_dict["skip_sections"] = tuple(n.strip() for n in skip_list)

    return conf_dict


class Section(list):
    '''a very basic agent section class'''
    version_info = {
        'PluginVersion': VERSION,
        'DockerPyVersion': docker.version,
    }

    # Should we need to parallelize one day, change this to be
    # more like the Section class in agent_azure, for instance
    def __init__(self, name=None, separator=0, piggytarget=None):
        super(Section, self).__init__()
        self.sep = chr(separator)
        if piggytarget is not None:
            self.append('<<<<%s>>>>' % piggytarget)
        if name is not None:
            self.append('<<<docker_%s:sep(%d)>>>' % (name, separator))
            version_json = json.dumps(Section.version_info)
            self.append(self.sep.join(('@docker_version_info', version_json)))

    def write(self):
        if self[0].startswith('<<<<'):
            self.append('<<<<>>>>')
        for line in self:
            sys.stdout.write("%s\n" % line)


def report_exception_to_server(exc, location):
    LOGGER.info("handling exception: %s", exc)
    msg = "Plugin exception in %s: %s" % (location, exc)
    sec = Section('node_info')
    sec.append(json.dumps({"Unknown": msg}))
    sec.write()


class MKDockerClient(docker.DockerClient):
    '''a docker.DockerClient that caches containers and node info'''
    API_VERSION = "auto"

    def __init__(self, config):
        super(MKDockerClient, self).__init__(config['base_url'], version=MKDockerClient.API_VERSION)
        all_containers = self.containers.list(all=True)
        if config['container_id'] == "name":
            self.all_containers = {c.attrs["Name"].lstrip('/'): c for c in all_containers}
        elif config['container_id'] == "long":
            self.all_containers = {c.attrs["Id"]: c for c in all_containers}
        else:
            self.all_containers = {c.attrs["Id"][:12]: c for c in all_containers}
        self.node_info = self.info()


class AgentDispatcher(object):
    '''AgentDispatcher is responsible for running a check_mk_agent inside a container

    If the check_mk agent is installed in the countainer, run it.
    Otherwise execute the agent of the node in the context of the container.
    Using this approach we should always get at least basic information from
    the container.
    Once it comes to plugins and custom configuration the user needs to use
    a little more complex setup. Have a look at the documentation.
    '''
    @staticmethod
    def iter_socket(sock, descriptor):
        header = sock.recv(8)
        while header:
            actual_descriptor, length = struct.unpack('>BxxxL', header)
            while length:
                data = sock.recv(length)
                length -= len(data)
                LOGGER.debug("Received data: %r", data)
                if actual_descriptor == descriptor:
                    yield data
            header = sock.recv(8)

    def get_stdout(self, exec_return_val):
        if isinstance(exec_return_val, tuple):
            # it's a tuple since version 3.0.0
            exit_code, sock = exec_return_val
            if exit_code not in (0, None):
                return ''
        else:
            sock = exec_return_val

        return ''.join(self.iter_socket(sock, 1))

    def __init__(self):
        remote = os.getenv("REMOTE", "")
        self.env = {"REMOTE": remote}
        self.env_from_node = {"REMOTE": remote, "MK_FROM_NODE": "1"}
        self._agent_code = None
        self.agent_code_exc = None

    def _read_agent_code(self):
        LOGGER.debug("reading agent code")
        try:
            agent_file = subprocess.check_output(['which', 'check_mk_agent']).strip()
            LOGGER.debug("source file: %s", agent_file)
            source = open(agent_file).read()
            self._agent_code = source + "\nexit\n"
        except () if DEBUG else (subprocess.CalledProcessError, IOError) as exc:
            self.agent_code_exc = exc

    @property
    def agent_code(self):
        if self._agent_code is None and self.agent_code_exc is None:
            self._read_agent_code()
        return self._agent_code

    def check_container(self, container):
        '''run check_mk agent in container or container context'''

        LOGGER.debug("trying to run containers check_mk_agent")
        result = container.exec_run(['sh', '-c', 'check_mk_agent'],
                                    environment=self.env,
                                    socket=True)
        output = self.get_stdout(result)
        if output:
            LOGGER.info("successfully ran containers check_mk_agent")
            return output
        LOGGER.info("container has no agent or executing agent failed")

        # check for agent code and bash:
        if not self.agent_code:
            LOGGER.info("failed to load agent code: %s", self.agent_code_exc)
            return None
        result = container.exec_run(['sh', '-c', 'bash -c echo'], socket=True)
        if not self.get_stdout(result):
            LOGGER.info("failed to run bash in container")
            return None

        result = container.exec_run('bash',
                                    environment=self.env_from_node,
                                    socket=True,
                                    stdin=True,
                                    stderr=False)
        try:
            nbytes = result.sendall(self.agent_code)
        except AttributeError:
            # it's a tuple since version 3.0.0
            nbytes = result[1].sendall(self.agent_code)
        LOGGER.debug("sent agent to container (%d bytes)", nbytes)
        agent_ouput = self.get_stdout(result)
        LOGGER.info("successfully ran check_mk_agent that was sent to container")
        return agent_ouput


def time_it(func):
    '''Decorator to time the function'''
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        before = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            LOGGER.info("%r took %ss", func.func_name, time.time() - before)

    return wrapped


@time_it
def set_version_info(client):
    data = client.version()
    LOGGER.debug(data)
    Section.version_info['ApiVersion'] = data.get('ApiVersion')


#.
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
    '''Skip the section, if configured to do so'''
    if section_name in config["skip_sections"]:
        LOGGER.info("skipped section: %s", section_name)
        return True
    return False


@time_it
def section_node_info(client):
    LOGGER.debug(client.node_info)
    section = Section('node_info')
    section.append(json.dumps(client.node_info))
    section.write()


@time_it
def section_node_disk_usage(client):
    '''docker system df'''
    section = Section('node_disk_usage')
    try:
        data = client.df()
    except () if DEBUG else docker.errors.APIError as exc:
        section.write()
        LOGGER.exception(exc)
        return
    LOGGER.debug(data)

    def get_row(type_, instances, is_inactive, key='Size'):
        inactive = [i for i in instances if is_inactive(i)]
        item_data = {
            'type': type_,
            'size': sum(i.get(key, 0) for i in instances),
            'reclaimable': sum(i.get(key, 0) for i in inactive),
            'count': len(instances),
            'active': len(instances) - len(inactive),
        }
        return json.dumps(item_data)

    # images:
    images = data.get('Images') or []
    row = get_row('images', images, lambda i: i['Containers'] == 0)
    section.append(row)

    # containers:
    containers = data.get('Containers') or []
    row = get_row('containers', containers, lambda c: c['State'] != 'running', key='SizeRw')
    section.append(row)

    # volumes
    volumes = [v.get('UsageData', {}) for v in data.get('Volumes') or []]
    if not any(-1 in v.values() for v in volumes):
        row = get_row('volumes', volumes, lambda v: v.get('RefCount', 0) == 0)
        section.append(row)

    # build_cache:
    build_cache = data.get('BuildCache') or []
    row = get_row('buildcache', build_cache, lambda b: b.get('InUse'))
    section.append(row)

    section.write()


@time_it
def section_node_images(client):
    '''in subsections list [[[images]]] and [[[containers]]]'''
    section = Section('node_images')

    images = client.images.list()
    LOGGER.debug(images)
    section.append('[[[images]]]')
    for image in images:
        section.append(json.dumps(image.attrs))

    LOGGER.debug(client.all_containers)
    section.append('[[[containers]]]')
    for container in client.all_containers.itervalues():
        section.append(json.dumps(container.attrs))

    section.write()


@time_it
def section_node_network(client):
    networks = client.networks.list(filters={'driver': 'bridge'})
    section = Section('node_network')
    section += [json.dumps(n.attrs) for n in networks]
    section.write()


def section_container_node_name(client, container_id):
    node_name = client.node_info.get("Name")
    section = Section('container_node_name', piggytarget=container_id)
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
    section = Section('container_status', piggytarget=container_id)
    section.append(json.dumps(status))
    section.write()


def section_container_labels(client, container_id):
    container = client.all_containers[container_id]
    section = Section('container_labels', piggytarget=container_id)
    section.append(json.dumps(container.labels))
    section.write()


def section_container_network(client, container_id):
    container = client.all_containers[container_id]
    network = container.attrs.get("NetworkSettings", {})
    section = Section('container_network', piggytarget=container_id)
    section.append(json.dumps(network))
    section.write()


def section_container_agent(client, container_id, dispatcher):
    result = dispatcher.check_container(client.all_containers[container_id])
    if not result:
        return
    section = Section(piggytarget=container_id)
    section.append(result)
    section.write()


NODE_SECTIONS = (
    ('docker_node_info', section_node_info),
    ('docker_node_disk_usage', section_node_disk_usage),
    ('docker_node_images', section_node_images),
    ('docker_node_network', section_node_network),
)

CONTAINER_API_SECTIONS = (
    ('docker_container_node_name', section_container_node_name),
    ('docker_container_status', section_container_status),
    ('docker_container_labels', section_container_labels),
    ('docker_container_network', section_container_network),
)


def call_node_sections(client, config):
    for name, section in NODE_SECTIONS:
        if is_disabled_section(config, name):
            continue
        try:
            section(client)
        except () if DEBUG else Exception as exc:
            report_exception_to_server(exc, section.func_name)


def call_container_sections(client, config):
    dispatcher = AgentDispatcher()
    for container_id, container in client.all_containers.iteritems():
        LOGGER.info("container id: %s", container_id)
        for name, section in CONTAINER_API_SECTIONS:
            if is_disabled_section(config, name):
                continue
            try:
                section(client, container_id)
            except () if DEBUG else Exception as exc:
                report_exception_to_server(exc, section.func_name)
        if (container.status == "running" and
                not is_disabled_section(config, 'docker_container_agent')):
            try:
                section_container_agent(client, container_id, dispatcher)
            except () if DEBUG else Exception as exc:
                report_exception_to_server(exc, "section_container_agent")


#.
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
    except () if DEBUG else Exception as exc:
        report_exception_to_server(exc, "MKDockerClient.__init__")
        sys.exit(1)

    set_version_info(client)

    call_node_sections(client, config)

    call_container_sections(client, config)


if __name__ == "__main__":
    main()
