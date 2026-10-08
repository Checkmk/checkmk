#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

"""How the agent logs in to AWS.

The agent logs in once per run as the "hub": with an access key or with the boto3
default credential chain, optionally followed by one AssumeRole into a role whose
account is then monitored.
"""

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


def _login_session(login: AccessKey | DefaultCredentials, region: str) -> boto3.session.Session:
    # No try/except here, but not because this cannot fail. The constructor does not
    # resolve credentials, so it raises nothing about them, yet it does read the shared
    # config: a missing AWS_PROFILE gives ProfileNotFound and an unparsable file gives
    # ConfigParseError. Both are BotoCoreError, and every caller builds the session
    # inside its own try, so they are reported there together with the errors from
    # session.client(...).
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
    role: AssumedRole,
    region: str,
    config: botocore.config.Config | None,
) -> boto3.session.Session:
    assumed_role_object = session.client("sts", config=config).assume_role(
        RoleArn=role.arn,
        RoleSessionName="AssumeRoleSession",
        **({"ExternalId": role.external_id} if role.external_id else {}),
    )
    credentials = assumed_role_object["Credentials"]
    return boto3.session.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name=region,
    )


def create_hub_session(
    hub: HubCredentials, region: str, config: botocore.config.Config | None
) -> boto3.session.Session:
    if hub.role is None:
        return _login_session(hub.login, region)
    try:
        return _assume_role(_login_session(hub.login, region), hub.role, region, config)
    except Exception as e:
        raise AwsAccessError(describe_credential_failure(e))


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
    """

    def __init__(
        self,
        hub: HubCredentials,
        global_service_region: str,
        proxy_config: botocore.config.Config | None,
    ) -> None:
        self._hub = hub
        self._global_service_region = global_service_region
        self._proxy_config = proxy_config
        self._session: boto3.session.Session | None = None
        self._account_id: str | None = None

    def session(self) -> boto3.session.Session:
        """The single session of this run, built on first use and then reused."""
        if self._session is None:
            self._session = create_hub_session(
                self._hub, self._global_service_region, self._proxy_config
            )
        return self._session

    def account_id(self) -> str:
        """The account the credentials belong to. One STS call per run, then cached."""
        if self._account_id is None:
            try:
                # The session is built inside the try on purpose. It does not resolve
                # credentials, but it does read the shared config, so a missing
                # AWS_PROFILE or an unparsable config file raises here rather than at the
                # client call below.
                self._account_id = (
                    self.session()
                    .client("sts", config=self._proxy_config)
                    .get_caller_identity()["Account"]
                )
            except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError) as e:
                # BotoCoreError covers every client-side failure, including all the
                # credential ones. ClientError is not a BotoCoreError, so it stays listed.
                raise AwsAccessError(describe_credential_failure(e))
        return self._account_id
