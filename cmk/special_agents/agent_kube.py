#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for monitoring Kubernetes clusters. The fully supported API version of Kubernetes
depends on the corresponding python module. E.g. v11 of the python module will support mainly
Kubernetes API v1.15. Please take a look on the official website to see, if you API version
is supported: https://github.com/kubernetes-client/python
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import Counter, defaultdict
from typing import DefaultDict, Dict, List, Optional

import urllib3  # type: ignore[import]
from kubernetes import client  # type: ignore[import] # pylint: disable=import-error
from pydantic import BaseModel

import cmk.utils.password_store
import cmk.utils.profile

from cmk.special_agents.utils.agent_common import SectionWriter
from cmk.special_agents.utils_kubernetes.api_server import APIServer
from cmk.special_agents.utils_kubernetes.schemas import MetaData, NodeResources, Phase, PodInfo


class PodResources(BaseModel):
    running: int = 0
    pending: int = 0
    succeeded: int = 0
    failed: int = 0
    unknown: int = 0
    capacity: int = 0
    allocatable: int = 0


class PathPrefixAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not values:
            return ""
        path_prefix = "/" + values.strip("/")
        setattr(namespace, self.dest, path_prefix)


def parse_arguments(args: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--debug", action="store_true", help="Debug mode: raise Python exceptions")
    p.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbose mode (for even more output use -vvv)",
    )
    p.add_argument("--port", type=int, default=None, help="Port to connect to")
    p.add_argument("--token", required=True, help="Token for that user")
    p.add_argument(
        "--api-server-endpoint", required=True, help="API server endpoint for Kubernetes API calls"
    )
    p.add_argument(
        "--path-prefix",
        default="",
        action=PathPrefixAction,
        help="Optional URL path prefix to prepend to Kubernetes API calls",
    )
    p.add_argument("--no-cert-check", action="store_true", help="Disable certificate verification")
    p.add_argument(
        "--profile",
        metavar="FILE",
        help="Profile the performance of the agent and write the output to a file",
    )

    arguments = p.parse_args(args)
    return arguments


def setup_logging(verbosity: int) -> None:
    if verbosity >= 3:
        lvl = logging.DEBUG
    elif verbosity == 2:
        lvl = logging.INFO
    elif verbosity == 1:
        lvl = logging.WARN
    else:
        logging.disable(logging.CRITICAL)
        lvl = logging.CRITICAL
    logging.basicConfig(level=lvl, format="%(asctime)s %(levelname)s %(message)s")


class Pod:
    def __init__(self, metadata: MetaData, phase: Phase, info: PodInfo) -> None:
        self.metadata = metadata
        self.node = info.node
        self.phase = phase

    def name(self, prepend_namespace=False) -> str:
        if not prepend_namespace:
            return self.metadata.name

        return f"{self.metadata.namespace}_{self.metadata.name}"


class Node:
    def __init__(self, metadata: MetaData, resources: Dict[str, NodeResources]) -> None:
        self.metadata = metadata
        self.resources = resources
        self._pods: List[Pod] = []

    @property
    def name(self) -> str:
        return self.metadata.name

    def append(self, pod: Pod) -> None:
        self._pods.append(pod)

    def pod_resources(self) -> PodResources:
        resources = {
            "capacity": self.resources["capacity"].pods,
            "allocatable": self.resources["allocatable"].pods,
        }
        resources.update(dict(Counter([pod.phase for pod in self._pods])))
        return PodResources(**resources)


class Cluster:
    @classmethod
    def from_api_server(cls, api_server: APIServer) -> Cluster:
        cluster = cls()
        for node_api in api_server.nodes():
            node = Node(node_api.metadata, node_api.resources)
            cluster.add_node(node)

        for pod_api in api_server.pods():
            pod = Pod(pod_api.metadata, pod_api.phase, pod_api.info)
            cluster.add_pod(pod)

        return cluster

    def __init__(self) -> None:
        self._nodes: Dict[str, Node] = {}
        self._pods: Dict[str, Pod] = {}

    def add_node(self, node: Node) -> None:
        self._nodes[node.name] = node

    def add_pod(self, pod: Pod) -> None:
        try:
            node = self._nodes[pod.node]
        except KeyError:
            raise KeyError(f"Node {pod.node} of {pod.name} was not listed in the API")
        node.append(pod)
        self._pods[pod.name(prepend_namespace=True)] = pod

    def pod_resources(self) -> PodResources:
        resources: DefaultDict[str, int] = defaultdict(int)
        for node in self._nodes.values():
            for k, v in dict(node.pod_resources()).items():
                resources[k] += v
        return PodResources(**resources)

    def sections(self) -> None:
        # with ConditionalPiggybackSection(self.name):
        with SectionWriter("k8s_pod_resources") as writer:
            writer.append(self.pod_resources().json())


def make_api_client(arguments: argparse.Namespace) -> client.ApiClient:
    config = client.Configuration()

    host = arguments.api_server_endpoint
    if arguments.port is not None:
        host = "%s:%s" % (host, arguments.port)
    if arguments.path_prefix:
        host = "%s%s" % (host, arguments.path_prefix)
    config.host = host
    config.api_key_prefix["authorization"] = "Bearer"
    config.api_key["authorization"] = arguments.token

    if arguments.no_cert_check:
        config.verify_ssl = False
    else:
        config.ssl_ca_cert = os.environ.get("REQUESTS_CA_BUNDLE")

    return client.ApiClient(config)


def main(args: Optional[List[str]] = None) -> int:
    if args is None:
        cmk.utils.password_store.replace_passwords()
        args = sys.argv[1:]
    arguments = parse_arguments(args)

    try:
        setup_logging(arguments.verbose)
        logging.debug("parsed arguments: %s\n", arguments)

        with cmk.utils.profile.Profile(
            enabled=bool(arguments.profile), profile_file=arguments.profile
        ):

            api_client = make_api_client(arguments)
            api_server = APIServer.from_kubernetes(api_client)
            cluster = Cluster.from_api_server(api_server)
            cluster.sections()

    except urllib3.exceptions.MaxRetryError as e:
        if arguments.debug:
            raise
        if isinstance(e.reason, urllib3.exceptions.NewConnectionError):
            sys.stderr.write(
                "Failed to establish a connection to %s:%s at URL %s"
                % (e.pool.host, e.pool.port, e.url)
            )
        else:
            sys.stderr.write("%s" % e)
        return 1
    except Exception as e:
        # if arguments.debug:
        #     raise
        sys.stderr.write("%s" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
