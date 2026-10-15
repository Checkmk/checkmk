#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections.abc import Iterable, Iterator
from typing import Final, Literal, Self

type Level = Literal["info", "warning"]


class AgentMessages:
    """
    Collect messages to be shown in the "Check_MK" service of the host.

    There are two kinds of messages, both shown in the "Check_MK" service:

    Infos are always shown with the state OK. Use them for things worth
    knowing that are no problem, for example a resource that was skipped
    on purpose.

    Warnings are meant for problems that did not stop the agent from
    producing data, for example a single endpoint the configured account
    may not access. Their state is configurable in the rule "Status of the
    Checkmk services", under "Individual states per data source",
    "Special agent".
    While a warning is reported with a state other than OK, automatic service
    discovery skips the host, as the data is probably incomplete. A warning
    that is reported on every run therefore disables automatic service
    discovery for the host, until it is resolved or its state is set to OK.
    The HW/SW inventory still processes the data and shows the warnings in
    its service.

    Write the rendered section to the agent output, preferably at the end.
    It is written at the top level, so it ends any piggyback output you may
    have left open. You can write it more than once; the messages of all
    occurrences are shown.

    It is recommended to always create it using this class; do not write
    the section by hand.

    Example:

        >>> import sys
        >>> messages = AgentMessages()
        >>> messages.add_info("Skipped 3 resources without a region")
        >>> messages.add_warning("Could not create section 'foobar_userdata': permission to endpoint denied")
        >>> _ = sys.stdout.write(messages.render())
        <<<<>>>>
        <<<cmk_agent_messages:sep(0)>>>
        {"level": "info", "message": "Skipped 3 resources without a region"}
        {"level": "warning", "message": "Could not create section 'foobar_userdata': permission to endpoint denied"}

    Nothing is written if there are no messages:

        >>> AgentMessages().render()
        ''
    """

    SECTION_NAME: Final = "cmk_agent_messages"

    def __init__(self) -> None:
        self._messages: list[tuple[Level, str]] = []

    def add_info(self, message: str) -> None:
        """Add an info, always shown with the state OK."""
        self._messages.append(("info", message))

    def add_warning(self, message: str) -> None:
        """Add a warning, shown with the configured state (WARN by default)."""
        self._messages.append(("warning", message))

    def __len__(self) -> int:
        return len(self._messages)

    def __iter__(self) -> Iterator[tuple[Level, str]]:
        """The level and text of each message, in the order they were added."""
        return iter(self._messages)

    def _to_lines(self) -> Iterable[str]:
        return (json.dumps({"level": level, "message": m}) for level, m in self._messages)

    @classmethod
    def from_string_table(cls, string_table: Iterable[Iterable[str]]) -> Self:
        """
        Deserialize the messages from the rows of the section.

        A message without a known level is read as a warning. A row that is
        not in the expected layout is kept as an "Unreadable message" warning,
        so a broken writer is noticed rather than silenced.

        Example:

            >>> list(AgentMessages.from_string_table([['{"level": "info", "message": "first"}'], ["oops"]]))
            [('info', 'first'), ('warning', 'Unreadable message: oops')]
        """
        messages = cls()
        messages._messages = [cls._parse_row(row) for row in string_table]
        return messages

    @staticmethod
    def _parse_row(row: Iterable[str]) -> tuple[Level, str]:
        raw = " ".join(row)
        try:
            match json.loads(raw):
                case {"level": "info", "message": str(message)}:
                    return "info", message
                case {"message": str(message)}:
                    return "warning", message
                case _other:
                    pass
        except ValueError:
            pass
        return "warning", f"Unreadable message: {raw[:200]}"

    def render(self) -> str:
        """
        Render the section containing the messages.

        Returns:
            The section as text to be written to the agent output,
            or an empty string if there are no messages.
        """
        if not self._messages:
            return ""
        rows = "\n".join(self._to_lines())
        return f"<<<<>>>>\n<<<{self.SECTION_NAME}:sep(0)>>>\n{rows}\n"
