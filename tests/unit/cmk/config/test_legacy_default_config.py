#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Transitional: goes away together with cmk.base.config.get_default_config.

from cmk.base.config import get_default_config
from cmk.config import get_legacy_default_base_config


def test_legacy_default_config_only_drops_types() -> None:
    assert set(get_default_config()) - set(get_legacy_default_base_config()) == {
        "Any",
        "CMCAuthorization",
        "CMCConfigMultiprocessing",
        "CMCConfigMultiprocessingMandatory",
        "CMCGraphiteConnection",
        "CMCInitialScheduling",
        "Contact",
        "ContactName",
        "Container",
        "EventRule",
        "ExitSpec",
        "Final",
        "FolderAttributesForBase",
        "HostAddress",
        "HostName",
        "HTTPProxySpec",
        "IPMICredentials",
        "Iterable",
        "LabelPickerRuleValue",
        "Labels",
        "Literal",
        "LogCmkHelpers",
        "Mapping",
        "NotificationParameterSpecs",
        "NotificationPluginNameStr",
        "NotifyPluginParamsDict",
        "OAuth2Connection",
        "PasswordConfig",
        "RawIntervalFromConfig",
        "RealTimeChecks",
        "RediscoveryParameters",
        "RuleSpec",
        "Sequence",
        "ServiceName",
        "SmartPingTuning",
        "SmartPingTuningBase",
        "SNMPCredentials",
        "SNMPTiming",
        "SSCConfigSet",
        "SupportsInt",
        "TagConfigSpec",
        "TypedDict",
    }


def test_legacy_default_config_keeps_values() -> None:
    default_config = get_default_config()
    assert get_legacy_default_base_config() == {
        key: default_config[key] for key in get_legacy_default_base_config()
    }
