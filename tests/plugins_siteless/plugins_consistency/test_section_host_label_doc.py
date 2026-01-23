#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test the documentation of the host label functions.

Currently the helper below is just used to facilitate the testing.
Someday it may be used to automatically extract the doc for all
builtin host labels.
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Final

from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    AgentSectionPlugin,
    SectionName,
    SNMPSectionPlugin,
)
from tests.testlib.common.repo import is_non_free_repo

CRE_DOCUMENTED_BUILTIN_HOST_LABELS: Final = {
    "cmk/azure/resource_group",
    "cmk/azure/subscription_id",
    "cmk/azure/subscription_name",
    "cmk/azure/tag/{key}:{value}",  # deprecated azure plugin
    "cmk/azure/tag/{label}:{value}",
    "cmk/azure/entity:resource_group",
    "cmk/azure/entity:<entity_type>",
    "cmk/azure/region:<region>",
    "cmk/azure/entity:subscription",
    "cmk/azure/entity:tenant",
    "cmk/azure/vm:instance",
    "cmk/aws/tag/{key}:{value}",
    "cmk/check_mk_server",
    "cmk/cloud:azure",
    "cmk/cdp_neighbor/{neighbor_id}",
    "cmk/ceph/osd",
    "cmk/ceph/mon",
    "cmk/device_model",
    "cmk/device_type",
    "cmk/docker_image",
    "cmk/docker_image_name",
    "cmk/docker_image_version",
    "cmk/docker_object:container",
    "cmk/docker_object:node",
    "cmk/has_cdp_neighbors",
    "cmk/has_lldp_neighbors",
    "cmk/kubernetes/annotation/{key}:{value}",
    "cmk/kubernetes",
    "cmk/kubernetes/deployment",
    "cmk/kubernetes/cronjob",
    "cmk/kubernetes/daemonset",
    "cmk/kubernetes/namespace",
    "cmk/kubernetes/node",
    "cmk/kubernetes/object",
    "cmk/kubernetes/statefulset",
    "cmk/kubernetes/cluster",
    "cmk/kubernetes/cluster-host",
    "cmk/l3v4_topology",
    "cmk/l3v6_topology",
    "cmk/meraki",
    "cmk/meraki/device_type",
    "cmk/meraki/has_lldp_neighbors",
    "cmk/meraki/net_id",
    "cmk/meraki/net_name",
    "cmk/meraki/org_id",
    "cmk/meraki/org_name",
    "cmk/nutanix/object",
    "cmk/os_family",
    "cmk/os_type",
    "cmk/os_platform",
    "cmk/os_name",
    "cmk/os_version",
    "cmk/pve/cluster:<cluster_name>",
    "cmk/pve/entity:node",
    "cmk/pve/entity:<entity_type>",
    "cmk/vsphere_object",
    "cmk/vsphere_vcenter",
    "cmk/systemd/unit:{name}",
    "cmk/podman/host",
    "cmk/podman/node:{node}",
    "cmk/podman/object:container",
    "cmk/podman/object:node",
    "cmk/podman/pod:{pod}",
    "cmk/podman/user:{user}",
}

CEE_DOCUMENTED_BUILTIN_HOST_LABELS: Final = {
    "cmk/rmk/node_type",
    "cmk/otel/metrics",  # CCE, actually.
}


def all_documented_builtin_host_labels() -> set[str]:
    if is_non_free_repo():
        return CEE_DOCUMENTED_BUILTIN_HOST_LABELS | CRE_DOCUMENTED_BUILTIN_HOST_LABELS
    return CEE_DOCUMENTED_BUILTIN_HOST_LABELS


KNOWN_NON_BUILTIN_LABEL_PRODUCERS: Final = {
    "labels",
    "ps",
    "ps_lnx",
}


def test_all_sections_have_host_labels_documented(
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    """Test that all sections have documented their host labels"""
    sections: Iterable[AgentSectionPlugin | SNMPSectionPlugin] = [
        *(s for s in agent_based_plugins.agent_sections.values()),
        *(s for s in agent_based_plugins.snmp_sections.values()),
    ]

    encountered_labels: defaultdict[str, dict[SectionName, Sequence[str]]] = defaultdict(dict)

    for section in (
        s for s in sections if s.host_label_function.__name__ != "_noop_host_label_function"
    ):
        assert section.host_label_function.__doc__, (
            f"Missing doc-string for host label function of {section.name}"
        )

        short_description, body = section.host_label_function.__doc__.split("\n", 1)
        text_sections = _TextSection(
            header=short_description,
            lines=body.splitlines(),
        ).subsections()

        label_paragraphs = [p for p in text_sections if p.header == "Labels"]
        assert len(label_paragraphs) == 1, (
            f"Missing 'Labels:' section in doc-string for host label function of {section.name}"
        )

        if str(section.name) in KNOWN_NON_BUILTIN_LABEL_PRODUCERS:
            continue

        label_docs = label_paragraphs[0].subsections()
        # at least one label
        assert label_docs
        for doc in label_docs:
            assert doc.header is not None, f"header in {section.name} not set"
            encountered_labels[doc.header][section.name] = doc.lines

    assert all_documented_builtin_host_labels() == set(encountered_labels.keys())

    for label_name, section_to_lines in encountered_labels.items():
        if len({" ".join(lines) for lines in section_to_lines.values()}) != 1:
            info = "\n".join(
                f"{section_name}\n  {' '.join(lines)}"
                for section_name, lines in section_to_lines.items()
            )
            assert False, f"documentation for label '{label_name}' differ: \n{info}"


def test_builtin_labels_start_with_cmk() -> None:
    assert all(l.startswith("cmk/") for l in all_documented_builtin_host_labels())


class _TextSection:
    """A helper to parse doc-strings"""

    def __init__(
        self,
        *,
        header: str | None,
        lines: Sequence[str],
    ):
        self.header: Final = header
        # strip empty lines at beginning & end
        content_flags = [bool(l.strip()) for l in lines]
        content_lines = (
            lines[content_flags.index(True) : -content_flags[::-1].index(True) or None]
            if any(content_flags)
            else []
        )
        indent = self._get_indent(content_lines)
        self.lines: Final[Sequence[str]] = [l[indent:].rstrip() for l in content_lines]

    @staticmethod
    def _get_indent(lines: Sequence[str]) -> int:
        for line in lines:
            stripped = line.lstrip()
            if not stripped:
                continue
            return len(line) - len(stripped)
        return 0

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(header={self.header}, lines={self.lines})"

    def subsections(self) -> Sequence["_TextSection"]:
        """Split up the body in subsections"""

        subsections = []
        header = None
        lines: list[str] = []
        for line in self.lines:
            if not line or line.isspace():
                if lines:
                    lines.append(line)
                continue

            if line.startswith(" "):
                lines.append(line)
                continue

            new_header = line[:-1].strip() if line.endswith(":") else None
            if new_header != header:
                if lines:
                    subsections.append(_TextSection(header=header, lines=lines))
                header = new_header
                lines = []
                continue

            if new_header is None:
                lines.append(line)
                continue

        if lines:
            subsections.append(_TextSection(header=header, lines=lines))

        return subsections
