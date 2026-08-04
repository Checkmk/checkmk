#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-override"

"""Test the documentation of the host label functions.

Currently the helper below is just used to facilitate the testing.
Someday it may be used to automatically extract the doc for all
builtin host labels.
"""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Final

from cmk.agent_based.v2 import AgentSection, entry_point_prefixes, SimpleSNMPSection, SNMPSection
from cmk.agent_based.v3_unstable import entry_point_prefixes as entry_point_prefixes_v3_unstable
from cmk.agent_based.v3_unstable import MetricsSection
from cmk.discover_plugins import discover_all_plugins, DiscoveredPlugins, PluginGroup
from cmk.ruleset_matcher.labels import BuiltinLabelsKey

_KNOWN_NON_BUILTIN_LABEL_PRODUCERS: Final = {
    "labels",
    "ps",
    "ps_lnx",
}


type Section = (
    AgentSection[object]
    | SNMPSection[object, object]
    | SimpleSNMPSection[object, object]
    | MetricsSection[object]
)


def extract_shipped_host_labels() -> Mapping[str, str]:
    return {
        **_extract_discovered_labels(),
        **{e.value: "" for e in BuiltinLabelsKey},
    }


def _extract_discovered_labels() -> Mapping[str, str]:
    ep = entry_point_prefixes()
    ep_v3_unstable = entry_point_prefixes_v3_unstable()
    discovered_plugins: DiscoveredPlugins[Section] = discover_all_plugins(
        PluginGroup.AGENT_BASED,
        {
            AgentSection: ep[AgentSection],
            SimpleSNMPSection: ep[SimpleSNMPSection],
            SNMPSection: ep[SNMPSection],
            MetricsSection: ep_v3_unstable[MetricsSection],
        },
        skip_wrong_types=False,
        raise_errors=True,
    )

    encountered_labels: defaultdict[str, dict[str, str]] = defaultdict(dict)
    for section in (
        s
        for s in discovered_plugins.plugins.values()
        if (f := s.host_label_function) and f.__name__ != "_noop_host_label_function"
    ):
        if not section.host_label_function.__doc__:
            raise AssertionError(f"Missing doc-string for host label function of {section.name}")

        short_description, body = section.host_label_function.__doc__.split("\n", 1)
        text_sections = _TextSection(
            header=short_description,
            lines=body.splitlines(),
        ).subsections()

        label_paragraphs = [p for p in text_sections if p.header == "Labels"]
        if len(label_paragraphs) != 1:
            raise AssertionError(
                f"Missing 'Labels:' section in doc-string for host label function of {section.name}"
            )

        if str(section.name) in _KNOWN_NON_BUILTIN_LABEL_PRODUCERS:
            continue

        label_docs = label_paragraphs[0].subsections()
        # at least one label
        if not label_docs:
            raise AssertionError(f"Expected at least one label: {section.name}")

        for doc in label_docs:
            if doc.header is None:
                raise AssertionError(f"Header in {section.name} not set")
            encountered_labels[doc.header][section.name] = " ".join(doc.lines)

    def _ensure_uniqe_value(label: str, desc: Mapping[str, str]) -> tuple[str, str]:
        if len(s := set(desc.values())) != 1:
            raise AssertionError(f"Documentations for label '{label}' differ: {desc!r}")
        return label, s.pop()

    return dict(_ensure_uniqe_value(*item) for item in encountered_labels.items())


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
