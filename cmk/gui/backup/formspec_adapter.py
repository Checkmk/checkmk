#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Explicit boundary between the on-disk ``TargetConfig`` and the WatoMode's form specs.

We mustn't touch the on-disk ``TargetConfig`` as it is shared with the CMA.
"""

from collections.abc import Mapping

from cmk.utils.backup.targets.aws_s3_bucket import S3Params
from cmk.utils.backup.targets.azure_blob_storage import (
    BlobStorageADCredentials,
    BlobStorageCredentials,
    BlobStorageParams,
)
from cmk.utils.backup.targets.config import TargetConfig
from cmk.utils.backup.targets.local import LocalTargetParams
from cmk.utils.backup.targets.remote_interface import RemoteTargetParams
from cmk.utils.password_store import PasswordId


def is_formspec_password(value: object) -> bool:
    """Whether ``value`` is a ``Password`` FormSpec value (rather than a ``PasswordId``)."""
    match value:
        case ("cmk_postprocessed", "explicit_password" | "stored_password", (str(), str())):
            return True
        case _:
            return False


def formspec_to_password_id(value: object) -> PasswordId:
    """Convert a ``Password`` FormSpec value to a ``PasswordId``. Idempotent for ``PasswordId``."""
    match value:
        case ("cmk_postprocessed", "explicit_password", (str(_password_id), str(secret))):
            return "password", secret
        case ("cmk_postprocessed", "stored_password", (str(password_store_id), str())):
            return "store", password_store_id
        case ("password", str(secret)):
            return "password", secret
        case ("store", str(password_store_id)):
            return "store", password_store_id
        case str(password_store_id):
            return password_store_id
        case _:
            raise ValueError(f"Cannot convert {value!r} to a password id.")


def target_config_from_ui(raw: Mapping[str, object]) -> TargetConfig:
    """Convert the setup form's output to the on-disk ``TargetConfig`` (secrets -> PasswordId)."""
    match raw:
        case {
            "title": str(title),
            "remote": ("local", {"path": str(path), "is_mountpoint": bool(is_mountpoint)}),
        }:
            return TargetConfig(
                title=title,
                remote=("local", LocalTargetParams(path=path, is_mountpoint=is_mountpoint)),
            )
        case {"title": str(title), "remote": ("aws_s3_bucket", dict() as params)}:
            return TargetConfig(title=title, remote=("aws_s3_bucket", _s3_from_form_spec(params)))
        case {"title": str(title), "remote": ("azure_blob_storage", dict() as params)}:
            return TargetConfig(
                title=title, remote=("azure_blob_storage", _blob_from_form_spec(params))
            )
        case _:
            raise ValueError(f"Invalid backup target parameters: {raw!r}")


def _s3_from_form_spec(raw: Mapping[str, object]) -> RemoteTargetParams[S3Params]:
    match raw:
        case {
            "remote": {
                "access_key": str(access_key),
                "secret": secret,
                "bucket": str(bucket),
                "endpoint_url": str(endpoint_url),
            },
            "temp_folder": {"path": str(path), "is_mountpoint": bool(is_mountpoint)},
        }:
            s3_params = S3Params(
                access_key=access_key,
                secret=formspec_to_password_id(secret),
                bucket=bucket,
                endpoint_url=endpoint_url,
            )
            return RemoteTargetParams(
                remote=s3_params,
                temp_folder=LocalTargetParams(path=path, is_mountpoint=is_mountpoint),
            )
        case {
            "remote": {"access_key": str(access_key), "secret": secret, "bucket": str(bucket)},
            "temp_folder": {"path": str(path), "is_mountpoint": bool(is_mountpoint)},
        }:
            s3_params = S3Params(
                access_key=access_key,
                secret=formspec_to_password_id(secret),
                bucket=bucket,
            )
            return RemoteTargetParams(
                remote=s3_params,
                temp_folder=LocalTargetParams(path=path, is_mountpoint=is_mountpoint),
            )
        case _:
            raise ValueError(f"Invalid AWS S3 backup target parameters: {raw!r}")


def _blob_from_form_spec(raw: Mapping[str, object]) -> RemoteTargetParams[BlobStorageParams]:
    match raw:
        case {
            "remote": {
                "storage_account_name": str(storage_account_name),
                "container": str(container),
                "credentials": credentials,
            },
            "temp_folder": {"path": str(path), "is_mountpoint": bool(is_mountpoint)},
        }:
            return RemoteTargetParams(
                remote=BlobStorageParams(
                    storage_account_name=storage_account_name,
                    container=container,
                    credentials=_credentials_from_form_spec(credentials),
                ),
                temp_folder=LocalTargetParams(path=path, is_mountpoint=is_mountpoint),
            )
        case _:
            raise ValueError(f"Invalid Azure Blob Storage backup target parameters: {raw!r}")


def _credentials_from_form_spec(raw: object) -> BlobStorageCredentials:
    match raw:
        case ("shared_key", shared_key):
            return "shared_key", formspec_to_password_id(shared_key)
        case (
            "active_directory",
            {
                "tenant_id": str(tenant_id),
                "client_id": str(client_id),
                "client_secret": client_secret,
            },
        ):
            return "active_directory", BlobStorageADCredentials(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=formspec_to_password_id(client_secret),
            )
        case _:
            raise ValueError(f"Unknown Azure Blob Storage credentials: {raw!r}")
