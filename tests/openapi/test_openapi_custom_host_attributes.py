#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.rest_api_client import ClientRegistry


def test_create_and_get(clients: ClientRegistry) -> None:
    clients.CustomHostAttr.create(name="coordinates", title="Coordinates").assert_status_code(201)

    resp = clients.CustomHostAttr.get("coordinates")
    assert resp.json["id"] == "coordinates"
    assert resp.json["title"] == "Coordinates"


def test_create_with_all_fields(clients: ClientRegistry) -> None:
    resp = clients.CustomHostAttr.create(
        name="location",
        title="Location",
        topic="My Topic",
        help_text="Where the host lives.",
        show_in_table=True,
        add_custom_macro=True,
    )
    resp.assert_status_code(201)
    ext = resp.json["extensions"]
    assert ext["topic"] == "My Topic"
    assert ext["help"] == "Where the host lives."
    assert ext["show_in_table"] is True
    assert ext["add_custom_macro"] is True


def test_create_defaults(clients: ClientRegistry) -> None:
    resp = clients.CustomHostAttr.create(name="minimal", title="Minimal")
    resp.assert_status_code(201)
    ext = resp.json["extensions"]
    assert ext["topic"] == "Custom attributes"
    assert ext["help"] == ""
    assert ext["show_in_table"] is False
    assert ext["add_custom_macro"] is False


def test_list(clients: ClientRegistry) -> None:
    clients.CustomHostAttr.create(name="attr_a", title="Attr A")
    clients.CustomHostAttr.create(name="attr_b", title="Attr B")

    resp = clients.CustomHostAttr.get_all()
    resp.assert_status_code(200)
    names = [v["id"] for v in resp.json["value"]]
    assert "attr_a" in names
    assert "attr_b" in names


def test_list_empty(clients: ClientRegistry) -> None:
    resp = clients.CustomHostAttr.get_all()
    resp.assert_status_code(200)
    assert resp.json["value"] == []


def test_update(clients: ClientRegistry) -> None:
    clients.CustomHostAttr.create(name="myattr", title="Old Title")
    clients.CustomHostAttr.edit(name="myattr", title="New Title").assert_status_code(200)

    resp = clients.CustomHostAttr.get("myattr")
    assert resp.json["title"] == "New Title"


def test_update_partial(clients: ClientRegistry) -> None:
    clients.CustomHostAttr.create(
        name="myattr", title="Title", topic="Original Topic", show_in_table=False
    )
    clients.CustomHostAttr.edit(name="myattr", show_in_table=True)

    resp = clients.CustomHostAttr.get("myattr")
    assert resp.json["extensions"]["show_in_table"] is True
    assert resp.json["extensions"]["topic"] == "Original Topic"


def test_delete(clients: ClientRegistry) -> None:
    clients.CustomHostAttr.create(name="myattr", title="To Delete")
    clients.CustomHostAttr.delete("myattr").assert_status_code(204)

    clients.CustomHostAttr.get("myattr", expect_ok=False).assert_status_code(404)


def test_delete_removes_from_list(clients: ClientRegistry) -> None:
    clients.CustomHostAttr.create(name="attr_a", title="A")
    clients.CustomHostAttr.create(name="attr_b", title="B")
    clients.CustomHostAttr.delete("attr_a")

    resp = clients.CustomHostAttr.get_all()
    names = [v["id"] for v in resp.json["value"]]
    assert "attr_a" not in names
    assert "attr_b" in names


def test_get_nonexistent_returns_404(clients: ClientRegistry) -> None:
    clients.CustomHostAttr.get("does_not_exist", expect_ok=False).assert_status_code(404)


def test_delete_nonexistent_returns_404(clients: ClientRegistry) -> None:
    clients.CustomHostAttr.delete("does_not_exist", expect_ok=False).assert_status_code(404)


def test_delete_etag(clients: ClientRegistry) -> None:
    clients.CustomHostAttr.create(name="myattr", title="To Delete")
    clients.CustomHostAttr.delete(
        "myattr", expect_ok=False, etag="invalid_etag"
    ).assert_status_code(412)
    clients.CustomHostAttr.delete("myattr", etag="valid_etag").assert_status_code(204)


def test_edit_etag(clients: ClientRegistry) -> None:
    clients.CustomHostAttr.create(name="myattr", title="Original Title")
    clients.CustomHostAttr.edit(
        name="myattr", title="New Title", expect_ok=False, etag="invalid_etag"
    ).assert_status_code(412)
    clients.CustomHostAttr.edit(
        name="myattr", title="New Title", etag="valid_etag"
    ).assert_status_code(200)


def test_update_nonexistent_returns_404(clients: ClientRegistry) -> None:
    clients.CustomHostAttr.edit("does_not_exist", title="X", expect_ok=False).assert_status_code(
        404
    )


def test_create_duplicate_name_fails(clients: ClientRegistry) -> None:
    clients.CustomHostAttr.create(name="myattr", title="First")
    resp = clients.CustomHostAttr.create(
        name="myattr", title="Second", expect_ok=False
    ).assert_status_code(400)
    assert "already in use" in resp.json["fields"]["body.name"]["msg"]


@pytest.mark.parametrize(
    "invalid_name",
    [
        "invalid name",
        "invalid!name",
        "invalid$name",
        "",
    ],
)
def test_create_invalid_name_fails(clients: ClientRegistry, invalid_name: str) -> None:
    clients.CustomHostAttr.create(name=invalid_name, title="X", expect_ok=False).assert_status_code(
        400
    )
