#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from werkzeug.datastructures import FileStorage

from cmk.utils.render import filesize

from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.hooks import request_memoize
from cmk.gui.http import request
from cmk.gui.i18n import _, translate_to_current_language
from cmk.gui.utils.encrypter import Encrypter

from cmk.rulesets.v1 import Help, Message
from cmk.rulesets.v1.form_specs import FileUpload
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.shared_typing import vue_formspec_components as VueComponents

from ._base import FormSpecVisitor
from ._type_defs import DataOrigin, DefaultValue, InvalidValue
from ._utils import (
    compute_validators,
    get_title_and_help,
)

FileName = str
FileType = str
FileContent = bytes
FileContentEncrypted = str


@dataclass(frozen=True, kw_only=True)
class FileUploadModel:
    input_uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    file_name: FileName | None = None
    file_type: FileType | None = None
    file_content_encrypted: FileContentEncrypted | None = None


@request_memoize()
def read_content_of_uploaded_file(file_storage: FileStorage) -> FileContent:
    # We have to memoize the file content extraction, since the data can only be read once
    return file_storage.read()


class _FileSizeValidator:
    def __init__(self, max_size: int) -> None:
        self._max_size = max_size

    def __call__(self, value: tuple[str, str, bytes]) -> None:
        if not value[2]:
            return
        if len(value[2]) > self._max_size:
            raise ValidationError(
                Message("File size exceeds the maximum allowed size of %s bytes")
                % filesize(self._max_size)
            )


class _MimeTypeValidator:
    def __init__(
        self,
        mime_types: frozenset[str],
    ) -> None:
        self._mime_types = mime_types

    def __call__(self, value: tuple[str, str, bytes]) -> None:
        if value[1] in self._mime_types:
            return

        raise ValidationError(
            Message("Invalid mime type, supported types are: %s") % ", ".join(self._mime_types),
        )


class _FileExtensionValidator:
    def __init__(
        self,
        extension_types: frozenset[str],
    ) -> None:
        self._extension_types = extension_types

    def __call__(self, value: tuple[str, str, bytes]) -> None:
        file_name = value[0]
        if file_name is not None and any(file_name.endswith(ext) for ext in self._extension_types):
            return

        raise ValidationError(
            Message("Invalid extension type, supported types are: %s")
            % ", ".join(self._extension_types),
        )


class FileUploadVisitor(FormSpecVisitor[FileUpload, FileUploadModel, FileUploadModel]):
    def _parse_value(self, raw_value: object) -> FileUploadModel | InvalidValue[FileUploadModel]:
        if isinstance(raw_value, DefaultValue):
            return InvalidValue(reason=_("Using default value"), fallback_value=FileUploadModel())

        if self.options.data_origin == DataOrigin.DISK:
            if not isinstance(raw_value, tuple):
                return InvalidValue(
                    reason=_("Invalid data format"), fallback_value=FileUploadModel()
                )

            return FileUploadModel(
                file_name=raw_value[0],
                file_type=raw_value[1],
                file_content_encrypted=self.encrypt_content(raw_value[2]),
            )

        # Handle DataOrigin.FRONTEND
        if not isinstance(raw_value, dict):
            return InvalidValue(reason=_("Invalid data format"), fallback_value=FileUploadModel())

        input_uuid = raw_value["input_uuid"]
        uploaded_file = request.files.get(input_uuid)

        if uploaded_file is not None:
            file_content = read_content_of_uploaded_file(uploaded_file) if uploaded_file else None

            if file_content is not None:
                # New file
                return FileUploadModel(
                    input_uuid=input_uuid,
                    file_name=uploaded_file.filename,
                    file_type=uploaded_file.content_type,
                    file_content_encrypted=self.encrypt_content(file_content),
                )

        if raw_value.get("file_name") is None:
            return InvalidValue(
                reason=_("Invalid data. Missing filename"), fallback_value=FileUploadModel()
            )

        # Existing file, all data is already in raw_value
        return FileUploadModel(
            input_uuid=input_uuid,
            file_name=raw_value["file_name"],
            file_type=raw_value["file_type"],
            file_content_encrypted=raw_value["file_content_encrypted"],
        )

    @classmethod
    def encrypt_content(cls, content: bytes) -> str:
        return base64.b64encode(
            Encrypter.encrypt(base64.b64encode(content).decode("ascii"))
        ).decode("ascii")

    @classmethod
    def decrypt_content(cls, content: str) -> bytes:
        return base64.b64decode(Encrypter.decrypt(base64.b64decode(content)))

    def _to_vue(
        self, parsed_value: FileUploadModel | InvalidValue[FileUploadModel]
    ) -> tuple[VueComponents.FileUpload, FileUploadModel]:
        title, help_text = get_title_and_help(self.form_spec)
        help_text = (
            Help("Note: The maximum allowed file size is 10MB. ").localize(
                translate_to_current_language
            )
            + help_text
        )

        return (
            VueComponents.FileUpload(
                title=title,
                help=help_text,
                validators=build_vue_validators(self._validators()),
                i18n=VueComponents.FileUploadI18n(
                    replace_file=_("Replace file"),
                ),
            ),
            parsed_value.fallback_value if isinstance(parsed_value, InvalidValue) else parsed_value,
        )

    def _validators(self) -> Sequence[Callable[[tuple[str, str, bytes]], object]]:
        validators: list[Callable[[tuple[str, str, bytes]], object]] = []

        if self.form_spec.mime_types:
            validators.append(_MimeTypeValidator(frozenset(self.form_spec.mime_types)))
        if self.form_spec.extensions:
            validators.append(_FileExtensionValidator(frozenset(self.form_spec.extensions)))

        # Hardcoded file size limit of 10MB
        validators.append(_FileSizeValidator(10 * 1024 * 1024))

        return validators + compute_validators(self.form_spec)

    def _to_disk(self, parsed_value: FileUploadModel) -> tuple[str, str, bytes]:
        assert parsed_value.file_name is not None
        assert parsed_value.file_type is not None
        assert parsed_value.file_content_encrypted is not None
        return (
            parsed_value.file_name,
            parsed_value.file_type,
            self.decrypt_content(parsed_value.file_content_encrypted),
        )
