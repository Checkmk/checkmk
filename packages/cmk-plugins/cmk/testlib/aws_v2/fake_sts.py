#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
A fake STS endpoint for the hub login.

Tests point boto3 at it through AWS_ENDPOINT_URL_STS, the setting boto3 offers for this.
AssumeRole hands out a temporary key per account, "ASIA<account id>", and
GetCallerIdentity answers with the account of the key: the hub account for any static
key. Roles in DENIED_ACCOUNT cannot be assumed.

DescribeRegions names NOT_ENABLED_REGION as an opt-in region the account has not enabled.
Every other call of SCP_DENIED_ACCOUNT is denied by a service control policy.

S3 ListBuckets answers with an account that has no buckets.

ListAccounts answers with ORGANIZATION_PAGES, one page per call, active and inactive
accounts mixed. It denies callers that log in with NO_LIST_KEY_ID.

Tests that also set AWS_ENDPOINT_URL send every other service here, too. The fake
records who signed such a request and for which region, then answers with an error.

The fake logs every request it gets to stderr, and pytest shows these lines for a
failing test. If a new boto3 breaks the tests, they show what reached the fake.
"""

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

HUB_ACCOUNT = "111111111111"
ROLE_ACCOUNT = "222222222222"
ROLE = "arn:aws:iam::222222222222:role/CheckmkMonitoring"
DENIED_ACCOUNT = "999999999999"
SCP_DENIED_ACCOUNT = "555555555555"
NOT_ENABLED_REGION = "me-central-1"
MANAGEMENT_ACCOUNT = "888888888888"
LIST_ROLE = f"arn:aws:iam::{MANAGEMENT_ACCOUNT}:role/CheckmkAccountList"
NO_LIST_KEY_ID = "AKIANOLIST"

ORGANIZATION_PAGES = [
    [
        {"Id": MANAGEMENT_ACCOUNT, "State": "ACTIVE", "Status": "ACTIVE"},
        {"Id": "333333333333", "State": "ACTIVE", "Status": "ACTIVE"},
        {"Id": "666666666666", "State": "SUSPENDED", "Status": "SUSPENDED"},
    ],
    [
        # An answer from before AWS added State.
        {"Id": "444444444444", "Status": "ACTIVE"},
        # State wins over the deprecated Status.
        {"Id": "777777777777", "State": "CLOSED", "Status": "ACTIVE"},
    ],
]
ACTIVE_ORGANIZATION_ACCOUNTS = [MANAGEMENT_ACCOUNT, "333333333333", "444444444444"]

_ACCESS_DENIED_RESPONSE = """\
<ErrorResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
  <Error><Type>Sender</Type><Code>AccessDenied</Code><Message>Not authorized</Message></Error>
  <RequestId>4</RequestId>
</ErrorResponse>
"""


def temporary_key_id(account: str) -> str:
    return f"ASIA{account}"


TEMPORARY_KEY_ID = temporary_key_id(ROLE_ACCOUNT)


def _assume_role_response(account: str) -> str:
    return f"""\
<AssumeRoleResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
  <AssumeRoleResult>
    <Credentials>
      <AccessKeyId>{temporary_key_id(account)}</AccessKeyId>
      <SecretAccessKey>temporary-secret</SecretAccessKey>
      <SessionToken>temporary-token</SessionToken>
      <Expiration>2099-01-01T00:00:00Z</Expiration>
    </Credentials>
    <AssumedRoleUser>
      <AssumedRoleId>AROAEXAMPLE:checkmk</AssumedRoleId>
      <Arn>arn:aws:sts::{account}:assumed-role/CheckmkMonitoring/checkmk</Arn>
    </AssumedRoleUser>
  </AssumeRoleResult>
  <ResponseMetadata><RequestId>1</RequestId></ResponseMetadata>
</AssumeRoleResponse>
"""


def _caller_identity_response(account: str) -> str:
    return f"""\
<GetCallerIdentityResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
  <GetCallerIdentityResult>
    <Arn>arn:aws:iam::{account}:user/checkmk</Arn>
    <UserId>AIDAEXAMPLE</UserId>
    <Account>{account}</Account>
  </GetCallerIdentityResult>
  <ResponseMetadata><RequestId>2</RequestId></ResponseMetadata>
</GetCallerIdentityResponse>
"""


_DESCRIBE_REGIONS_RESPONSE = f"""\
<DescribeRegionsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>5</requestId>
  <regionInfo>
    <item><regionName>eu-central-1</regionName><optInStatus>opt-in-not-required</optInStatus></item>
    <item><regionName>{NOT_ENABLED_REGION}</regionName><optInStatus>not-opted-in</optInStatus></item>
  </regionInfo>
</DescribeRegionsResponse>
"""


_SCP_DENIED_RESPONSE = """\
<ErrorResponse>
  <Error>
    <Type>Sender</Type>
    <Code>AccessDenied</Code>
    <Message>Not authorized, with an explicit deny in a service control policy</Message>
  </Error>
  <RequestId>6</RequestId>
</ErrorResponse>
"""


_LIST_BUCKETS_RESPONSE = """\
<ListAllMyBucketsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Owner><ID>1</ID><DisplayName>checkmk</DisplayName></Owner>
  <Buckets></Buckets>
</ListAllMyBucketsResult>
"""


_SERVICE_ERROR_RESPONSE = """\
<ErrorResponse>
  <Error><Type>Sender</Type><Code>FakeAws</Code><Message>Not faked</Message></Error>
  <RequestId>3</RequestId>
</ErrorResponse>
"""


@dataclass(frozen=True)
class SignedRequest:
    key_id: str
    region: str
    service: str


@dataclass(frozen=True)
class AssumeRoleCall:
    caller_key_id: str
    params: dict[str, str]


@dataclass
class FakeSts:
    url: str = ""
    assume_role_calls: list[AssumeRoleCall] = field(default_factory=list)
    service_requests: list[SignedRequest] = field(default_factory=list)
    list_accounts_calls: list[SignedRequest] = field(default_factory=list)
    # Both kinds of calls, in the order they arrived.
    calls: list[AssumeRoleCall | SignedRequest] = field(default_factory=list)


def _signed_request(authorization: str) -> SignedRequest:
    # AWS4-HMAC-SHA256 Credential=<key id>/<date>/<region>/<service>/aws4_request, ...
    key_id, _date, region, service, _ = (
        authorization.split("Credential=")[1].split(",", maxsplit=1)[0].split("/")
    )
    return SignedRequest(key_id, region, service)


def _handler(sts: FakeSts) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
            params = {key: values[0] for key, values in parse_qs(body).items()}
            self.log_message(
                "%s %s %s",
                self.command,
                params.get("Action", self.path),
                _signed_request(self.headers["Authorization"]),
            )
            if self.headers.get("X-Amz-Target", "").endswith(".ListAccounts"):
                self._list_accounts(json.loads(body or "{}"))
                return
            match params.get("Action"):
                case "AssumeRole":
                    caller = _signed_request(self.headers["Authorization"]).key_id
                    call = AssumeRoleCall(caller, params)
                    sts.assume_role_calls.append(call)
                    sts.calls.append(call)
                    # arn:<partition>:iam::<account>:role/<name>
                    account = params["RoleArn"].split(":")[4]
                    if account == DENIED_ACCOUNT:
                        self._answer(403, _ACCESS_DENIED_RESPONSE)
                    else:
                        self._answer(200, _assume_role_response(account))
                case "GetCallerIdentity":
                    key_id = _signed_request(self.headers["Authorization"]).key_id
                    account = (
                        key_id.removeprefix("ASIA") if key_id.startswith("ASIA") else HUB_ACCOUNT
                    )
                    self._answer(200, _caller_identity_response(account))
                case _:
                    request = _signed_request(self.headers["Authorization"])
                    sts.service_requests.append(request)
                    sts.calls.append(request)
                    if request.key_id == temporary_key_id(SCP_DENIED_ACCOUNT):
                        self._answer(403, _SCP_DENIED_RESPONSE)
                    elif params.get("Action") == "DescribeRegions":
                        self._answer(200, _DESCRIBE_REGIONS_RESPONSE)
                    elif request.service == "s3" and urlparse(self.path).path == "/":
                        self._answer(200, _LIST_BUCKETS_RESPONSE)
                    else:
                        self._answer(400, _SERVICE_ERROR_RESPONSE)

        do_GET = do_HEAD = do_PUT = do_DELETE = do_POST

        def _list_accounts(self, request: dict[str, str]) -> None:
            caller = _signed_request(self.headers["Authorization"])
            sts.list_accounts_calls.append(caller)
            if caller.key_id == NO_LIST_KEY_ID:
                denied = {"__type": "AccessDeniedException", "Message": "Not allowed to list"}
                self._answer(400, json.dumps(denied), "application/x-amz-json-1.1")
                return
            page = int(request.get("NextToken", "0"))
            answer: dict[str, object] = {"Accounts": ORGANIZATION_PAGES[page]}
            if page + 1 < len(ORGANIZATION_PAGES):
                answer["NextToken"] = str(page + 1)
            self._answer(200, json.dumps(answer), "application/x-amz-json-1.1")

        def _answer(self, status: int, response: str, content_type: str = "text/xml") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(response.encode())

    return Handler


@contextmanager
def running_fake_sts() -> Iterator[FakeSts]:
    sts = FakeSts()
    server = HTTPServer(("127.0.0.1", 0), _handler(sts))
    sts.url = f"http://127.0.0.1:{server.server_port}"
    threading.Thread(target=server.serve_forever, args=(0.01,), daemon=True).start()
    try:
        yield sts
    finally:
        server.shutdown()
        server.server_close()
