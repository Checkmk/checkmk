#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

"""How the agent logs in to AWS.

The agent logs in once per run as the "hub": with an access key, with the boto3
default credential chain or with a named profile. Without spokes, it monitors the account of the login.

To monitor other accounts, the hub assumes a "spoke" role of the same name in each of
them. Every spoke is exactly one AssumeRole away from the login identity, so roles are
never chained.

The spoke accounts are either listed in the rule or, for an organization, found by
ListAccounts on every run. The hub calls ListAccounts itself, or it assumes an account list
role in the management account for that one call. That role is also one AssumeRole away
from the login identity, and the spokes are not assumed through it.

If ListAccounts fails, the accounts of the last successful listing are monitored. A failed
listing says nothing about the accounts themselves, and without their data Checkmk would
show their services as vanished.
"""

import json
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import boto3
import botocore

from cmk.server_side_programs.v1 import Storage

from .config import AGENT, AwsAccessError, describe_credential_failure

# boto3 sessions are not thread-safe, their clients are. Create every client under this lock.
CLIENT_LOCK = threading.Lock()


@dataclass(frozen=True)
class AccessKey:
    key_id: str
    secret: str


@dataclass(frozen=True)
class DefaultCredentials:
    """The boto3 default credential chain.

    Environment variables, the ~/.aws files of the site user, and the instance profile
    or EKS Pod Identity when Checkmk runs on AWS. Checkmk stores no secret.
    """


@dataclass(frozen=True)
class NamedProfile:
    """A profile of the ~/.aws files of the site user, for example one with a credential_process.

    Checkmk stores no secret. The profile is read on the site that runs the agent.
    """

    name: str


@dataclass(frozen=True)
class HubCredentials:
    login: AccessKey | DefaultCredentials | NamedProfile
    session_name: str = "checkmk"


@dataclass(frozen=True)
class Organization:
    """Every active account of the organization, except the excluded ones."""

    excluded_ids: Sequence[str] = ()
    list_role_arn: str | None = None
    list_external_id: str | None = None


@dataclass(frozen=True)
class SpokeAccounts:
    accounts: Sequence[str] | Organization
    role_name: str
    external_id: str | None = None


def role_session_name(site: str | None) -> str:
    """The RoleSessionName of every AssumeRole call. CloudTrail shows it to the customer.

    Site IDs only use letters, digits and underscores, which AWS accepts here.
    """
    return f"checkmk-{site}" if site else "checkmk"


def _login_session(
    login: AccessKey | DefaultCredentials | NamedProfile, region: str
) -> boto3.session.Session:
    # Reads the shared config, so a missing profile or a bad config file raises a
    # BotoCoreError here. The callers build the session inside their own try.
    match login:
        case AccessKey(key_id=key_id, secret=secret):
            return boto3.session.Session(
                aws_access_key_id=key_id,
                aws_secret_access_key=secret,
                region_name=region,
            )
        case DefaultCredentials():
            return boto3.session.Session(region_name=region)
        case NamedProfile(name=name):
            return boto3.session.Session(profile_name=name, region_name=region)


def _assume_role(
    session: boto3.session.Session,
    role_arn: str,
    external_id: str | None,
    session_name: str,
    region: str,
    config: botocore.config.Config | None,
) -> tuple[boto3.session.Session, str]:
    """The session of the assumed role, and the account AWS says the role belongs to."""
    with CLIENT_LOCK:
        sts = session.client("sts", config=config)
    assumed_role_object = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name,
        **({"ExternalId": external_id} if external_id else {}),
    )
    credentials = assumed_role_object["Credentials"]
    # arn:<partition>:sts::<account>:assumed-role/<role>/<session>
    account_id = assumed_role_object["AssumedRoleUser"]["Arn"].split(":")[4]
    return boto3.session.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name=region,
    ), account_id


class AccountListStore:
    """The answer of the last successful ListAccounts call of one rule host.

    The answer is only valid for the identity that listed the accounts: the hub account
    and the account list role. Other credentials may belong to another organization.
    """

    _KEY = "organization_accounts"

    def __init__(self, hostname: str) -> None:
        self._storage = Storage(AGENT, hostname)

    def read(self, lister: Sequence[str | None]) -> Sequence[Mapping[str, str]] | None:
        try:
            stored = json.loads(self._storage.read(self._KEY, "null"))
        except ValueError:
            return None
        if not isinstance(stored, dict) or stored.get("lister") != list(lister):
            return None
        accounts = stored.get("accounts")
        return accounts if isinstance(accounts, list) else None

    def write(self, lister: Sequence[str | None], accounts: Sequence[Mapping[str, str]]) -> None:
        self._storage.write(
            self._KEY,
            json.dumps(
                {
                    "lister": list(lister),
                    "accounts": [
                        {
                            key: account[key]
                            for key in ("Id", "Name", "State", "Status")
                            if key in account
                        }
                        for account in accounts
                    ],
                }
            ),
        )


def _is_active(account: Mapping[str, str]) -> bool:
    # AWS replaces Status with State, which also knows PENDING_ACTIVATION and CLOSED.
    return account.get("State", account.get("Status")) == "ACTIVE"


@dataclass(frozen=True)
class AwsAccount:
    id: str
    session: boto3.session.Session
    # Only ListAccounts tells the name, so only the accounts of an organization have one.
    name: str | None = None


class AwsCredentials:
    """Owns the credentials for one agent run.

    One base session is built, and every region shares it. Credentials are therefore
    resolved once per run instead of once per region. That costs nothing with a static
    access key, but with the boto3 credential provider chain it is one provider lookup
    instead of N. A `credential_process` or IAM Roles Anywhere setup pays a subprocess or
    a signed HTTPS round trip for each of those lookups.

    The base session is pinned to the global service region. Clients override the region
    individually, so a shared session does not force a shared region. Keeping the base
    session in the configured global region also keeps the AssumeRole STS calls inside the
    partition being monitored, which is what us-gov-* and cn-* setups need.

    With spoke accounts, each account gets one more session from its role, also built
    once per run.
    """

    def __init__(
        self,
        hub: HubCredentials,
        global_service_region: str,
        client_config: botocore.config.Config | None,
        spokes: SpokeAccounts | None = None,
        account_list_store: AccountListStore | None = None,
    ) -> None:
        self._hub = hub
        self._spokes = spokes
        self._account_list_store = account_list_store
        self.account_listing_error: AwsAccessError | None = None
        self._global_service_region = global_service_region
        self._client_config = client_config
        self._session: boto3.session.Session | None = None
        self._account_id: str | None = None
        self._account_names: dict[str, str] = {}

    def session(self) -> boto3.session.Session:
        """The login (hub) session, built on first use and then reused.

        The sessions of spoke accounts come from open_account().
        """
        if self._session is None:
            self._session = _login_session(self._hub.login, self._global_service_region)
        return self._session

    def session_account_id(self) -> str:
        """The account of session(), the login's account.

        At most one STS call per run.
        """
        try:
            # The session is built inside the try on purpose. It does not resolve
            # credentials, but it does read the shared config, so a missing AWS_PROFILE or
            # an unparsable config file raises here rather than at the client call below.
            session = self.session()
            if (account_id := self._account_id) is None:
                with CLIENT_LOCK:
                    sts = session.client("sts", config=self._client_config)
                account_id = sts.get_caller_identity()["Account"]
                self._account_id = account_id
        except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError, OSError) as e:
            # BotoCoreError covers every client-side failure, including all the
            # credential ones. ClientError is not a BotoCoreError, so it stays listed.
            # OSError is a credential_process that cannot be started.
            raise AwsAccessError(describe_credential_failure(e))
        return account_id

    def monitored_account_ids(self) -> Sequence[str]:
        """The accounts this run monitors. Raises AwsAccessError if the hub login fails.

        If ListAccounts fails but an earlier listing is stored, its accounts are returned
        and account_listing_error tells why.
        """
        # Called also for spoke accounts, so that a broken login fails here, once.
        session_account_id = self.session_account_id()
        if self._spokes is None:
            return [session_account_id]
        if isinstance(accounts := self._spokes.accounts, Organization):
            return self._organization_account_ids(accounts, session_account_id)
        return accounts

    def _organization_account_ids(
        self, organization: Organization, session_account_id: str
    ) -> Sequence[str]:
        store = self._account_list_store
        lister = (session_account_id, organization.list_role_arn)
        try:
            accounts = self._list_accounts(organization)
        except AwsAccessError as error:
            if store is None or (stored := store.read(lister)) is None:
                raise
            self.account_listing_error = error
            accounts = stored
        else:
            if store is not None:
                store.write(lister, accounts)
        # open_account() gives each account its name from here.
        self._account_names = {
            account["Id"]: account["Name"] for account in accounts if account.get("Name")
        }
        return [
            account["Id"]
            for account in accounts
            if _is_active(account) and account["Id"] not in organization.excluded_ids
        ]

    def _list_accounts(self, organization: Organization) -> Sequence[Mapping[str, str]]:
        try:
            session = self.session()
            if organization.list_role_arn is not None:
                session, _ = _assume_role(
                    session,
                    organization.list_role_arn,
                    organization.list_external_id,
                    self._hub.session_name,
                    self._global_service_region,
                    self._client_config,
                )
            with CLIENT_LOCK:
                client = session.client("organizations", config=self._client_config)
            return [
                account
                for page in client.get_paginator("list_accounts").paginate()
                for account in page["Accounts"]
            ]
        except Exception as e:
            raise AwsAccessError(
                f"Cannot list the accounts in the organization: {describe_credential_failure(e)}"
            )

    def open_account(self, account_id: str) -> AwsAccount:
        """One account of monitored_account_ids(), with the session to use for all its regions.

        A spoke role is assumed here, right before its account is monitored. Its
        credentials last one hour, which a long list of accounts could outlast if every
        role were assumed at the start of the run.
        """
        if self._spokes is None:
            return AwsAccount(account_id, self.session())
        return self._spoke_account(account_id, self._spokes)

    def _spoke_account(self, account_id: str, spokes: SpokeAccounts) -> AwsAccount:
        try:
            login = self.session()
            partition = login.get_partition_for_region(self._global_service_region)
            session, assumed_account_id = _assume_role(
                login,
                f"arn:{partition}:iam::{account_id}:role/{spokes.role_name}",
                spokes.external_id,
                self._hub.session_name,
                self._global_service_region,
                self._client_config,
            )
        except Exception as e:
            raise AwsAccessError(f"Account {account_id}: {describe_credential_failure(e)}")
        return AwsAccount(assumed_account_id, session, name=self._account_names.get(account_id))
