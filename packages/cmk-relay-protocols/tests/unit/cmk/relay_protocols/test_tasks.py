#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from pydantic import ValidationError

from cmk.relay_protocols.tasks import (
    AdHocActiveCheckTask,
    AdHocPasswordStore,
    AdHocSiteStores,
    TaskCreateRequest,
    TaskResponse,
)


def test_fields_and_default_timeout() -> None:
    task = AdHocActiveCheckTask(host="myhost", command="check_icmp 1.2.3.4")
    assert task.host == "myhost"
    assert task.command == "check_icmp 1.2.3.4"
    assert task.timeout == 60.0
    assert task.type == "AD_HOC_ACTIVE_CHECK"


def test_discriminated_in_create_request() -> None:
    request = TaskCreateRequest.model_validate(
        {"spec": {"type": "AD_HOC_ACTIVE_CHECK", "host": "h", "command": "c"}}
    )
    assert isinstance(request.spec, AdHocActiveCheckTask)


def test_discriminated_in_task_response() -> None:
    response = TaskResponse.model_validate(
        {
            "spec": {"type": "AD_HOC_ACTIVE_CHECK", "host": "h", "command": "c"},
            "status": "PENDING",
            "result_type": None,
            "result_payload": None,
            "creation_timestamp": "2026-01-01T00:00:00",
            "update_timestamp": "2026-01-01T00:00:00",
            "id": "task-1",
        }
    )
    assert isinstance(response.spec, AdHocActiveCheckTask)


def test_without_site_stores_the_task_means_the_applied_configuration() -> None:
    task = AdHocActiveCheckTask.model_validate({"host": "h", "command": "c"})

    assert task.site_stores is None


def test_site_stores_survive_the_round_trip_through_json() -> None:
    task = AdHocActiveCheckTask(
        host="h",
        command="check_httpv2 --auth-pw-pwstore uuid1:tmp/check_mk/passwords_adhoc_1",
        site_stores=AdHocSiteStores(
            ca_bundle="-----BEGIN CERTIFICATE-----\nMIIB...\n-----END CERTIFICATE-----\n",
            passwords=AdHocPasswordStore(
                path="tmp/check_mk/passwords_adhoc_1", values={"uuid1": "s3cret"}
            ),
        ),
    )

    assert AdHocActiveCheckTask.model_validate_json(task.model_dump_json()) == task


def test_site_stores_always_name_the_ca_bundle() -> None:
    """Passwords alone would leave the relay guessing which CAs the check is to trust."""
    with pytest.raises(ValidationError, match="ca_bundle"):
        AdHocSiteStores.model_validate(
            {"passwords": {"path": "tmp/check_mk/passwords_adhoc_1", "values": {}}}
        )


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/omd/sites/mysite/tmp/check_mk/passwords_adhoc_1", id="absolute"),
        pytest.param("tmp/check_mk", id="the directory itself"),
        pytest.param("tmp/check_mk/../../etc/password_store.secret", id="leaves the directory"),
        pytest.param(
            "var/check_mk/core/helper_config/latest/secrets/active_secrets", id="elsewhere"
        ),
    ],
)
def test_a_store_path_outside_the_ad_hoc_files_dir_is_rejected(path: str) -> None:
    with pytest.raises(ValidationError, match="below tmp/check_mk"):
        AdHocPasswordStore(path=path, values={})
