#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.form_specs import get_visitor, RawFrontendData, VisitorOptions
from cmk.gui.form_specs.unstable import LegacyValueSpec
from cmk.gui.valuespec import FileUpload, TextInput, UploadOrPasteTextFile


@pytest.mark.usefixtures("request_context")
def test_legacy_valuespec_ignores_file_inputs_sent_as_objects() -> None:
    # Crash groups 4397/4107/4224: the frontend sends file inputs as {} in input_context
    visitor = get_visitor(
        LegacyValueSpec.wrap(TextInput()),
        VisitorOptions(migrate_values=True, mask_values=False),
    )

    assert (
        visitor.to_disk(
            RawFrontendData(
                {"varprefix": "posted", "input_context": {"posted": "foo", "posted_upload": {}}}
            )
        )
        == "foo"
    )


_UPLOAD_NOT_SUPPORTED = (
    "File uploads are not supported in this form. "
    "Please paste the content instead, if the field offers it."
)


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    "valuespec, input_context, upload_key",
    [
        pytest.param(
            FileUpload(allow_empty=False), {"posted": {}}, "posted", id="required-file-upload"
        ),
        pytest.param(
            FileUpload(allow_empty=True), {"posted": {}}, "posted", id="optional-file-upload"
        ),
        pytest.param(
            UploadOrPasteTextFile(allow_empty=True),
            {"posted_use": "0", "posted_0": {}},
            "posted_0",
            id="upload-or-paste-with-upload-selected",
        ),
    ],
)
def test_legacy_valuespec_reports_file_uploads_as_unsupported(
    valuespec: FileUpload | UploadOrPasteTextFile, input_context: dict[str, object], upload_key: str
) -> None:
    visitor = get_visitor(
        LegacyValueSpec.wrap(valuespec),
        VisitorOptions(migrate_values=True, mask_values=False),
    )

    messages = visitor.validate(
        RawFrontendData({"varprefix": "posted", "input_context": input_context})
    )

    assert [(m.location, m.message) for m in messages] == [([upload_key], _UPLOAD_NOT_SUPPORTED)]


@pytest.mark.usefixtures("request_context")
def test_legacy_valuespec_accepts_pasted_content_of_upload_or_paste_field() -> None:
    visitor = get_visitor(
        LegacyValueSpec.wrap(UploadOrPasteTextFile()),
        VisitorOptions(migrate_values=True, mask_values=False),
    )

    assert (
        visitor.to_disk(
            RawFrontendData(
                {
                    "varprefix": "posted",
                    "input_context": {"posted_use": "1", "posted_0": {}, "posted_1": "content\n"},
                }
            )
        )
        == "content\n"
    )
