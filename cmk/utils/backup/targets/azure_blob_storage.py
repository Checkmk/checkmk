#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path
from typing import assert_never, Final, Literal, TYPE_CHECKING, TypedDict, Union

from cmk.ccc.exceptions import MKGeneralException

from cmk.utils.backup.targets.remote_interface import ProgressStepLogger, RemoteTarget
from cmk.utils.password_store import extract, PasswordId

if TYPE_CHECKING:
    # Conditional import to only consume the necessary memory when the feature is used
    from azure.identity import ClientSecretCredential


class BlobStorageADCredentials(TypedDict):
    tenant_id: str
    client_id: str
    client_secret: PasswordId


BlobStorageCredentials = (
    tuple[Literal["shared_key"], PasswordId]
    | tuple[Literal["active_directory"], BlobStorageADCredentials]
)


class BlobStorageParams(TypedDict):
    storage_account_name: str
    container: str
    credentials: BlobStorageCredentials


class BlobStorage:
    def __init__(self, params: BlobStorageParams) -> None:
        self.account_url: Final = f"https://{params['storage_account_name']}.blob.core.windows.net"
        # Conditional import to only consume the necessary memory when the feature is used
        from azure.storage.blob import ContainerClient, LinearRetry

        self.container_client: Final = ContainerClient(
            account_url=self.account_url,
            container_name=params["container"],
            credential=self._credentials(params["credentials"]),
            retry_policy=LinearRetry(retry_total=0),
        )

    def ready(self) -> None:
        try:
            container_exists = self.container_client.exists()
        except Exception as e:
            raise MKGeneralException(
                "Failed to check if the specified container exists. Likely causes:"
                "<ul>"
                f'<li>Storage account does not exist. To verify this, check if the <a href="{self.account_url}">account url</a> is reachable.</li>'
                "<li>Wrong credentials.</li>"
                "<li>Issues with the internet access of your Checkmk server.</li>"
                "</ul>"
                f"Original error message: {e}."
            )
        if not container_exists:
            raise MKGeneralException(
                "The specified container does not exist within the specified storage account."
            )

    def download(self, key: Path, target: Path) -> Path:
        target_file_path = target / key
        target_file_path.parent.mkdir(parents=True, exist_ok=True)
        with target_file_path.open(mode="wb") as download_destination:
            self.container_client.download_blob(
                str(key),
                progress_hook=_BlobStorageLogger(),
            ).readinto(download_destination)
        return target_file_path

    def upload(self, file: Path, key: Path) -> None:
        with file.open(mode="rb") as upload_data:
            self.container_client.upload_blob(
                str(key),
                upload_data,
                overwrite=True,
                progress_hook=_BlobStorageLogger(),
            )

    def remove(self, key: Path) -> None:
        self.container_client.delete_blob(str(key))

    def objects(self) -> Iterator[Path]:
        yield from (Path(blob_name) for blob_name in self.container_client.list_blob_names())

    # NOTE: We can't use the '|' operator below because of the forward reference.
    @staticmethod
    def _credentials(
        configured_credentials: BlobStorageCredentials,
    ) -> Union[str, "ClientSecretCredential"]:
        # Conditional import to only consume the necessary memory when the feature is used
        from azure.identity import ClientSecretCredential

        # a match statement would be perfect here but the type narrowing does not seem to work in
        # this particular case with a match statement :(
        if configured_credentials[0] == "shared_key":
            if not (shared_key := extract(configured_credentials[1])):
                raise MKGeneralException("Failed to retrieve storage account shared key")
            return shared_key
        if configured_credentials[0] == "active_directory":
            ad_credentials = configured_credentials[1]
            if not (client_secret := extract(ad_credentials["client_secret"])):
                raise MKGeneralException("Failed to retrieve client secret")

            return ClientSecretCredential(
                tenant_id=ad_credentials["tenant_id"],
                client_id=ad_credentials["client_id"],
                client_secret=client_secret,
            )
        return assert_never(configured_credentials)


class BlobStorageTarget(RemoteTarget[BlobStorageParams, BlobStorage]):
    @staticmethod
    def _remote_storage(remote_params: BlobStorageParams) -> BlobStorage:
        return BlobStorage(remote_params)


class _BlobStorageLogger:
    def __init__(self) -> None:
        self.logger: Final = ProgressStepLogger()

    def __call__(self, current: int, total: int | None) -> None:
        if not total:
            return
        self.logger(current / total * 100)
