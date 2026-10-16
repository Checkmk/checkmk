#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

"""How the agent logs in to AWS.

The agent logs in once per run as the "hub": with an access key or with the boto3
default credential chain, optionally followed by one AssumeRole into a role whose
account is then monitored.

To monitor several accounts, the hub assumes a "spoke" role of the same name in each of
them. Every spoke is exactly one AssumeRole away from the login identity: an assumed role
cannot be combined with spokes, because that would chain roles.

The spoke accounts are either listed in the rule or, for an organization, found by
ListAccounts on every run. The hub calls ListAccounts itself, or it assumes an account list
role in the management account for that one call. That role is also one AssumeRole away
from the login identity, and the spokes are not assumed through it.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import boto3
import botocore

from .config import AwsAccessError, describe_credential_failure


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
class AssumedRole:
    """The role the login assumes right away. Its account is the one monitored."""

    arn: str
    external_id: str | None = None


@dataclass(frozen=True)
class HubCredentials:
    login: AccessKey | DefaultCredentials
    role: AssumedRole | None = None
    session_name: str = "checkmk"


@dataclass(frozen=True)
class Organization:
    """Every active account of the organization, except the excluded ones."""

    excluded_ids: Sequence[str] = ()
    list_role_arn: str | None = None


@dataclass(frozen=True)
class SpokeAccounts:
    accounts: Sequence[str] | Organization
    role_name: str
    # Sent to every role this rule assumes, the account list role included.
    external_id: str | None = None


def role_session_name(site: str | None) -> str:
    """The RoleSessionName of every AssumeRole call. CloudTrail shows it to the customer.

    Site IDs only use letters, digits and underscores, which AWS accepts here.
    """
    return f"checkmk-{site}" if site else "checkmk"


def _login_session(login: AccessKey | DefaultCredentials, region: str) -> boto3.session.Session:
    # Reads the shared config, so a bad AWS_PROFILE or config file raises a BotoCoreError
    # here. The callers build the session inside their own try.
    match login:
        case AccessKey(key_id=key_id, secret=secret):
            return boto3.session.Session(
                aws_access_key_id=key_id,
                aws_secret_access_key=secret,
                region_name=region,
            )
        case DefaultCredentials():
            return boto3.session.Session(region_name=region)


def _assume_role(
    session: boto3.session.Session,
    role_arn: str,
    external_id: str | None,
    session_name: str,
    region: str,
    config: botocore.config.Config | None,
) -> tuple[boto3.session.Session, str]:
    """The session of the assumed role, and the account AWS says the role belongs to."""
    assumed_role_object = session.client("sts", config=config).assume_role(
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


def _create_hub_session(
    hub: HubCredentials, region: str, config: botocore.config.Config | None
) -> tuple[boto3.session.Session, str | None]:
    """The hub session, and its account if the AssumeRole answer already told it."""
    if hub.role is None:
        return _login_session(hub.login, region), None
    try:
        return _assume_role(
            _login_session(hub.login, region),
            hub.role.arn,
            hub.role.external_id,
            hub.session_name,
            region,
            config,
        )
    except Exception as e:
        raise AwsAccessError(describe_credential_failure(e))


def _is_active(account: Mapping[str, str]) -> bool:
    # AWS replaces Status with State, which also knows PENDING_ACTIVATION and CLOSED.
    return account.get("State", account.get("Status")) == "ACTIVE"


@dataclass(frozen=True)
class AwsAccount:
    id: str
    session: boto3.session.Session
    # The piggyback host for the account's own data, or None for the rule host.
    host: str | None = None


class AwsCredentials:
    """Owns the credentials for one agent run.

    One base session is built, and every region shares it. Credentials are therefore
    resolved once per run instead of once per region. That costs nothing with a static
    access key, but with AssumeRole it is one STS call instead of N, and with the boto3
    credential provider chain it is one provider lookup instead of N. A
    `credential_process` or IAM Roles Anywhere setup pays a subprocess or a signed HTTPS
    round trip for each of those lookups.

    The base session is pinned to the global service region. Clients override the region
    individually, so a shared session does not force a shared region. Keeping the base
    session in the configured global region also keeps the AssumeRole STS call inside the
    partition being monitored, which is what us-gov-* and cn-* setups need.

    With spoke accounts, each account gets one more session from its role, also built
    once per run.
    """

    def __init__(
        self,
        hub: HubCredentials,
        global_service_region: str,
        proxy_config: botocore.config.Config | None,
        spokes: SpokeAccounts | None = None,
    ) -> None:
        if hub.role is not None and spokes is not None:
            raise ValueError("An assumed role cannot be combined with spoke accounts")
        self._hub = hub
        self._spokes = spokes
        self._global_service_region = global_service_region
        self._proxy_config = proxy_config
        self._session: boto3.session.Session | None = None
        self._account_id: str | None = None

    def session(self) -> boto3.session.Session:
        """The login (hub) session, built on first use and then reused.

        The sessions of spoke accounts come from open_account().
        """
        if self._session is None:
            self._session, self._account_id = _create_hub_session(
                self._hub, self._global_service_region, self._proxy_config
            )
        return self._session

    def session_account_id(self) -> str:
        """The account of session(): the login's account, or the role's with an assumed role.

        At most one STS call per run.
        """
        try:
            # The session is built inside the try on purpose. It does not resolve
            # credentials, but it does read the shared config, so a missing AWS_PROFILE or
            # an unparsable config file raises here rather than at the client call below.
            # With an assumed role, building it already tells the account.
            session = self.session()
            if (account_id := self._account_id) is None:
                account_id = session.client("sts", config=self._proxy_config).get_caller_identity()[
                    "Account"
                ]
                self._account_id = account_id
        except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError) as e:
            # BotoCoreError covers every client-side failure, including all the
            # credential ones. ClientError is not a BotoCoreError, so it stays listed.
            raise AwsAccessError(describe_credential_failure(e))
        return account_id

    def monitored_account_ids(self) -> Sequence[str]:
        """The accounts this run monitors. Raises AwsAccessError if the hub login fails."""
        # Called also for spoke accounts, so that a broken login fails here, once.
        session_account_id = self.session_account_id()
        if self._spokes is None:
            return [session_account_id]
        if isinstance(accounts := self._spokes.accounts, Organization):
            return self._organization_account_ids(accounts, self._spokes.external_id)
        return accounts

    def _organization_account_ids(
        self, organization: Organization, external_id: str | None
    ) -> Sequence[str]:
        try:
            session = self.session()
            if organization.list_role_arn is not None:
                session, _ = _assume_role(
                    session,
                    organization.list_role_arn,
                    external_id,
                    self._hub.session_name,
                    self._global_service_region,
                    self._proxy_config,
                )
            client = session.client("organizations", config=self._proxy_config)
            accounts = [
                account
                for page in client.get_paginator("list_accounts").paginate()
                for account in page["Accounts"]
            ]
        except Exception as e:
            raise AwsAccessError(
                f"Cannot list the accounts in the organization: {describe_credential_failure(e)}"
            )
        return [
            account["Id"]
            for account in accounts
            if _is_active(account) and account["Id"] not in organization.excluded_ids
        ]

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
            # Without an assumed role, session() is the login identity itself.
            login = self.session()
            partition = login.get_partition_for_region(self._global_service_region)
            session, assumed_account_id = _assume_role(
                login,
                f"arn:{partition}:iam::{account_id}:role/{spokes.role_name}",
                spokes.external_id,
                self._hub.session_name,
                self._global_service_region,
                self._proxy_config,
            )
        except Exception as e:
            raise AwsAccessError(f"Account {account_id}: {describe_credential_failure(e)}")
        return AwsAccount(assumed_account_id, session, host=assumed_account_id)
