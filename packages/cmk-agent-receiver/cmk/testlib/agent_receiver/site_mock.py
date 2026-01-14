#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from enum import auto, Enum
from http import HTTPStatus
from typing import assert_never, final, NewType

from pydantic import BaseModel, Field

from ...agent_receiver.lib.auth import B64SiteInternalSecret
from .schema import JsonSchema
from .wiremock import Request, Response, Wiremock, WMapping


class OP(Enum):
    ADD = auto()
    DEL = auto()


Relay = str
Change = tuple[Relay, OP]
State = NewType("State", str)


class RelayData(BaseModel):
    alias: str
    siteid: str
    num_fetchers: int = 17
    log_level: str = "INFO"


class GetResponse(BaseModel):
    """basic structure of a checkmk GET response for a single item"""

    id: str
    extensions: RelayData
    links: list[str] = Field(default_factory=list)  # keep empty here
    domainType: str = "relay"


class ListResponse(BaseModel):
    value: list[GetResponse]
    links: list[str] = Field(default_factory=list)  # keep empty here
    domainType: str = "relay"


class PostResponse(BaseModel):
    id: Relay
    links: list[str] = Field(default_factory=list)  # keep empty here
    domainType: str = "relay"


@dataclass(frozen=True)
class User:
    name: str
    password: str

    @property
    def bearer(self) -> str:
        return f"Bearer {self.name} {self.password}"


@final
class SiteMock:
    def __init__(
        self, wiremock: Wiremock, site_name: str, user: User, internal_secret: B64SiteInternalSecret
    ) -> None:
        self.wiremock = wiremock
        self.site_name = site_name
        self.user = user
        self.internal_secret = f"InternalToken {internal_secret}"
        self._scenario_setup = False

    @property
    def base_url(self) -> str:
        return f"{self.wiremock.base_url}{self.base_route}"

    @property
    def base_route(self) -> str:
        return f"/{self.site_name}/check_mk/api/unstable"

    def set_scenario(
        self, relays: Sequence[Relay] | Relay, changes: Sequence[Change] | None = None
    ) -> None:
        """Setup a WireMock scenario for relay management testing.
        limited to work on one site. Please call this only once

        Examples:
            # Simple static scenario
            site.set_scenario(["relay1", "relay2"])

            # Dynamic scenario with changes
            site.set_scenario(
                relays=["relay1"],
                changes=[("relay2", OP.ADD), ("relay1", OP.DEL)]
            )
        """
        if self._scenario_setup:
            raise RuntimeError("Only one wiremock scenario should be used per test")
        self._scenario_setup = True
        if isinstance(relays, str):
            relays = [relays]
        changes = changes or []
        # use a random scenario name to ensure test isolation
        name = f"testcase-{secrets.token_urlsafe(5)}"

        # initial state is always started in wiremock do not change
        state = State("Started")
        self._set_scenario_get(relays, name=name, state=state)
        used_relays = list(relays)
        for idx, (relayid, op) in enumerate(changes):
            old_state = state
            state = State(f"Step-{idx}")
            match op:
                case OP.ADD:
                    used_relays.append(relayid)
                    self._set_relay_add(relayid, name, prev=old_state, next=state)
                case OP.DEL:
                    used_relays.remove(relayid)
                    self._set_relay_del(relayid, name, prev=old_state, next=state)
                case _:
                    assert_never(op)

            self._set_scenario_get(used_relays, name=name, state=state)

    def _set_relay_del(self, relayid: Relay, name: str, prev: State, next: State) -> None:  # noqa: A002
        mapping = WMapping(
            scenarioName=name,
            requiredScenarioState=prev,
            newScenarioState=next,
            request=Request(
                method="DELETE",
                url=f"{self.base_route}/objects/relay/{relayid}",
                headers={
                    "Authorization": {
                        "matches": f"^(?:{self.user.bearer}|{self.internal_secret})$"
                    },
                },
            ),
            response=Response(
                status=HTTPStatus.NO_CONTENT,
            ),
        )
        self.wiremock.setup_mapping(mapping)

    def _set_relay_add(self, relayid: Relay, name: str, prev: State, next: State) -> None:  # noqa: A002
        mapping = WMapping(
            scenarioName=name,
            requiredScenarioState=prev,
            newScenarioState=next,
            request=Request(
                method="POST",
                url=f"{self.base_route}/domain-types/relay/collections/all",
                headers={
                    "Content-Type": {"matches": "application/json"},
                    "Authorization": {
                        "matches": f"^(?:{self.user.bearer}|{self.internal_secret})$"
                    },
                },
                bodyPatterns=[
                    {
                        "matchesJsonSchema": json.dumps(
                            RelayData.model_json_schema(schema_generator=JsonSchema)
                        ),
                    }
                ],
            ),
            response=Response(
                status=HTTPStatus.OK,
                body=PostResponse(id=relayid).model_dump_json(),
            ),
        )
        self.wiremock.setup_mapping(mapping)

    def _set_scenario_get(self, relays: Sequence[Relay], *, name: str, state: State) -> None:
        mapping = WMapping(
            scenarioName=name,
            requiredScenarioState=state,
            request=Request(
                method="GET",
                url=f"{self.base_route}/domain-types/relay/collections/all",
                headers={
                    "Authorization": {
                        "matches": f"^(?:{self.user.bearer}|{self.internal_secret})$"
                    },
                },
            ),
            response=Response(
                status=200,
                body=ListResponse(
                    value=[
                        GetResponse(id=r, extensions=RelayData(alias=r, siteid=self.site_name))
                        for r in relays
                    ]
                ).model_dump_json(),
            ),
        )
        self.wiremock.setup_mapping(mapping)

        for r in relays:
            mapping = WMapping(
                scenarioName=name,
                requiredScenarioState=state,
                request=Request(
                    method="GET",
                    url=f"{self.base_route}/objects/relay/{r}",
                    headers={
                        "Authorization": {
                            "matches": f"^(?:{self.user.bearer}|{self.internal_secret})$"
                        },
                    },
                ),
                response=Response(
                    status=200,
                    body=GetResponse(
                        id=r, extensions=RelayData(alias=r, siteid=self.site_name)
                    ).model_dump_json(),
                ),
            )
            self.wiremock.setup_mapping(mapping)

    def mock_relay_get_error(self, relay_id: Relay, status: HTTPStatus, error_message: str) -> None:
        """Mock a GET request for a specific relay to return an error status code.

        Args:
            relay_id: The relay ID to mock the error for
            status: The HTTP status code to return
            error_message: The error message to include in the response body
        """
        mapping = WMapping(
            priority=0,
            request=Request(
                method="GET",
                url=f"{self.base_route}/objects/relay/{relay_id}",
                headers={
                    "Authorization": {
                        "matches": f"^(?:{self.user.bearer}|{self.internal_secret})$"
                    },
                },
            ),
            response=Response(
                status=status,
                body=error_message,
            ),
        )
        self.wiremock.setup_mapping(mapping)
