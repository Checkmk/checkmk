#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import io

import pytest
from werkzeug import datastructures as werkzeug_datastructures

from cmk.ccc.user import UserId

from cmk.gui.form_specs.vue.visitors import (
    DataOrigin,
    FileUploadVisitor,
    get_visitor,
    VisitorOptions,
)
from cmk.gui.form_specs.vue.visitors.file_upload import FileUploadModel
from cmk.gui.http import request
from cmk.gui.session import UserContext

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    FileUpload,
)


@pytest.fixture(scope="module", name="spec")
def file_upload_spec() -> FileUpload:
    return FileUpload(title=Title("some file"))


def test_file_upload_content_encryption(
    spec: FileUpload,
    with_user: tuple[UserId, str],
) -> None:
    with UserContext(with_user[0]):
        # Data from disk (unencrypted)
        visitor = get_visitor(spec, VisitorOptions(data_origin=DataOrigin.DISK))
        vue_value = visitor.to_vue(("my_file", "text/ascii", b"FOO"))[1]
        assert isinstance(vue_value, FileUploadModel)
        assert vue_value.file_type == "text/ascii"
        assert vue_value.file_content_encrypted is not None
        assert FileUploadVisitor.decrypt_content(vue_value.file_content_encrypted) == b"FOO"

        # Data edited in frontend (encrypted)
        visitor = get_visitor(spec, VisitorOptions(data_origin=DataOrigin.FRONTEND))
        value_from_frontend = {
            "input_uuid": "some_uuid",
            "file_name": "my_file",
            "file_type": "text/ascii",
            "file_content_encrypted": FileUploadVisitor.encrypt_content(b"FOO"),
        }
        vue_value = visitor.to_vue(value_from_frontend)[1]
        assert isinstance(vue_value, FileUploadModel)
        assert vue_value.file_type == "text/ascii"
        assert vue_value.file_content_encrypted is not None
        assert FileUploadVisitor.decrypt_content(vue_value.file_content_encrypted) == b"FOO"


def test_file_upload_invalid_data(
    spec: FileUpload,
    with_user: tuple[UserId, str],
) -> None:
    invalid_value = {"BROKEN": True}
    with UserContext(with_user[0]):
        visitor = get_visitor(spec, VisitorOptions(data_origin=DataOrigin.DISK))
        vue_value = visitor.to_vue(invalid_value)[1]
        assert isinstance(vue_value, FileUploadModel)
        assert vue_value.file_name is None
        assert len(visitor.validate(invalid_value)) == 1


def test_file_upload_new_file_from_frontend(
    spec: FileUpload,
    with_user: tuple[UserId, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with UserContext(with_user[0]), monkeypatch.context() as m:
        m.setattr(
            request,
            "files",
            werkzeug_datastructures.ImmutableMultiDict(
                {
                    "some_uuid": werkzeug_datastructures.FileStorage(
                        stream=io.BytesIO(b"some data"),
                        filename="some_filename",
                        content_type="text/plain",
                    )
                }
            ),
        )
        visitor = get_visitor(spec, VisitorOptions(data_origin=DataOrigin.FRONTEND))
        value_from_frontend = {"input_uuid": "some_uuid"}
        vue_value = visitor.to_vue(value_from_frontend)[1]
        assert isinstance(vue_value, FileUploadModel)
        assert vue_value.file_content_encrypted is not None
        assert FileUploadVisitor.decrypt_content(vue_value.file_content_encrypted) == b"some data"

        disk_value = visitor.to_disk(value_from_frontend)
        assert disk_value[0] == "some_filename"
        assert disk_value[1] == "text/plain"
        assert disk_value[2] == b"some data"
