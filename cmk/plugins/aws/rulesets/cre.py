#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1.form_specs import DictElement


def edition_specific_global_services() -> dict[str, DictElement]:
    return {}


def edition_specific_regional_services() -> dict[str, DictElement]:
    return {}


def migrate_edition_specific_global_services_vs_to_fs(values: dict) -> None:
    pass


def migrate_edition_specific_regional_services_vs_to_fs(values: dict) -> None:
    pass


def handle_edition_switch(values: dict) -> None:
    values["global_services"].pop("route53", None)
    values["global_services"].pop("cloudfront", None)
    values["services"].pop("sns", None)
    values["services"].pop("lambda", None)
    values["services"].pop("aws_lambda", None)
    values["services"].pop("ecs", None)
    values["services"].pop("elasticache", None)
