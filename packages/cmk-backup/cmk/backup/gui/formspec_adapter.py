#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Explicit boundary between the on-disk ``TargetConfig`` and the setup form's ``Password``
FormSpec representation.

The setup form speaks the FormSpec password shape; the on-disk ``TargetConfig`` (shared with the
CMA appliance tool) stores secrets as a ``PasswordId``. This adapter converts in both directions
so the form does not depend on a ``migrate=`` callback to do the steady-state transform.
"""

from collections.abc import Mapping

from cmk.backup.utils.targets.aws_s3_bucket import S3Params
from cmk.backup.utils.targets.azure_blob_storage import (
    BlobStorageADCredentials,
    BlobStorageCredentials,
    BlobStorageParams,
)
from cmk.backup.utils.targets.config import TargetConfig
from cmk.backup.utils.targets.local import LocalTargetParams
from cmk.backup.utils.targets.remote_interface import RemoteTargetParams
from cmk.gui.form_specs import (
    formspec_to_password_id,
    password_id_to_formspec,
    RawDiskData,
)


class FormspecAdapter:
    @staticmethod
    def from_form_spec(raw: Mapping[str, object]) -> TargetConfig:
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
                return TargetConfig(
                    title=title, remote=("aws_s3_bucket", _s3_from_form_spec(params))
                )
            case {"title": str(title), "remote": ("azure_blob_storage", dict() as params)}:
                return TargetConfig(
                    title=title, remote=("azure_blob_storage", _blob_from_form_spec(params))
                )
            case _:
                raise ValueError(f"Invalid backup target parameters: {raw!r}")

    @staticmethod
    def to_form_spec(target_config: TargetConfig) -> RawDiskData:
        """Convert the on-disk ``TargetConfig`` to the form's input (secrets -> FormSpec)."""
        remote = target_config["remote"]
        if remote[0] == "aws_s3_bucket":
            s3_params = remote[1]
            form_remote = {**s3_params, "remote": _s3_to_form_spec(s3_params["remote"])}
            return RawDiskData({**target_config, "remote": ("aws_s3_bucket", form_remote)})
        if remote[0] == "azure_blob_storage":
            blob_params = remote[1]
            form_remote = {**blob_params, "remote": _blob_to_form_spec(blob_params["remote"])}
            return RawDiskData({**target_config, "remote": ("azure_blob_storage", form_remote)})
        # "local" has no secret to convert.
        return RawDiskData(target_config)


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


def _s3_to_form_spec(remote: S3Params) -> Mapping[str, object]:
    return {**remote, "secret": password_id_to_formspec(remote["secret"])}


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


def _blob_to_form_spec(remote: BlobStorageParams) -> Mapping[str, object]:
    return {**remote, "credentials": _credentials_to_form_spec(remote["credentials"])}


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


def _credentials_to_form_spec(credentials: BlobStorageCredentials) -> object:
    if credentials[0] == "shared_key":
        return "shared_key", password_id_to_formspec(credentials[1])
    ad = credentials[1]
    return "active_directory", {
        **ad,
        "client_secret": password_id_to_formspec(ad["client_secret"]),
    }
