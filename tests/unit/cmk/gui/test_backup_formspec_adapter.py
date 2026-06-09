#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.gui.backup.formspec_adapter import target_config_from_ui
from cmk.gui.backup.handler import target_type_registry
from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DictElement,
    Dictionary,
    String,
)
from cmk.utils.backup.targets.aws_s3_bucket import S3Params
from cmk.utils.backup.targets.azure_blob_storage import (
    BlobStorageADCredentials,
    BlobStorageParams,
)
from cmk.utils.backup.targets.config import TargetConfig
from cmk.utils.backup.targets.local import LocalTargetParams
from cmk.utils.backup.targets.remote_interface import RemoteTargetParams

_TEMP_FOLDER = LocalTargetParams(path="/tmp/backup", is_mountpoint=False)


def _target_form_spec() -> Dictionary:
    return Dictionary(
        elements={
            "title": DictElement(required=True, parameter_form=String()),
            "remote": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    elements=[
                        CascadingSingleChoiceElement(
                            name=target_type.ident(),
                            title=Title(  # astrein: disable=localization-checker
                                target_type.title()
                            ),
                            parameter_form=target_type.form_spec(),
                        )
                        for target_type in target_type_registry.values()
                    ],
                ),
            ),
        }
    )


_LOCAL = TargetConfig(
    title="Local",
    remote=("local", LocalTargetParams(path="/backup", is_mountpoint=True)),
)

_S3_STORED_WITH_ENDPOINT = TargetConfig(
    title="S3 stored secret with endpoint",
    remote=(
        "aws_s3_bucket",
        RemoteTargetParams(
            remote=S3Params(
                access_key="AKIA",
                secret=("store", "s3-secret-id"),
                bucket="my-bucket",
                endpoint_url="https://s3.example.com",
            ),
            temp_folder=_TEMP_FOLDER,
        ),
    ),
)

_S3_EXPLICIT_NO_ENDPOINT = TargetConfig(
    title="S3 explicit secret without endpoint",
    remote=(
        "aws_s3_bucket",
        RemoteTargetParams(
            remote=S3Params(
                access_key="AKIA",
                secret=("password", "s3-secret-value"),
                bucket="my-bucket",
            ),
            temp_folder=_TEMP_FOLDER,
        ),
    ),
)

_AZURE_SHARED_KEY_STORED = TargetConfig(
    title="Azure shared key stored",
    remote=(
        "azure_blob_storage",
        RemoteTargetParams(
            remote=BlobStorageParams(
                storage_account_name="account",
                container="container",
                credentials=("shared_key", ("store", "shared-key-id")),
            ),
            temp_folder=_TEMP_FOLDER,
        ),
    ),
)

_AZURE_SHARED_KEY_EXPLICIT = TargetConfig(
    title="Azure shared key explicit",
    remote=(
        "azure_blob_storage",
        RemoteTargetParams(
            remote=BlobStorageParams(
                storage_account_name="account",
                container="container",
                credentials=("shared_key", ("password", "shared-key-value")),
            ),
            temp_folder=_TEMP_FOLDER,
        ),
    ),
)

_AZURE_ACTIVE_DIRECTORY_STORED = TargetConfig(
    title="Azure active directory stored",
    remote=(
        "azure_blob_storage",
        RemoteTargetParams(
            remote=BlobStorageParams(
                storage_account_name="account",
                container="container",
                credentials=(
                    "active_directory",
                    BlobStorageADCredentials(
                        tenant_id="tenant",
                        client_id="client",
                        client_secret=("store", "client-secret-id"),
                    ),
                ),
            ),
            temp_folder=_TEMP_FOLDER,
        ),
    ),
)

_AZURE_ACTIVE_DIRECTORY_EXPLICIT = TargetConfig(
    title="Azure active directory explicit",
    remote=(
        "azure_blob_storage",
        RemoteTargetParams(
            remote=BlobStorageParams(
                storage_account_name="account",
                container="container",
                credentials=(
                    "active_directory",
                    BlobStorageADCredentials(
                        tenant_id="tenant",
                        client_id="client",
                        client_secret=("password", "client-secret-value"),
                    ),
                ),
            ),
            temp_folder=_TEMP_FOLDER,
        ),
    ),
)

_ALL_TARGET_CONFIGS = [
    _LOCAL,
    _S3_STORED_WITH_ENDPOINT,
    _S3_EXPLICIT_NO_ENDPOINT,
    _AZURE_SHARED_KEY_STORED,
    _AZURE_SHARED_KEY_EXPLICIT,
    _AZURE_ACTIVE_DIRECTORY_STORED,
    _AZURE_ACTIVE_DIRECTORY_EXPLICIT,
]


@pytest.mark.parametrize(
    "target_config", _ALL_TARGET_CONFIGS, ids=[c["title"] for c in _ALL_TARGET_CONFIGS]
)
def test_target_config_round_trips_through_form_visitor(
    request_context: None, target_config: TargetConfig
) -> None:
    form_value = RawDiskData(target_config)

    visitor = get_visitor(
        _target_form_spec(), VisitorOptions(migrate_values=True, mask_values=False)
    )
    parsed_from_form = visitor.to_disk(form_value)

    assert isinstance(parsed_from_form, dict)
    assert target_config_from_ui(parsed_from_form) == target_config
