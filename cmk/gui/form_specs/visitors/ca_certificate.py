#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Sequence
from typing import override

from cmk.crypto import certificate
from cmk.gui.form_specs.unstable.ca_certificate import CACertificateChoice
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.rulesets.v1 import Message
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.shared_typing import vue_formspec_components as shared_type_defs
from cmk.utils.encryption import load_certificate, raw_certificates

from ..visitors.multiline_text import MultilineTextVisitor
from ._base import FormSpecVisitor
from ._type_defs import DefaultValue, IncomingData, InvalidValue
from ._utils import compute_validators, get_title_and_help
from .list import ListVisitor
from .validators import build_vue_validators


def _validate_pem(value: str) -> None:
    try:
        certificate.Certificate.load_pem(certificate.CertificatePEM(value))
    except Exception as e:
        raise ValidationError(Message("Invalid certificate: %(e)s") % {"e": str(e)})


def _details(ca: certificate.Certificate) -> Sequence[shared_type_defs.ValueSummaryDetail]:
    return [
        shared_type_defs.ValueSummaryDetail(title=_("Subject"), text=ca.subject.rfc4514_string()),
        shared_type_defs.ValueSummaryDetail(title=_("Issuer"), text=ca.issuer.rfc4514_string()),
        shared_type_defs.ValueSummaryDetail(
            title=_("Validity"),
            text=_("%(not_before)s to %(not_after)s")
            % {
                "not_before": ca.not_valid_before.date().isoformat(),
                "not_after": ca.not_valid_after.date().isoformat(),
            },
        ),
        shared_type_defs.ValueSummaryDetail(title=_("Fingerprint"), text=ca.show_fingerprint()),
    ]


def _chain_details(
    pem: str,
) -> Sequence[Sequence[shared_type_defs.ValueSummaryDetail]]:
    chain = [load_certificate(raw) for raw in raw_certificates(pem)]
    readable = [ca for ca in chain if ca is not None]
    if not readable or len(readable) != len(chain):
        return [[shared_type_defs.ValueSummaryDetail(title=_("Certificate"), text=_("Unreadable"))]]
    return [_details(ca) for ca in readable]


def _summary(pem: str) -> shared_type_defs.ValueSummary:
    return shared_type_defs.ValueSummary(value=pem, label=None, detail_groups=_chain_details(pem))


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


class CACertificatesVisitor(ListVisitor[str]):
    @override
    def _element_summaries(
        self, element_values: Sequence[object]
    ) -> Sequence[shared_type_defs.ValueSummary] | None:
        pems = [value for value in element_values if isinstance(value, str)]
        if len(pems) != len(element_values):
            return None
        return [_summary(pem) for pem in pems]


class CACertificateChoiceVisitor(
    FormSpecVisitor[CACertificateChoice, Sequence[str], Sequence[str]]
):
    @override
    def _parse_value(self, raw_value: IncomingData) -> Sequence[str] | InvalidValue[Sequence[str]]:
        if isinstance(raw_value, DefaultValue):
            return []
        match raw_value.value:
            case list() as pems if all(isinstance(pem, str) for pem in pems):
                return pems
            case _:
                return InvalidValue(reason=_("Invalid certificate choice"), fallback_value=[])

    @override
    def _to_vue(
        self, parsed_value: Sequence[str] | InvalidValue[Sequence[str]]
    ) -> tuple[shared_type_defs.CaCertificateChoice, object]:
        title, help_text = get_title_and_help(self.form_spec)
        return (
            shared_type_defs.CaCertificateChoice(
                title=title,
                help=help_text,
                validators=build_vue_validators(compute_validators(self.form_spec)),
                elements=[_summary(pem) for pem in self.form_spec.certificates],
                chosen_label=_("Trusted"),
                not_chosen_label=_("Not trusted"),
            ),
            parsed_value.fallback_value if isinstance(parsed_value, InvalidValue) else parsed_value,
        )

    @override
    def _to_disk(self, parsed_value: Sequence[str]) -> Sequence[str]:
        return [pem for pem in self.form_spec.certificates if pem in parsed_value]
