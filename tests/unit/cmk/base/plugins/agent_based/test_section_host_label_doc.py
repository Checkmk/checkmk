#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test the documentation of the host label functions

Cutrrently the helper below is just used to facilitate the testing.
Someday it may be used to automatically extract the doc for all
builtin host labels.
"""
import itertools
from typing import Final, List, Optional, Sequence, Set

ALL_DOCUMENTED_BUILTIN_HOST_LABELS: Final = {
    "cmk/device_type",
    "cmk/docker_image",
    "cmk/docker_image_name",
    "cmk/docker_image_version",
    "cmk/docker_object:container",
    "cmk/docker_object:node",
    "cmk/kubernetes_object:endpoint",
    "cmk/kubernetes:yes",
    "cmk/kubernetes",
    "cmk/kubernetes/deployment",
    "cmk/kubernetes/daemonset",
    "cmk/kubernetes/namespace",
    "cmk/kubernetes/node",
    "cmk/kubernetes/object",
    "cmk/kubernetes/statefulset",
    "cmk/kubernetes/cluster",
    "cmk/os_family",
    "cmk/vsphere_object",
}


KNOWN_MISSING_DOCSTRING: Final = {  # TODO CMK-7660
    "esx_vsphere_vm",
    "k8s_daemon_pods",
    "k8s_ingress_infos",
    "k8s_job_info",
    "k8s_nodes",
    "k8s_pod_container",
    "k8s_replicas",
    "k8s_service_port",
    "k8s_stateful_set_replicas",
    "omd_info",
}

KNOWN_NON_BUILTIN_LABEL_PRODUCERS: Final = {
    "labels",
    "ps",
    "ps_lnx",
}


def test_all_sections_have_host_labels_documented(fix_register):
    """Test that all sections have documented their host labels"""
    sections = itertools.chain(
        fix_register.agent_sections.values(),
        fix_register.snmp_sections.values(),
    )

    encountered_labels: Set[Optional[str]] = set()

    for section in (
        s for s in sections if s.host_label_function.__name__ != "_noop_host_label_function"
    ):

        if str(section.name) in KNOWN_MISSING_DOCSTRING:
            assert not section.host_label_function.__doc__
            continue

        assert (
            section.host_label_function.__doc__
        ), f"Missing doc-string for host label function of {section.name}"

        short_description, body = section.host_label_function.__doc__.split("\n", 1)
        text_sections = _TextSection(
            header=short_description,
            lines=body.splitlines(),
        ).subsections()

        label_paragraphs = [p for p in text_sections if p.header == "Labels"]
        assert (
            len(label_paragraphs) == 1
        ), f"Missing 'Labels:' section in doc-string for host label function of {section.name}"

        if str(section.name) in KNOWN_NON_BUILTIN_LABEL_PRODUCERS:
            continue

        label_docs = label_paragraphs[0].subsections()
        # at least one label
        assert label_docs
        encountered_labels.update(doc.header for doc in label_docs)

    assert ALL_DOCUMENTED_BUILTIN_HOST_LABELS == encountered_labels


def test_builtin_labels_start_with_cmk():
    assert all(l.startswith("cmk/") for l in ALL_DOCUMENTED_BUILTIN_HOST_LABELS)


class _TextSection:
    """A helper to parse doc-strings"""

    def __init__(
        self,
        *,
        header: Optional[str],
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
        lines: List[str] = []
        for line in self.lines:
            if not line.strip():
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
