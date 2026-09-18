#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Sequence
from typing import override

from cmk.crypto import certificate
from cmk.gui.logged_in import user
from cmk.rulesets.v1 import Message
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ..visitors.multiline_text import MultilineTextVisitor
from ._type_defs import InvalidValue


def _validate_pem(value: str) -> None:
    try:
        certificate.Certificate.load_pem(certificate.CertificatePEM(value))
    except Exception as e:
        raise ValidationError(Message("Invalid certificate: %(e)s") % {"e": str(e)})


class CACertificateVisitor(MultilineTextVisitor):
    @override
    def _to_vue(
        self, parsed_value: str | InvalidValue[str]
    ) -> tuple[shared_type_defs.FormSpec, object]:
        multiline_text, value = super()._to_vue(parsed_value)
        assert isinstance(multiline_text, shared_type_defs.MultilineText)
        return (
            shared_type_defs.CaCertificate(
                title=multiline_text.title,
                help=multiline_text.help,
                validators=multiline_text.validators,
                label=multiline_text.label,
                input_hint=multiline_text.input_hint,
                # Fetching a certificate is a server side request to a host chosen by the user.
                allow_fetch=user.may("general.server_side_requests"),
            ),
            value,
        )

    @override
    def _validators(self) -> Sequence[Callable[[str], object]]:
        return [_validate_pem, *super()._validators()]
