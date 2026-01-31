#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Iterator
from pathlib import Path
from typing import Final, TypedDict

from cmk.ccc.exceptions import MKGeneralException
from cmk.utils.backup.targets.remote_interface import ProgressStepLogger, RemoteTarget
from cmk.utils.password_store import extract, PasswordId


class S3Params(TypedDict, total=False):
    access_key: str
    secret: PasswordId
    bucket: str
    endpoint_url: str  # Optional: für S3-kompatible Anbieter wie Backblaze


class S3Bucket:
    def __init__(self, params: S3Params) -> None:
        # Conditional import to only consume the necessary memory when the feature is used
        import boto3

        if not (secret_extracted := extract(params["secret"])):
            raise MKGeneralException("Failed to retrieve secret")

        endpoint_url = params.get("endpoint_url")
        client_args = dict(
            aws_access_key_id=params["access_key"],
            aws_secret_access_key=secret_extracted,
        )
        if endpoint_url:
            client_args["endpoint_url"] = endpoint_url

        self.client: Final = boto3.client("s3", **client_args)
        self.bucket: Final = boto3.resource("s3", **client_args).Bucket(params["bucket"])

    def ready(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket.name)
        except Exception as e:
            raise MKGeneralException(
                f"Failed to access bucket {self.bucket.name}. Likely causes:"
                "<ul>"
                "<li>Bucket does not exist.</li>"
                "<li>Wrong credentials.</li>"
                "<li>The specified AWS account does not have access to the bucket.</li>"
                "<li>Issues with the internet access of your Checkmk server.</li>"
                "</ul>"
                f"Original error message: {e}."
            )

    def download(self, key: Path, target: Path) -> Path:
        target_file_path = target / key
        target_file_path.parent.mkdir(parents=True, exist_ok=True)
        s3_object = self.bucket.Object(str(key))
        s3_object.download_file(
            str(target_file_path),
            Callback=_S3Logger(total_size=s3_object.content_length),
        )
        return target_file_path

    def upload(self, file: Path, key: Path) -> None:
        self.bucket.upload_file(
            str(file.absolute()),
            str(key),
            Callback=_S3Logger(total_size=file.stat().st_size),
        )

    def remove(self, key: Path) -> None:
        self.bucket.delete_objects(Delete={"Objects": [{"Key": str(key)}]})

    def objects(self) -> Iterator[Path]:
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket.name):
            for obj in page["Contents"]:
                yield Path(obj["Key"])


class S3Target(RemoteTarget[S3Params, S3Bucket]):
    @staticmethod
    def _remote_storage(remote_params: S3Params) -> S3Bucket:
        return S3Bucket(remote_params)


class _S3Logger:
    def __init__(self, *, total_size: int) -> None:
        self.total_size: Final = total_size
        self.logger: Final = ProgressStepLogger()
        self._currently_done = 0

    def __call__(self, increment: int) -> None:
        self._currently_done += increment
        self.logger(self._currently_done / self.total_size * 100)
