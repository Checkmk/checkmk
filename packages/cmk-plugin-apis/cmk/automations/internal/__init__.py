#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Internal automations API: the ``Automation`` plug-in type and the discovery prefix.

This is the ``internal`` variant of the per-domain automations API (see the
plugin discovery reference in ``cmk.discover_plugins``). It is not exposed to
third-party plug-in authors; it carries the actions the GUI and the REST API
ask the backend to perform, e.g. ``service-discovery``.

To be discovered, a plug-in module must be placed in the ``automations``
subdirectory of a plug-in family (``cmk/plugins/<family>/automations/<module>.py``)
and the plug-in instance name must start with the prefix returned by
:func:`entry_point_prefixes`.

An automation declares the state its handler runs against and how to build it.
The engine builds the state from the site's root and the raw configuration,
keeps it, and updates it whenever the configuration changes. Both the state and
the result are types of the plug-in's own; this package only names what the
engine needs of them, so that it depends on nothing.
"""

from abc import ABC, abstractmethod
from ast import literal_eval
from collections.abc import Callable, Mapping
from dataclasses import astuple, dataclass
from pathlib import Path
from typing import NewType, override, Self

AutomationID = NewType("AutomationID", str)
"""The name an automation is called by, e.g. ``service-discovery``.

It is part of the wire format: the caller sends it, and the backend looks the
automation up by it.
"""


@dataclass
class AutomationResult(ABC):
    def serialize(self, _for_cmk_version: str, /) -> str:
        """Serialize the result for a peer running the given Checkmk version.

        The version lets a result stay compatible with older central sites. Results
        that depend on it may parse it with ``cmk.ccc.version.Version.from_str``.
        """
        return repr(astuple(self))

    @classmethod
    def deserialize(cls, serialized_result: str, /) -> Self:
        return cls(*literal_eval(serialized_result))

    @staticmethod
    @abstractmethod
    def automation_call() -> AutomationID: ...


class AutomationState(ABC):
    """Whatever an automation needs to have ready before it runs.

    The engine builds it with the automation's :attr:`Automation.state_factory`,
    keeps it alive between calls and hands it the new arguments via
    :meth:`update` whenever they change.
    """

    @abstractmethod
    def update(self, omd_root: Path, raw_config: Mapping[str, object]) -> None: ...


type StateFactory[StateT: AutomationState] = Callable[[Path, Mapping[str, object]], StateT]
"""Build a state from the site's root and the raw configuration."""


class NoState(AutomationState):
    """The state of an automation that needs none.

    Such an automation reads nothing but its arguments and its standard input,
    or loads what it needs itself. Naming this class as the factory spares it
    deriving anything from the configuration.
    """

    def __init__(self, _omd_root: Path, _raw_config: Mapping[str, object]) -> None:
        pass

    @override
    def update(self, _omd_root: Path, _raw_config: Mapping[str, object]) -> None:
        pass


@dataclass(frozen=True, kw_only=True)
class Automation[StateT: AutomationState, ResultT: AutomationResult]:
    """An action the backend performs on request, selected by its :attr:`name`.

    Example:
    ********

    >>> from collections.abc import Sequence
    >>> class Greeting(AutomationResult):
    ...     def __init__(self, text: str) -> None:
    ...         self.text = text
    ...     def serialize(self, for_cmk_version: str) -> str:
    ...         return repr(self.text)
    ...     @staticmethod
    ...     def automation_call() -> AutomationID:
    ...         return AutomationID("greet")
    >>> def greet(_state: NoState, args: Sequence[str]) -> Greeting:
    ...     return Greeting(f"Hello {', '.join(args)}")
    >>> automation_greet = Automation(
    ...     name=AutomationID("greet"),
    ...     state_factory=NoState,
    ...     handler=greet,
    ...     result=Greeting,
    ... )
    """

    name: AutomationID
    state_factory: StateFactory[StateT]
    """Produce the state :attr:`handler` runs against, ready for the given arguments.

    The engine calls each distinct factory once and keeps what it returns:
    automations that name the same factory share the same state.
    """
    handler: Callable[[StateT, list[str]], ResultT]
    """Perform the automation against its state and return its result.

    The arguments are the ones the caller sent, without the automation's name.
    """
    result: type[ResultT]
    """The type :attr:`handler` returns.

    Declaring it ties the handler's return type to the result type the
    automation is documented to produce, so the two cannot drift apart.
    """
    lock_configuration: bool = False
    """Read the configuration under the configuration lock when the CLI runs this.

    The GUI holds that lock during every Setup action and calls automations from
    within them, so this must stay off for any automation it calls that way: the
    CLI would wait for a lock its own caller holds.
    """

    def __post_init__(self) -> None:
        """Make sure the name matches the automation id of the result type.
        A mismatch here will make the caller try to deserialize the wrong type.
        """
        rname = self.result.automation_call()
        if not self.name == rname:
            raise TypeError(f"Automation {self.name!r}: Mismatching ID of result type: {rname!r}")


def entry_point_prefixes() -> Mapping[type[Automation], str]:  # type: ignore[type-arg]
    """Return the types of plug-ins and their respective prefixes that can be discovered by Checkmk.

    Example:
    ********

    >>> for plugin_type, prefix in entry_point_prefixes().items():
    ...     print(f'{prefix}... = {plugin_type.__name__}(...)')
    automation_... = Automation(...)
    """
    return {Automation: "automation_"}


__all__ = [
    "Automation",
    "AutomationID",
    "AutomationResult",
    "AutomationState",
    "entry_point_prefixes",
    "NoState",
    "StateFactory",
]
