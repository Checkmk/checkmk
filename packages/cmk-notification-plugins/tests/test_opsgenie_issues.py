#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from http import HTTPStatus
from typing import Final
from urllib.parse import parse_qs, unquote, urlsplit

import pytest
import urllib3

from cmk.notification_plugins.opsgenie_issues import main
from cmk.testlib.notification_plugins import exit_code, explicit_password
from cmk.utils.paths import trusted_ca_file

_SUCCESS: Final = {"result": "Request will be processed", "took": 0.1, "requestId": "req-1"}
_NOT_FOUND: Final = {"message": "Alert does not exist", "took": 0.0, "requestId": "req-2"}
_REJECTED: Final = {"message": "nope", "took": 0.0, "requestId": "req-4"}

_PROXY_ENV_VARS: Final = (
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
)

API_KEY: Final = explicit_password("PARAMETER_PASSWORD", "my-api-key")

HOST_CONTEXT: Final = {
    **API_KEY,
    "WHAT": "HOST",
    "NOTIFICATIONTYPE": "PROBLEM",
    "HOSTNAME": "myhost",
    "HOSTSHORTSTATE": "DOWN",
    "PREVIOUSHOSTHARDSHORTSTATE": "UP",
    "HOSTOUTPUT": "Host unreachable",
    "HOSTPROBLEMID": "42",
    "LASTHOSTPROBLEMID": "41",
}

SERVICE_CONTEXT: Final = {
    **API_KEY,
    "WHAT": "SERVICE",
    "NOTIFICATIONTYPE": "PROBLEM",
    "HOSTNAME": "myhost",
    "SERVICEDESC": "CPU load",
    "SERVICESHORTSTATE": "CRIT",
    "PREVIOUSSERVICEHARDSHORTSTATE": "OK",
    "SERVICEOUTPUT": "Load too high",
    "SERVICEPROBLEMID": "7",
    "LASTSERVICEPROBLEMID": "6",
}

HOST_ALIAS: Final = "HOST_PROBLEM_ID: 42"
SERVICE_ALIAS: Final = "SVC_PROBLEM_ID: 7"

_OPS_TEAM: Final = {"name": "ops", "type": "team"}
_NET_TEAM: Final = {"name": "net", "type": "team"}
_CMK_TEAM: Final = {"name": "cmk", "type": "team"}

_HOST_ACK: Final = {"HOSTACKAUTHOR": "jdoe", "HOSTACKCOMMENT": "on it"}
_SERVICE_ACK: Final = {"SERVICEACKAUTHOR": "jdoe", "SERVICEACKCOMMENT": "on it"}

_CREATE_ALERT_FAILED: Final = "Exception when calling AlertApi -> create_alert: "
_CREATE_ALERT_UNHANDLED: Final = "Unhandled exception when calling AlertApi -> create_alert: "

HOST_DESCRIPTION: Final = (
    "Host: myhost\n"
    "    Event:    UP -> DOWN\n"
    "    Output:   Host unreachable\n"
    "    Perfdata: \n"
    "    \n"
    "    "
)


@dataclass(frozen=True)
class SentRequest:
    method: str
    host: str
    path: str
    query: Mapping[str, list[str]]
    body: Mapping[str, object]
    authorization: str


class FakeOpsgenie:
    """Unknown GET requests answer 404 (alert not found), everything else is accepted."""

    def __init__(self) -> None:
        self.requests: list[SentRequest] = []
        self._replies: dict[tuple[str, str], tuple[int, Mapping[str, object]]] = {}

    def reply(self, method: str, path: str, status: int, payload: Mapping[str, object]) -> None:
        self._replies[(method, path)] = (status, payload)

    def urlopen(self, method: str, url: str, **kw: object) -> urllib3.HTTPResponse:
        parts = urlsplit(url)
        path = unquote(parts.path)
        body = kw.get("body")
        headers = kw.get("headers")
        self.requests.append(
            SentRequest(
                method=method,
                host=parts.netloc,
                path=path,
                query=parse_qs(parts.query),
                body=json.loads(body) if isinstance(body, str) else {},
                authorization=(
                    str(headers.get("Authorization")) if isinstance(headers, Mapping) else ""
                ),
            )
        )
        default = (
            (HTTPStatus.NOT_FOUND, _NOT_FOUND)
            if method == "GET"
            else (HTTPStatus.ACCEPTED, _SUCCESS)
        )
        status, payload = self._replies.get((method, path), default)
        return urllib3.HTTPResponse(
            body=json.dumps(payload).encode(),
            status=status,
            reason=HTTPStatus(status).phrase,
            preload_content=True,
        )

    def calls(self) -> list[tuple[str, str]]:
        return [(r.method, r.path) for r in self.requests]


@pytest.fixture(name="opsgenie")
def fixture_opsgenie(monkeypatch: pytest.MonkeyPatch) -> FakeOpsgenie:
    fake = FakeOpsgenie()
    # opsgenie_sdk sends via urllib3, which `responses` cannot intercept.
    monkeypatch.setattr(urllib3.PoolManager, "urlopen", fake.urlopen)
    for var in _PROXY_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    return fake


def _body_of(opsgenie: FakeOpsgenie, method: str, path: str) -> Mapping[str, object]:
    return next(r.body for r in opsgenie.requests if (r.method, r.path) == (method, path))


def _created_alert(
    notify_context: Callable[[Mapping[str, str]], None],
    opsgenie: FakeOpsgenie,
    context: Mapping[str, str],
) -> Mapping[str, object]:
    notify_context(context)
    main()
    return _body_of(opsgenie, "POST", "/v2/alerts")


def test_missing_api_key_aborts(
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
    opsgenie: FakeOpsgenie,
) -> None:
    notify_context({k: v for k, v in HOST_CONTEXT.items() if k not in API_KEY})

    assert exit_code(main) == 2
    assert capsys.readouterr().err == "API key not set\n"
    assert not opsgenie.requests


def test_api_key_is_sent_as_genie_key(
    notify_context: Callable[[Mapping[str, str]], None], opsgenie: FakeOpsgenie
) -> None:
    notify_context(HOST_CONTEXT)

    main()

    assert [r.authorization for r in opsgenie.requests] == ["GenieKey my-api-key"]


def test_problem_creates_alert_with_default_payload(
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
    opsgenie: FakeOpsgenie,
) -> None:
    notify_context(HOST_CONTEXT)

    main()

    assert opsgenie.calls() == [("POST", "/v2/alerts")]
    assert opsgenie.requests[0].host == "api.opsgenie.com"
    assert opsgenie.requests[0].body == {
        "note": "Alert created by Check_MK",
        "message": "Check_MK: myhost - DOWN",
        "alias": HOST_ALIAS,
        "description": HOST_DESCRIPTION,
        "responders": [],
        "visibleTo": [],
        "actions": [],
        "tags": [],
        "details": {},
        "entity": "",
        "priority": "P3",
    }
    assert capsys.readouterr().out.endswith("Request id: req-1, successfully created alert.\n")


def test_service_problem_alert_uses_default_templates(
    notify_context: Callable[[Mapping[str, str]], None], opsgenie: FakeOpsgenie
) -> None:
    body = _created_alert(notify_context, opsgenie, SERVICE_CONTEXT)

    assert (body["message"], body["description"]) == (
        "Check_MK: myhost/CPU load CRIT",
        (
            "Host: myhost\n"
            "    Service:  CPU load\n"
            "    Event:    OK -> CRIT\n"
            "    Output:   Load too high\n"
            "    Perfdata: \n"
            "    \n"
            "    "
        ),
    )


def test_host_problem_alert_uses_custom_templates(
    notify_context: Callable[[Mapping[str, str]], None], opsgenie: FakeOpsgenie
) -> None:
    body = _created_alert(
        notify_context,
        opsgenie,
        {
            **HOST_CONTEXT,
            "PARAMETER_HOST_MSG": "$HOSTNAME$ down",
            "PARAMETER_HOST_DESC": "Output: $HOSTOUTPUT$",
        },
    )

    assert (body["message"], body["description"]) == ("myhost down", "Output: Host unreachable")


def test_service_problem_alert_uses_custom_templates(
    notify_context: Callable[[Mapping[str, str]], None], opsgenie: FakeOpsgenie
) -> None:
    body = _created_alert(
        notify_context,
        opsgenie,
        {
            **SERVICE_CONTEXT,
            "PARAMETER_SVC_MSG": "$SERVICEDESC$ is $SERVICESHORTSTATE$",
            "PARAMETER_SVC_DESC": "$SERVICEOUTPUT$",
        },
    )

    assert (body["message"], body["description"]) == ("CPU load is CRIT", "Load too high")


def test_problem_alert_takes_plain_parameters(
    notify_context: Callable[[Mapping[str, str]], None], opsgenie: FakeOpsgenie
) -> None:
    body = _created_alert(
        notify_context,
        opsgenie,
        {
            **HOST_CONTEXT,
            "PARAMETER_PRIORITY": "P1",
            "PARAMETER_ENTITY": "web",
            "PARAMETER_SOURCE": "cmk-site",
            "PARAMETER_OWNER": "jdoe",
            "PARAMETER_NOTE_CREATED": "Created by monitoring",
        },
    )

    assert {key: body[key] for key in ("priority", "entity", "source", "user", "note")} == {
        "priority": "P1",
        "entity": "web",
        "source": "cmk-site",
        "user": "jdoe",
        "note": "Created by monitoring",
    }


# fmt: off
@pytest.mark.parametrize(
    "parameters, expected",
    [
        pytest.param({"PARAMETER_ACTIONSS": "restart ping"}, {"actions": ["restart", "ping"]}, id="actions"),
        pytest.param({"PARAMETER_TAGSS": "$HOSTNAME$ production"}, {"tags": ["myhost", "production"]}, id="macro_tags"),
    ],
)
# fmt: on
def test_problem_alert_payload_from_list_parameters(
    notify_context: Callable[[Mapping[str, str]], None],
    opsgenie: FakeOpsgenie,
    parameters: Mapping[str, str],
    expected: Mapping[str, object],
) -> None:
    body = _created_alert(notify_context, opsgenie, {**HOST_CONTEXT, **parameters})

    assert {key: body[key] for key in expected} == expected


def test_problem_alert_is_assigned_and_visible_to_teams(
    notify_context: Callable[[Mapping[str, str]], None], opsgenie: FakeOpsgenie
) -> None:
    body = _created_alert(
        notify_context,
        opsgenie,
        {
            **HOST_CONTEXT,
            "PARAMETER_TEAMSS": "ops net",
            "PARAMETER_TEAMS_1": "ops",
            "PARAMETER_TEAMS_2": "net",
        },
    )

    assert (body["responders"], body["visibleTo"]) == (
        [_OPS_TEAM, _NET_TEAM],
        [_OPS_TEAM, _NET_TEAM],
    )


def test_problem_alert_details_contain_selected_non_empty_elements(
    monkeypatch: pytest.MonkeyPatch,
    notify_context: Callable[[Mapping[str, str]], None],
    opsgenie: FakeOpsgenie,
) -> None:
    monkeypatch.setenv("OMD_SITE", "mysite")
    notify_context(
        {
            **HOST_CONTEXT,
            "PARAMETER_ELEMENTSS": "omdsite address hosttags abstime",
            "HOSTADDRESS": "10.0.0.1",
            "HOST_TAGS": "/wato/ tcp prod",
        },
    )

    main()

    assert _body_of(opsgenie, "POST", "/v2/alerts")["details"] == {
        "Site ID": "mysite",
        "IP address of host": "10.0.0.1",
        "Tags of the Host": "/wato/\ntcp\nprod",
    }


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason='"longoutput" reads the context key "LONGSERVICEOUTPUT$" (stray "$"), never set',
)
def test_problem_alert_details_contain_long_output(
    notify_context: Callable[[Mapping[str, str]], None], opsgenie: FakeOpsgenie
) -> None:
    notify_context(
        {
            **SERVICE_CONTEXT,
            "PARAMETER_ELEMENTSS": "longoutput",
            "LONGSERVICEOUTPUT": "line 1\nline 2",
        },
    )

    main()

    assert _body_of(opsgenie, "POST", "/v2/alerts")["details"] == {
        "Additional plug-in output": "line 1\nline 2"
    }


# fmt: off
@pytest.mark.parametrize(
    "teams, visible_to",
    [
        pytest.param({"PARAMETER_TEAMSS": "ops", "PARAMETER_TEAMS_1": "ops"}, [_OPS_TEAM, _CMK_TEAM], id="appended"),
        pytest.param({"PARAMETER_TEAMSS": "cmk", "PARAMETER_TEAMS_1": "cmk"}, [_CMK_TEAM], id="already_a_responder"),
    ],
)
# fmt: on
def test_problem_alert_is_visible_to_integration_team(
    notify_context: Callable[[Mapping[str, str]], None],
    opsgenie: FakeOpsgenie,
    teams: Mapping[str, str],
    visible_to: list[dict[str, str]],
) -> None:
    notify_context({**HOST_CONTEXT, **teams, "PARAMETER_INTEGRATION_TEAM": "cmk"})

    main()

    assert _body_of(opsgenie, "POST", "/v2/alerts")["visibleTo"] == visible_to


def test_problem_with_integration_team_and_unknown_alias_only_creates_alert(
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
    opsgenie: FakeOpsgenie,
) -> None:
    notify_context({**HOST_CONTEXT, "PARAMETER_INTEGRATION_TEAM": "cmk"})

    main()

    assert opsgenie.calls() == [("GET", f"/v2/alerts/{HOST_ALIAS}"), ("POST", "/v2/alerts")]
    assert opsgenie.requests[0].query == {"identifierType": ["alias"]}
    assert f'Alert with alias "{HOST_ALIAS}" not found.\n' in capsys.readouterr().out


def test_problem_updates_changed_texts_of_existing_alert(
    notify_context: Callable[[Mapping[str, str]], None], opsgenie: FakeOpsgenie
) -> None:
    opsgenie.reply(
        "GET",
        f"/v2/alerts/{HOST_ALIAS}",
        HTTPStatus.OK,
        {
            "data": {"id": "alert-1", "message": "old", "description": "old"},
            "took": 0.1,
            "requestId": "req-3",
        },
    )
    notify_context({**HOST_CONTEXT, "PARAMETER_INTEGRATION_TEAM": "cmk"})

    main()

    assert [(r.method, r.path, r.body) for r in opsgenie.requests[2:]] == [
        ("PUT", "/v2/alerts/alert-1/description", {"description": HOST_DESCRIPTION}),
        ("PUT", "/v2/alerts/alert-1/message", {"message": "Check_MK: myhost - DOWN"}),
    ]


def test_problem_keeps_unchanged_existing_alert(
    notify_context: Callable[[Mapping[str, str]], None], opsgenie: FakeOpsgenie
) -> None:
    opsgenie.reply(
        "GET",
        f"/v2/alerts/{HOST_ALIAS}",
        HTTPStatus.OK,
        {
            "data": {
                "id": "alert-1",
                "message": "Check_MK: myhost - DOWN",
                "description": HOST_DESCRIPTION,
            },
            "took": 0.1,
            "requestId": "req-3",
        },
    )
    notify_context({**HOST_CONTEXT, "PARAMETER_INTEGRATION_TEAM": "cmk"})

    main()

    assert opsgenie.calls() == [("GET", f"/v2/alerts/{HOST_ALIAS}"), ("POST", "/v2/alerts")]


# fmt: off
@pytest.mark.parametrize(
    "context, alias",
    [
        pytest.param(HOST_CONTEXT, HOST_ALIAS, id="host"),
        pytest.param({**HOST_CONTEXT, "HOSTPROBLEMID": "0"}, "HOST_PROBLEM_ID: 41", id="host_last_problem"),
        pytest.param(SERVICE_CONTEXT, SERVICE_ALIAS, id="service"),
        pytest.param({**SERVICE_CONTEXT, "SERVICEPROBLEMID": "0"}, "SVC_PROBLEM_ID: 6", id="service_last_problem"),
    ],
)
# fmt: on
def test_recovery_closes_alert_by_problem_id_alias(
    notify_context: Callable[[Mapping[str, str]], None],
    opsgenie: FakeOpsgenie,
    context: Mapping[str, str],
    alias: str,
) -> None:
    notify_context({**context, "NOTIFICATIONTYPE": "RECOVERY"})

    main()

    assert opsgenie.calls() == [("POST", f"/v2/alerts/{alias}/close")]
    assert opsgenie.requests[0].query == {"identifierType": ["alias"]}


def test_recovery_sends_default_close_note(
    notify_context: Callable[[Mapping[str, str]], None], opsgenie: FakeOpsgenie
) -> None:
    notify_context({**HOST_CONTEXT, "NOTIFICATIONTYPE": "RECOVERY"})

    main()

    assert opsgenie.requests[0].body == {"note": "Alert closed by Check_MK"}


def test_recovery_sends_configured_close_note_source_and_owner(
    notify_context: Callable[[Mapping[str, str]], None], opsgenie: FakeOpsgenie
) -> None:
    notify_context(
        {
            **HOST_CONTEXT,
            "NOTIFICATIONTYPE": "RECOVERY",
            "PARAMETER_NOTE_CLOSED": "Resolved",
            "PARAMETER_SOURCE": "cmk-site",
            "PARAMETER_OWNER": "jdoe",
        }
    )

    main()

    assert opsgenie.requests[0].body == {"note": "Resolved", "source": "cmk-site", "user": "jdoe"}


# fmt: off
@pytest.mark.parametrize(
    "context, alias",
    [
        pytest.param({**HOST_CONTEXT, **_HOST_ACK}, HOST_ALIAS, id="host"),
        pytest.param({**SERVICE_CONTEXT, **_SERVICE_ACK}, SERVICE_ALIAS, id="service"),
    ],
)
# fmt: on
def test_acknowledgement_acknowledges_alert(
    notify_context: Callable[[Mapping[str, str]], None],
    opsgenie: FakeOpsgenie,
    context: Mapping[str, str],
    alias: str,
) -> None:
    notify_context({**context, "NOTIFICATIONTYPE": "ACKNOWLEDGEMENT"})

    main()

    assert [(r.method, r.path, r.body) for r in opsgenie.requests] == [
        ("POST", f"/v2/alerts/{alias}/acknowledge", {"user": "jdoe", "note": "on it"})
    ]


@pytest.mark.parametrize(
    "notification_type",
    [
        "FLAPPINGSTART",
        "FLAPPINGSTOP",
        "FLAPPINGDISABLED",
        "DOWNTIMESTART",
        "DOWNTIMEEND",
        "DOWNTIMECANCELLED",
        "ALERTHANDLER (0)",
    ],
)
def test_notification_type_without_integration_team_is_skipped(
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
    opsgenie: FakeOpsgenie,
    notification_type: str,
) -> None:
    notify_context({**HOST_CONTEXT, "NOTIFICATIONTYPE": notification_type})

    assert exit_code(main) == 0
    assert capsys.readouterr().out.endswith(
        f"Notification type {notification_type} requires integration team to be set\n"
    )
    assert not opsgenie.requests


# fmt: off
@pytest.mark.parametrize(
    "notification_type, body",
    [
        pytest.param("FLAPPINGSTART", {"tags": ["Flapping"], "note": "Flapping started"}, id="flapping"),
        pytest.param("DOWNTIMESTART", {"tags": ["Downtime"], "note": "Downtime started"}, id="downtime"),
    ],
)
# fmt: on
def test_start_event_adds_tag(
    notify_context: Callable[[Mapping[str, str]], None],
    opsgenie: FakeOpsgenie,
    notification_type: str,
    body: Mapping[str, object],
) -> None:
    notify_context(
        {
            **HOST_CONTEXT,
            "NOTIFICATIONTYPE": notification_type,
            "PARAMETER_INTEGRATION_TEAM": "cmk",
        },
    )

    main()

    assert [(r.method, r.path, r.body) for r in opsgenie.requests] == [
        ("POST", f"/v2/alerts/{HOST_ALIAS}/tags", body)
    ]


@pytest.mark.parametrize(
    "notification_type, tag, note",
    [
        ("FLAPPINGSTOP", "Flapping", "Flapping stopped"),
        ("FLAPPINGDISABLED", "Flapping", "Flapping disabled"),
        ("DOWNTIMEEND", "Downtime", "Downtime ended"),
        ("DOWNTIMECANCELLED", "Downtime", "Downtime cancelled"),
    ],
)
def test_end_event_removes_tag(
    notify_context: Callable[[Mapping[str, str]], None],
    opsgenie: FakeOpsgenie,
    notification_type: str,
    tag: str,
    note: str,
) -> None:
    notify_context(
        {
            **HOST_CONTEXT,
            "NOTIFICATIONTYPE": notification_type,
            "PARAMETER_INTEGRATION_TEAM": "cmk",
        },
    )

    main()

    assert opsgenie.calls() == [("DELETE", f"/v2/alerts/{HOST_ALIAS}/tags")]
    query = opsgenie.requests[0].query
    assert (query["tags"], query["note"]) == ([tag], [note])


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason='unset source and owner are passed as None and end up as the literal "None"',
)
def test_tag_removal_omits_unset_source_and_owner(
    notify_context: Callable[[Mapping[str, str]], None], opsgenie: FakeOpsgenie
) -> None:
    notify_context(
        {**HOST_CONTEXT, "NOTIFICATIONTYPE": "FLAPPINGSTOP", "PARAMETER_INTEGRATION_TEAM": "cmk"},
    )

    main()

    assert {"source", "user"}.isdisjoint(opsgenie.requests[0].query)


def _alert_handler_requests(
    notify_context: Callable[[Mapping[str, str]], None],
    opsgenie: FakeOpsgenie,
    context: Mapping[str, str],
) -> list[tuple[str, str, Mapping[str, object]]]:
    notify_context({**HOST_CONTEXT, **context, "PARAMETER_INTEGRATION_TEAM": "cmk"})
    main()
    return [(r.method, r.path, r.body) for r in opsgenie.requests]


def test_alert_handler_note_contains_handler_details(
    notify_context: Callable[[Mapping[str, str]], None], opsgenie: FakeOpsgenie
) -> None:
    requests = _alert_handler_requests(
        notify_context,
        opsgenie,
        {
            "NOTIFICATIONTYPE": "ALERTHANDLER (0)",
            "ALERTHANDLERNAME": "restart",
            "ALERTHANDLERSTATE": "success",
            "ALERTHANDLEROUTPUT": "done",
        },
    )

    assert requests == [
        (
            "POST",
            f"/v2/alerts/{HOST_ALIAS}/notes",
            {"note": "Alert handler (restart): success\nOutput: done"},
        )
    ]


def test_alert_handler_note_falls_back_to_exit_code(
    notify_context: Callable[[Mapping[str, str]], None], opsgenie: FakeOpsgenie
) -> None:
    requests = _alert_handler_requests(
        notify_context, opsgenie, {"NOTIFICATIONTYPE": "ALERTHANDLER (2)"}
    )

    assert requests == [
        ("POST", f"/v2/alerts/{HOST_ALIAS}/notes", {"note": "Alert handler (unknown): 2\nOutput: "})
    ]


def test_alert_handler_note_is_truncated_to_api_limit(
    notify_context: Callable[[Mapping[str, str]], None], opsgenie: FakeOpsgenie
) -> None:
    notify_context(
        {
            **HOST_CONTEXT,
            "NOTIFICATIONTYPE": "ALERTHANDLER (0)",
            "ALERTHANDLEROUTPUT": "x" * 30000,
            "PARAMETER_INTEGRATION_TEAM": "cmk",
        },
    )

    main()

    note = opsgenie.requests[0].body["note"]
    assert isinstance(note, str)
    assert (len(note), note[-4:]) == (25000, "x...")


def test_unsupported_notification_type_sends_nothing(
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
    opsgenie: FakeOpsgenie,
) -> None:
    notify_context({**HOST_CONTEXT, "NOTIFICATIONTYPE": "CUSTOM"})

    main()

    assert capsys.readouterr().out.endswith("Notification type CUSTOM not supported\n")
    assert not opsgenie.requests


# fmt: off
@pytest.mark.parametrize(
    "status, error",
    [
        pytest.param(HTTPStatus.UNAUTHORIZED, _CREATE_ALERT_FAILED, id="api_error"),
        pytest.param(HTTPStatus.UNPROCESSABLE_ENTITY, _CREATE_ALERT_UNHANDLED, id="unhandled_error"),
    ],
)
# fmt: on
def test_failing_alert_creation_aborts(
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
    opsgenie: FakeOpsgenie,
    status: HTTPStatus,
    error: str,
) -> None:
    opsgenie.reply("POST", "/v2/alerts", status, _REJECTED)
    notify_context(HOST_CONTEXT)

    code = exit_code(main)

    assert code == 2
    assert capsys.readouterr().err.startswith(error)


def test_forbidden_alert_lookup_aborts(
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
    opsgenie: FakeOpsgenie,
) -> None:
    opsgenie.reply("GET", f"/v2/alerts/{HOST_ALIAS}", HTTPStatus.FORBIDDEN, _REJECTED)
    notify_context({**HOST_CONTEXT, "PARAMETER_INTEGRATION_TEAM": "cmk"})

    code = exit_code(main)

    assert code == 2
    assert capsys.readouterr().err.startswith("Exception when calling AlertApi -> get_alert: ")


# fmt: off
@pytest.mark.parametrize(
    "parameters, first_line",
    [
        pytest.param({}, f"Using trust store: {trusted_ca_file}\n", id="trust_store"),
        pytest.param({"PARAMETER_IGNORE_SSL": "True"}, "Ignoring SSL certificate verification\n", id="ignore_ssl"),
    ],
)
# fmt: on
@pytest.mark.usefixtures("opsgenie")
def test_connection_settings_are_reported(
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
    parameters: Mapping[str, str],
    first_line: str,
) -> None:
    notify_context({**HOST_CONTEXT, **parameters})

    main()

    assert capsys.readouterr().out.startswith(first_line)


@pytest.mark.usefixtures("opsgenie")
def test_explicit_proxy_is_reported_redacted(
    notify_context: Callable[[Mapping[str, str]], None], capsys: pytest.CaptureFixture[str]
) -> None:
    notify_context({**HOST_CONTEXT, "PARAMETER_PROXY_URL": "http://user:secret@proxy.lan:3128"})

    main()

    assert capsys.readouterr().out.startswith("Using proxy: http://***@proxy.lan:3128\n")


# fmt: off
@pytest.mark.parametrize(
    "parameters, uses_proxy",
    [
        pytest.param({}, True, id="from_environment_by_default"),
        pytest.param({"PARAMETER_PROXY_URL": "FROM_ENVIRONMENT"}, True, id="from_environment"),
        pytest.param({"PARAMETER_PROXY_URL": "NO_PROXY"}, False, id="no_proxy"),
        pytest.param({"PARAMETER_URL": "http://opsgenie.internal"}, False, id="other_scheme_not_configured"),
    ],
)
# fmt: on
@pytest.mark.usefixtures("opsgenie")
def test_environment_proxy_selection(
    monkeypatch: pytest.MonkeyPatch,
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
    parameters: Mapping[str, str],
    uses_proxy: bool,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://envproxy.lan:3128")
    notify_context({**HOST_CONTEXT, **parameters})

    main()

    assert ("Using proxy: http://envproxy.lan:3128\n" in capsys.readouterr().out) is uses_proxy


def test_configured_url_replaces_default_host(
    notify_context: Callable[[Mapping[str, str]], None], opsgenie: FakeOpsgenie
) -> None:
    notify_context({**HOST_CONTEXT, "PARAMETER_URL": "https://api.eu.opsgenie.com"})

    main()

    assert [r.host for r in opsgenie.requests] == ["api.eu.opsgenie.com"]
