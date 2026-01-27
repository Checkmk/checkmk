#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import asdict
from typing import override

from cmk.gui.form_specs import get_visitor
from cmk.gui.form_specs.unstable.oauth2_connection_setup import OAuth2ConnectionSetup
from cmk.gui.form_specs.visitors._base import FormSpecVisitor
from cmk.gui.form_specs.visitors._type_defs import (
    IncomingData,
    InvalidValue,
)
from cmk.gui.form_specs.visitors._utils import get_title_and_help
from cmk.gui.form_specs.visitors.validators import build_vue_validators
from cmk.gui.oauth2_connections.wato._modes import (
    get_authority_mapping,
    get_oauth2_connection_config,
    get_oauth2_connection_form_spec,
)
from cmk.shared_typing import vue_formspec_components as shared_type_defs
from cmk.shared_typing.vue_formspec_components import ConnectorType, Oauth2ConnectionConfig

_ParsedValueModel = Mapping[str, IncomingData]
_FallbackDataModel = _ParsedValueModel


class OAuth2ConnectionSetupVisitor(
    FormSpecVisitor[OAuth2ConnectionSetup, _ParsedValueModel, _FallbackDataModel]
):
    @override
    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParsedValueModel | InvalidValue[_FallbackDataModel]:
        return get_visitor(get_oauth2_connection_form_spec(), self.visitor_options)._parse_value(
            raw_value
        )

    @override
    def _validate(
        self, parsed_value: _ParsedValueModel
    ) -> list[shared_type_defs.ValidationMessage]:
        visitor = get_visitor(get_oauth2_connection_form_spec(), self.visitor_options)
        return visitor._validate(parsed_value)

    @override
    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackDataModel]
    ) -> tuple[shared_type_defs.FormSpec, object]:
        if isinstance(parsed_value, InvalidValue):
            raise TypeError("Received unexpected InvalidValue: %r" % parsed_value)
        title, help_text = get_title_and_help(self.form_spec)
        visitor = get_visitor(get_oauth2_connection_form_spec(), self.visitor_options)
        vue_form_spec, vue_value = visitor._to_vue(parsed_value)
        return (
            shared_type_defs.Oauth2ConnectionSetup(
                title=title,
                help=help_text,
                validators=build_vue_validators(visitor._validators()),
                config=Oauth2ConnectionConfig(**asdict(get_oauth2_connection_config())),
                form_spec=vue_form_spec,
                authority_mapping=[
                    shared_type_defs.Authority(
                        authority_id=ident,
                        authority_name=name,
                    )
                    for ident, name in get_authority_mapping().items()
                ],
                connector_type=ConnectorType(self.form_spec.connector_type),
            ),
            vue_value,
        )

    @override
    def _to_disk(self, parsed_value: _ParsedValueModel) -> object:
        ident = str(parsed_value["ident"]) if "ident" in parsed_value else None
        return get_visitor(get_oauth2_connection_form_spec(ident), self.visitor_options)._to_disk(
            parsed_value
        )
