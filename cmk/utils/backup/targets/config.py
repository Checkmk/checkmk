#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#########################################
# Schemas to share with CMA Backup tool #
# DO NOT CHANGE!                        #
#########################################

from typing import Literal, TypedDict

from .aws_s3_bucket import S3Params
from .azure_blob_storage import BlobStorageParams
from .local import LocalTargetParams
from .remote_interface import RemoteTargetParams

# these classes are only needed to make pydantic understand TargetConfig, otherwise we could
# simple use RemoteTargetParams[...]


class _S3TargetParams(RemoteTargetParams[S3Params]): ...


class _BlobStorageTargetParams(RemoteTargetParams[BlobStorageParams]): ...


LocalTargetConfig = tuple[Literal["local"], LocalTargetParams]
S3TargetConfig = tuple[Literal["aws_s3_bucket"], _S3TargetParams]
BlobStorageTargetConfig = tuple[Literal["azure_blob_storage"], _BlobStorageTargetParams]


class TargetConfig(TypedDict):
    title: str
    remote: LocalTargetConfig | S3TargetConfig | BlobStorageTargetConfig
