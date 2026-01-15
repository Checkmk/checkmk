#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
import urllib.parse
import uuid
from ast import literal_eval
from collections.abc import Sequence

import pytest

from cmk.ccc import version
from cmk.ccc.user import UserId
from cmk.gui.fields import FOLDER_PATTERN, FolderField
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.watolib.predefined_conditions import PredefinedConditionStore
from cmk.utils import paths
from tests.testlib.unit.rest_api_client import ClientRegistry
from tests.unit.cmk.web_test_app import WebTestAppForCMK


@pytest.mark.parametrize(
    "given, expected",
    [
        ("%%%%", False),
        ("root", False),
        ("/", True),
        ("/foo", True),
        ("/foo/bar", True),
        ("/foo/bar/", True),
        ("//", False),
        ("///", False),
        ("\\", True),
        ("\\foo", True),
        ("\\foo\\bar", True),
        ("\\foo\\bar\\", True),
        ("\\\\", False),
        ("\\\\\\", False),
        ("~", True),
        ("~foo", True),
        ("~foo~bar", True),
        ("~foo~bar~", True),
        ("~~", False),
        ("~~~", False),
        # This really should be false, but it is tricky to implement. Skipped for now.
        # ('/foo~bar\\baz', False),
        ("0123456789ABCDEF0123456789ABCDEF", True),
        ("0123456789ABCDEF0123456789ABCDEFG", False),
        ("0123456789abcdef0123456789abcdef", True),
        ("0123456789abcdef0123456789abcdefg", False),
        ("~DCN~DE.KAE.BS", True),
    ],
)
def test_folder_regexp(given: str, expected: bool) -> None:
    regexp = re.compile(f"(?:^{FOLDER_PATTERN})$")
    match = regexp.findall(given)
    assert bool(match) == expected, match


@pytest.mark.usefixtures("request_context")
def test_folder_schema() -> None:
    class FolderSchema(BaseSchema):
        folder = FolderField(required=True)

    schema = FolderSchema()
    assert schema.load({"folder": "/"})["folder"]
    assert schema.load({"folder": "\\"})["folder"]
    assert schema.load({"folder": "~"})["folder"]


def test_openapi_folder_validation(
    aut_user_auth_wsgi_app: WebTestAppForCMK, clients: ClientRegistry
) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "abababaabababaababababbbabababab"}',
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/", "attributes": {"foo": "bar"}}',
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    clients.Folder.create(
        folder_name="\\",
        title="test",
        parent="~",
        expect_ok=False,
    )


def test_openapi_folders_recursively(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all?recursive=1",
        status=200,
        headers={"Accept": "application/json"},
    )
    assert len(resp.json["value"]) == 1


def test_openapi_folders(clients: ClientRegistry) -> None:
    resp = clients.Folder.get_all()
    assert resp.json["value"] == []

    # Create folder /other_folder with title = bar
    clients.Folder.create(
        parent="/",
        folder_name="other_folder",
        title="bar",
    )

    # Create folder ~new_folder with title = foo
    clients.Folder.create(
        parent="~",
        folder_name="new_folder",
        title="foo",
        attributes={"tag_agent": "no-agent", "tag_piggyback": "auto-piggyback"},
    )

    # Create folder ~new_folder/sub_folder with title = foo
    clients.Folder.create(
        parent="~new_folder",
        folder_name="sub_folder",
        title="foo",
    )

    # First test without an ETag, fails with 428 (precondition required)
    clients.Folder.edit(
        folder_name="~new_folder",
        title="foobar",
        remove_attributes=["tag_agent", "tag_piggyback"],
        etag=None,
        expect_ok=False,
    ).assert_status_code(428)

    # First test without the proper ETag, fails with 412 (precondition failed)
    clients.Folder.edit(
        folder_name="~new_folder",
        title="foobar",
        remove_attributes=["tag_agent", "tag_piggyback"],
        etag="invalid_etag",
        expect_ok=False,
    ).assert_status_code(412)

    # With the right ETag, the operation shall succeed
    clients.Folder.edit(
        folder_name="~new_folder",
        title="foobar",
        remove_attributes=["tag_agent", "tag_piggyback"],
        etag="valid_etag",
    )

    # Even twice, as this is idempotent.
    clients.Folder.edit(
        folder_name="~new_folder",
        title="foobar",
        remove_attributes=[],
        etag="valid_etag",
    )

    # Move to the same source should give a 400
    clients.Folder.move(
        folder_name="~new_folder",
        destination="~",
        expect_ok=False,
    ).assert_status_code(400)

    # Check that unknown folders also give a 400
    clients.Folder.move(
        folder_name="~new_folder",
        destination="unknown_folder",
        expect_ok=False,
    ).assert_status_code(400)

    # Check that moving onto itself gives a 400
    clients.Folder.move(
        folder_name="~other_folder",
        destination="~other_folder",
        expect_ok=False,
    ).assert_status_code(400)

    # Check that moving into it's own subfolder is not possible.
    clients.Folder.move(
        folder_name="~new_folder",
        destination="/new_folder/sub_folder",
        expect_ok=False,
    ).assert_status_code(400)

    # Should succeed
    clients.Folder.move(
        folder_name="~new_folder",
        destination="~other_folder",
    )

    # Delete all folders.
    for folder_obj in clients.Folder.get_all().json["value"]:
        clients.Folder.delete(folder_name=folder_obj["id"])


def test_openapi_folder_non_existent_site(clients: ClientRegistry) -> None:
    folder_name = "my_folder"
    non_existing_site_name = "i_am_not_existing"
    clients.Folder.create(
        folder_name=folder_name,
        title="My super folder",
        parent="/",
    ).assert_status_code(200)
    resp = clients.Folder.edit(
        folder_name=f"~{folder_name}",
        update_attributes={"site": non_existing_site_name},
        expect_ok=False,
    )
    resp.assert_status_code(400)
    assert "site" in resp.json["fields"]["update_attributes"]


def test_openapi_folder_config_collections(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/host_config/collections/all",
        params='{"host_name": "host-1", "folder": "/new_folder"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/host_config/collections/all",
        params='{"host_name": "host-2", "folder": "/new_folder"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )


@pytest.mark.usefixtures("with_host")
def test_openapi_hosts_in_folder(clients: ClientRegistry) -> None:
    clients.Folder.get_hosts("~")


def test_openapi_hosts_in_folder_collection(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/host_config/collections/all",
        params='{"host_name": "host-1", "folder": "/new_folder"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/host_config/collections/all",
        params='{"host_name": "host-2", "folder": "/new_folder"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        query_string={"show_hosts": True},
        headers={"Accept": "application/json"},
        content_type="application/json",
        status=200,
    )
    hosts_ = resp.json["value"][0]["members"]["hosts"]["value"]
    assert len(hosts_) == 2
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        query_string={"show_hosts": False},
        headers={"Accept": "application/json"},
    )
    assert "hosts" not in resp.json["value"][0]["members"]


def _create_criticality_tag(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/host_tag_group/collections/all",
        params=json.dumps(
            {
                "id": "criticality",
                "title": "criticality",
                "topic": "nothing",
                "tags": [
                    {
                        "id": "discovered",
                        "title": "discovered",
                    }
                ],
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )


def test_openapi_create_folder_with_network_scan(
    aut_user_auth_wsgi_app: WebTestAppForCMK, with_automation_user: tuple[UserId, str]
) -> None:
    _create_criticality_tag(aut_user_auth_wsgi_app)
    user, _ = with_automation_user
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params=json.dumps(
            {
                "name": "folder-1",
                "title": "some title",
                "parent": "~",
                "attributes": {
                    "network_scan": {
                        "addresses": [
                            {"type": "network_range", "network": "172.10.9.0/24"},
                            {
                                "addresses": ["10.10.10.10", "10.10.10.9"],
                                "type": "explicit_addresses",
                            },
                            {
                                "from_address": "192.168.178.10",
                                "to_address": "192.168.178.20",
                                "type": "address_range",
                            },
                        ],
                        "exclude_addresses": [
                            {"regexp_list": ["some_pattern"], "type": "exclude_by_regexp"}
                        ],
                        "scan_interval": 86400,
                        "time_allowed": [{"start": "00:00:00", "end": "23:00:00"}],
                        "set_ip_address": True,
                        "tag_criticality": "discovered",
                        "run_as": user,
                        "translate_names": {"drop_domain": True, "convert_case": "lower"},
                    }
                },
            }
        ),
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )
    path = paths.omd_root / "etc/check_mk/conf.d/wato/folder-1/.wato"
    with path.open() as fo:
        result = literal_eval(fo.read())
    assert user == result["attributes"]["network_scan"].pop("run_as")
    assert result["attributes"]["network_scan"] == {
        "exclude_ranges": [("ip_regex_list", ["some_pattern"])],
        "ip_ranges": [
            ("ip_network", ("172.10.9.0", 24)),
            ("ip_list", ["10.10.10.10", "10.10.10.9"]),
            ("ip_range", ("192.168.178.10", "192.168.178.20")),
        ],
        "max_parallel_pings": 100,
        "scan_interval": 86400,
        "set_ipaddress": True,
        "time_allowed": [((0, 0), (23, 0))],
        "tag_criticality": "discovered",
        "translate_names": {"case": "lower", "drop_domain": True},
    }


def test_openapi_show_folder_with_network_scan_result(
    aut_user_auth_wsgi_app: WebTestAppForCMK, with_automation_user: tuple[UserId, str]
) -> None:
    _create_criticality_tag(aut_user_auth_wsgi_app)
    path = paths.omd_root / "etc/check_mk/conf.d/wato/folder-2/.wato"
    path.parent.mkdir(parents=True, exist_ok=True)
    user, _ = with_automation_user
    with path.open("w") as fo:
        fo.write(
            str(
                {
                    "title": "Clients (9)",
                    "attributes": {
                        "network_scan": {
                            "ip_ranges": [
                                ("ip_network", ("172.10.9.0", 24)),
                                ("ip_list", ["10.10.10.10", "10.10.10.9"]),
                                ("ip_range", ("192.168.178.10", "192.168.178.20")),
                            ],
                            "exclude_ranges": [("ip_regex_list", ["some_pattern"])],
                            "scan_interval": 86400,
                            "time_allowed": [((0, 0), (23, 0))],
                            "set_ipaddress": True,
                            "tag_criticality": "discovered",
                            "run_as": user,
                            "translate_names": {"drop_domain": True, "case": "lower"},
                        },
                        "network_scan_result": {
                            "start": 1661972701.0,
                            "end": 1661972713.0,
                            "state": True,
                            "output": "The network scan found 10 new hosts.",
                        },
                        "meta_data": {
                            "created_at": 1635451787.0,
                            "created_by": user,
                            "updated_at": 1661980583.1332564,
                        },
                    },
                    "num_hosts": 40,
                    "lock": False,
                    "lock_subfolders": False,
                    "__id": "cf2b6294fec34e57af4a164ee99134d7",
                }
            )
        )
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        query_string={"show_hosts": False},
        headers={"Accept": "application/json"},
    )
    assert resp.json["value"][0]["extensions"] == {
        "path": "/folder-2",
        "attributes": {
            "network_scan": {
                "addresses": [
                    {"type": "network_range", "network": "172.10.9.0/24"},
                    {
                        "addresses": ["10.10.10.10", "10.10.10.9"],
                        "type": "explicit_addresses",
                    },
                    {
                        "from_address": "192.168.178.10",
                        "to_address": "192.168.178.20",
                        "type": "address_range",
                    },
                ],
                "exclude_addresses": [
                    {"regexp_list": ["some_pattern"], "type": "exclude_by_regexp"}
                ],
                "scan_interval": 86400,
                "time_allowed": [{"start": "00:00:00", "end": "23:00:00"}],
                "set_ip_address": True,
                "tag_criticality": "discovered",
                "run_as": user,
                "translate_names": {"convert_case": "lower", "drop_domain": True},
            },
            "network_scan_result": {
                "start": "2022-08-31T19:05:01+00:00",
                "end": "2022-08-31T19:05:13+00:00",
                "state": "succeeded",
                "output": "The network scan found 10 new hosts.",
            },
            "meta_data": {
                "created_at": "2021-10-28T20:09:47+00:00",
                "updated_at": "2022-08-31T21:16:23.133256+00:00",
                "created_by": user,
            },
        },
    }


def test_openapi_show_hosts_on_folder(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/objects/folder_config/~new_folder",
        query_string={"show_hosts": True},
        status=200,
        headers={"Accept": "application/json"},
    )
    hosts_ = resp.json["members"]["hosts"]
    assert len(hosts_) > 0

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/objects/folder_config/~new_folder",
        query_string={"show_hosts": False},
        status=200,
        headers={"Accept": "application/json"},
    )
    assert "hosts" not in resp.json["members"]


def test_openapi_missing_folder(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    resp = aut_user_auth_wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/objects/folder_config/asdf" + uuid.uuid4().hex,
        status=404,
        headers={"Accept": "application/json"},
    )
    assert "title" in resp.json


def test_openapi_update_with_invalid_attribute_folder(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        params='{"name": "new_folder", "title": "foo", "parent": "/"}',
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        status=400,
        params=json.dumps({"title": "foo", "remove_attributes": ["tag_foobar"]}),
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )


def test_openapi_update_with_invalid_title(
    clients: ClientRegistry,
) -> None:
    clients.Folder.create(
        folder_name="new_folder",
        title="foo",
        parent="~",
    )

    clients.Folder.edit(
        folder_name="~new_folder",
        title="",
        expect_ok=False,
    ).assert_status_code(400)

    clients.Folder.edit(
        folder_name="~new_folder",
        update_attributes={"labels": "do_not_update:title"},
        expect_ok=False,
    ).assert_status_code(400)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_bulk_actions_folders(clients: ClientRegistry) -> None:
    clients.Folder.create(
        parent="~",
        folder_name="new_folder",
        title="foo",
    )

    # remove an attribute that the folder doesn't have
    clients.Folder.bulk_edit(
        entries=[
            {
                "folder": "~new_folder",
                "remove_attributes": ["tag_foobar"],
            }
        ],
        expect_ok=False,
    ).assert_status_code(400)

    # add tag_address_family
    clients.Folder.bulk_edit(
        entries=[
            {
                "folder": "~new_folder",
                "attributes": {"tag_address_family": "ip-v4-only"},
            }
        ],
    )

    # check label was added
    resp = clients.Folder.get("~new_folder")
    assert resp.json["extensions"]["attributes"]["tag_address_family"] == "ip-v4-only"

    # remove tag_address_family
    clients.Folder.bulk_edit(
        entries=[
            {
                "folder": "~new_folder",
                "remove_attributes": ["tag_address_family"],
            }
        ],
    )

    # check label was removed
    resp = clients.Folder.get("~new_folder")
    assert "tag_address_family" not in resp.json["extensions"]["attributes"]


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_folder_update(clients: ClientRegistry) -> None:
    clients.Folder.create(
        parent="/",
        folder_name="new_folder",
        title="foo",
        attributes={"tag_address_family": "ip-v6-only"},
    )

    # make sure we can update a folder without title argument (SUP-7195)
    resp = clients.Folder.edit(
        folder_name="~new_folder",
        update_attributes={"tag_address_family": "no-ip"},
    )

    # title should not change
    assert resp.json["title"] == "foo"

    # double check
    resp = clients.Folder.get("~new_folder")
    assert resp.json["title"] == "foo"

    # actually change the title
    resp = clients.Folder.edit(
        folder_name="~new_folder",
        title="fo",
    )
    assert resp.json["title"] == "fo"

    # double check
    resp = clients.Folder.get("~new_folder")
    assert resp.json["title"] == "fo"


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_folder_root(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    _ = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/objects/folder_config/~",
        query_string={"show_hosts": False},
        headers={"Accept": "application/json"},
        status=200,
    )


def test_openapi_folder_remove_attribute(clients: ClientRegistry) -> None:
    clients.Folder.create(
        parent="/",
        folder_name="new_folder",
        title="foo",
        attributes={"tag_address_family": "ip-v6-only"},
    )

    resp = clients.Folder.edit(
        folder_name="~new_folder",
        title="food",
        remove_attributes=["tag_address_family"],
    )
    assert "tag_address_family" not in resp.json["extensions"]["attributes"]

    # make sure changes are written to disk:
    resp = clients.Folder.get("~new_folder")
    assert "tag_address_family" not in resp.json["extensions"]["attributes"]


def test_openapi_folder_config_collections_recursive_list(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    def _create_folder(fname: str, parent: str) -> None:
        params = f'{{"name": "{fname}", "title": "{fname}", "parent": "{parent}"}}'
        aut_user_auth_wsgi_app.call_method(
            "post",
            "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
            params=params,
            status=200,
            headers={"Accept": "application/json"},
            content_type="application/json",
        )
        parent += f"{fname}~"

    def _create_folders_recursive(folders: Sequence[str]) -> None:
        _create_folder(folders[0], "~")
        parent = f"~{folders[0]}"
        for fname in folders[1:]:
            _create_folder(fname, parent)
            parent += f"~{fname}"

    _create_folders_recursive(["I", "want", "those"])
    _create_folders_recursive(["na", "na", "batman"])

    response = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        query_string={"parent": "~I", "recursive": "True"},
        status=200,
        headers={"Accept": "application/json"},
    )

    for folder in response.json["value"]:
        assert "batman" not in folder["id"]


@pytest.mark.skipif(
    version.edition(paths.omd_root) is version.Edition.COMMUNITY,
    reason="Tested Attribute is not in RAW",
)
def test_bake_agent_package_attribute_regression(
    clients: ClientRegistry, base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    folder_name = "blablabla"

    clients.Folder.create(
        folder_name=folder_name,
        title=folder_name,
        parent="~",
        attributes={"bake_agent_package": True},
    ).assert_status_code(200)

    # see if we get an outbound validation error on a single folder
    clients.Folder.get(folder_name=f"~{folder_name}").assert_status_code(200)

    # see if we get an outbound validation error on all folders
    clients.Folder.get_all().assert_status_code(200)


def test_delete_root_folder(
    base: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    resp = aut_user_auth_wsgi_app.delete(
        url=base + "/objects/folder_config/~",
        headers={"Accept": "application/json"},
        status=401,
    )
    assert resp.json["title"] == "Problem deleting folder."
    assert resp.json["detail"] == "Deleting the root folder is not permitted."


def test_create_folder_with_name_as_empty_string(clients: ClientRegistry) -> None:
    r = clients.Folder.create(
        folder_name="",
        title="some_foldeer_title",
        parent="~",
        expect_ok=False,
    )
    assert r.json["detail"] == "These fields have problems: name"
    assert r.json["fields"]["name"][0] == "string '' is too short. The minimum length is 1."


def test_openapi_folder_config_folders_with_duplicate_names_allowed_regression(
    clients: ClientRegistry,
) -> None:
    resp = clients.Folder.create(folder_name=None, title="a_duplicate", parent="~")
    assert resp.json["id"] == "~a_duplicate"

    resp = clients.Folder.create(folder_name=None, title="a_duplicate", parent="~")
    assert resp.json["id"] == "~a_duplicate-2"

    resp = clients.Folder.create(folder_name=None, title="a_duplicate", parent="~")
    assert resp.json["id"] == "~a_duplicate-3"

    wato_dir = paths.check_mk_config_dir / "wato"
    assert (wato_dir / "a_duplicate").exists()
    assert (wato_dir / "a_duplicate-2").exists()
    assert (wato_dir / "a_duplicate-3").exists()

    folders = [folder["id"] for folder in clients.Folder.get_all().json["value"]]
    assert "~a_duplicate" in folders
    assert "~a_duplicate-2" in folders
    assert "~a_duplicate-3" in folders


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_bulk_update_actions(clients: ClientRegistry) -> None:
    clients.Folder.create(
        parent="~",
        folder_name="new_folder",
        title="foo",
    )

    clients.Folder.bulk_edit(
        entries=[
            {
                "folder": "~new_folder",
                "update_attributes": {"tag_address_family": "ip-v4-only"},
            }
        ],
    )

    # check label was added
    resp = clients.Folder.get("~new_folder")
    assert resp.json["extensions"]["attributes"]["tag_address_family"] == "ip-v4-only"

    # remove tag_address_family
    clients.Folder.bulk_edit(
        entries=[
            {
                "folder": "~new_folder",
                "remove_attributes": ["tag_address_family"],
            }
        ],
    )

    # check label was removed
    resp = clients.Folder.get("~new_folder")
    assert "tag_address_family" not in resp.json["extensions"]["attributes"]


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_only_one_edit_action(clients: ClientRegistry) -> None:
    clients.Folder.create(
        parent="~",
        folder_name="new_folder",
        title="foo",
        attributes={"tag_address_family": "ip-v6-only"},
    )

    resp1 = clients.Folder.edit(
        folder_name="~new_folder",
        title="foobar",
        attributes={},
        remove_attributes=["tag_agent", "tag_piggyback"],
        update_attributes={"tag_address_family": "ip-v4-only"},
        etag=None,
        expect_ok=False,
    )
    resp1.assert_status_code(400)
    assert (
        "This endpoint only allows 1 action (set/update/remove) per call, you specified"
        in resp1.json["fields"]["_schema"][0]
    )

    resp2 = clients.Folder.edit(
        folder_name="~new_folder",
        title="foobar",
        remove_attributes=["tag_agent", "tag_piggyback"],
        update_attributes={"tag_address_family": "ip-v4-only"},
        etag=None,
        expect_ok=False,
    )
    resp2.assert_status_code(400)
    assert (
        "This endpoint only allows 1 action (set/update/remove) per call, you specified"
        in resp1.json["fields"]["_schema"][0]
    )

    resp3 = clients.Folder.edit(
        folder_name="~new_folder",
        title="foobar",
        attributes={},
        update_attributes={"tag_address_family": "ip-v4-only"},
        etag=None,
        expect_ok=False,
    )
    resp3.assert_status_code(400)
    assert (
        "This endpoint only allows 1 action (set/update/remove) per call, you specified"
        in resp1.json["fields"]["_schema"][0]
    )

    resp4 = clients.Folder.edit(
        folder_name="~new_folder",
        title="foobar",
        attributes={},
        remove_attributes=["tag_agent", "tag_piggyback"],
        etag=None,
        expect_ok=False,
    )
    resp4.assert_status_code(400)
    assert (
        "This endpoint only allows 1 action (set/update/remove) per call, you specified"
        in resp1.json["fields"]["_schema"][0]
    )


invalid_folder_names = (
    "folderA\\n",
    "folderB\n",
    "folder\nC",
    "\nfolderD",
)


@pytest.mark.parametrize("folder_name", invalid_folder_names)
def test_create_folder_name_with_newline(
    clients: ClientRegistry,
    folder_name: str,
) -> None:
    resp = clients.Folder.create(
        title="not_important",
        parent="/",
        folder_name=folder_name,
        expect_ok=False,
    )
    resp.assert_status_code(400)
    assert (
        resp.json["fields"]["name"][0]
        == f"{folder_name!r} does not match pattern '^[-\\\\w]*\\\\Z'."
    )


def test_openapi_folder_name_with_extended_characters(clients: ClientRegistry) -> None:
    extended_characters = "û亿Ï8Ĺ"
    encoded_extended_characters = urllib.parse.quote(extended_characters)

    res_create = clients.Folder.create(parent="/", title="test123", folder_name=extended_characters)
    created_folder = res_create.json

    res_get = clients.Folder.get(folder_name=f"~{encoded_extended_characters}")
    fetched_folder = res_get.json

    clients.Folder.delete(folder_name=f"~{encoded_extended_characters}").assert_status_code(204)

    clients.Folder.get(
        folder_name=f"~{encoded_extended_characters}", expect_ok=False
    ).assert_status_code(404)

    assert created_folder["id"] == fetched_folder["id"]
    assert created_folder["extensions"]["path"] == fetched_folder["extensions"]["path"]


def test_openapi_folder_with_extended_characters_parent(clients: ClientRegistry) -> None:
    extended_characters = "û亿Ï8Ĺ"

    clients.Folder.create(parent="/", title="First level", folder_name=extended_characters)

    res = clients.Folder.create(
        parent=f"/{extended_characters}", title="Second level", folder_name="second_level_folder"
    )

    assert res.json["id"] == f"~{extended_characters}~second_level_folder"
    assert res.json["extensions"]["path"] == f"/{extended_characters}/second_level_folder"


def test_move_root_folder(clients: ClientRegistry) -> None:
    resp = clients.Folder.move(folder_name="~", destination="/", expect_ok=False)
    resp.assert_status_code(400)
    assert resp.json["detail"] == "You can't move the root folder."


def test_openapi_delete_folder_with_hosts(clients: ClientRegistry) -> None:
    clients.Folder.create(
        parent="/",
        folder_name="new_folder",
        title="new_folder",
    )
    clients.HostConfig.create(host_name="host1", folder="~new_folder")
    no_force_delete_result = clients.Folder.delete(
        folder_name="~new_folder", mode="abort_on_nonempty", expect_ok=False
    )

    clients.Folder.delete(folder_name="~new_folder").assert_status_code(204)
    assert no_force_delete_result.status_code == 409


def test_openapi_delete_folder_with_subfolders(clients: ClientRegistry) -> None:
    clients.Folder.create(
        parent="/",
        folder_name="new_folder",
        title="new_folder",
    )
    clients.Folder.create(
        parent="~new_folder",
        folder_name="sub_folder",
        title="sub_folder",
    )
    no_force_delete_result = clients.Folder.delete(
        folder_name="~new_folder", mode="abort_on_nonempty", expect_ok=False
    )

    clients.Folder.delete(folder_name="~new_folder").assert_status_code(204)
    assert no_force_delete_result.status_code == 409


def test_openapi_delete_folder_with_rules(clients: ClientRegistry) -> None:
    clients.Folder.create(
        parent="/",
        folder_name="new_folder",
        title="new_folder",
    )

    clients.Rule.create(
        ruleset="active_checks:http",
        folder="~new_folder",
        conditions={},
        value_raw='{"name": "check_localhost", "host": {"address": ("direct", "localhost")}, "mode": ("url", {})}',
    )

    no_force_delete_result = clients.Folder.delete(
        folder_name="~new_folder", mode="abort_on_nonempty", expect_ok=False
    )

    clients.Folder.delete(folder_name="~new_folder").assert_status_code(204)
    assert no_force_delete_result.status_code == 409


def test_openapi_delete_folder_with_predefined_conditions(clients: ClientRegistry) -> None:
    clients.Folder.create(
        parent="/",
        folder_name="new_folder",
        title="new_folder",
    )

    clients.Folder.create(
        parent="/new_folder",
        folder_name="subfolder",
        title="subfolder",
    )

    PredefinedConditionStore().save(
        {
            "condition_1": {
                "title": "condition_1",
                "comment": "",
                "docu_url": "",
                "conditions": {"host_folder": "new_folder"},
                "owned_by": None,
                "shared_with": [],
            },
            "condition_2": {
                "title": "condition_2",
                "comment": "",
                "docu_url": "",
                "conditions": {"host_folder": "new_folder/subfolder"},
                "owned_by": None,
                "shared_with": [],
            },
        },
        pprint_value=False,
    )

    no_force_delete_subfolder_result = clients.Folder.delete(
        folder_name="~new_folder~subfolder",
        mode="abort_on_nonempty",
        expect_ok=False,
    )
    no_force_delete_folder_result = clients.Folder.delete(
        folder_name="~new_folder", mode="abort_on_nonempty", expect_ok=False
    )

    clients.Folder.delete(folder_name="~new_folder~subfolder").assert_status_code(204)
    clients.Folder.delete(folder_name="~new_folder").assert_status_code(204)

    assert no_force_delete_subfolder_result.status_code == 409
    assert no_force_delete_folder_result.status_code == 409


def test_openapi_delete_folder_default_mode_recursive(clients: ClientRegistry) -> None:
    clients.Folder.create(
        parent="/",
        folder_name="new_folder",
        title="new_folder",
    )
    clients.HostConfig.create(host_name="host1", folder="~new_folder")
    no_force_delete_result = clients.Folder.delete(folder_name="~new_folder")

    clients.Folder.get(folder_name="~new_folder", expect_ok=False).assert_status_code(404)
    assert no_force_delete_result.status_code == 204


@pytest.mark.skipif(
    version.edition(paths.omd_root)
    not in {
        version.Edition.ULTIMATEMT,
        version.Edition.ULTIMATE,
        version.Edition.CLOUD,
    },
    reason="Tested attribute is available in ULTIMATEMT, ULTIMATE, and CLOUD editions.",
)
@pytest.mark.parametrize(
    "field_value, status_code",
    [
        ("push-agent", 200),
        ("pull-agent", 200),
        ("invalid-value", 400),
    ],
)
def test_cmk_agent_connection_attribute_regression(
    clients: ClientRegistry,
    field_value: str,
    status_code: int,
) -> None:
    clients.Folder.create(
        folder_name="push-agent-folder",
        title="push-agent-folder",
        parent="~",
        attributes={"cmk_agent_connection": field_value},
        expect_ok=status_code == 200,
    ).assert_status_code(status_code)
