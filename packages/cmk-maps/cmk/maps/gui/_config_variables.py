#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ``connections_list_spec`` returns a ``List[Any]``: a list's element type is known
# only to the element spec it wraps, so the builder below has to name it too.
# mypy: disable-error-code="explicit-any"
"""Maps admin settings as native Checkmk global settings.

The settings appear under *Setup → Global settings* in two "Maps" groups and are
*also* reachable module-near (Customize → Maps → the "Maps" page menu) through
two curated modes (see :mod:`cmk.maps.gui._settings_modes`) — same variables,
same form specs, one ``global.mk`` per domain, two entry points (the DCD
pattern).

All Maps settings live in the feature's own :class:`ConfigDomainMaps` (like every
standalone Checkmk daemon package). Two display groups split them along the "read
by the daemon?" seam — the daemon consumes only the second group:

- "Maps: map & object defaults" (GUI-only, never read by the daemon):
  ``maps_map_defaults`` / ``maps_object_defaults`` — cohesive ``Dictionary``
  form specs consumed as a whole to seed a new map/object.
- "Maps: connections & daemon" (read + replicated to the daemon):
  ``maps_connections`` plus the two runtime knobs ``maps_log_level`` /
  ``maps_state_refresh_interval`` (individual scalars so each is independently
  searchable, resettable and site-overridable — the idiomatic Checkmk shape).

The form-spec builders are context-free so the curated ``_settings_modes`` can
reuse them verbatim; the ``ConfigVariable`` wrappers ignore the render-time
``GlobalSettingsContext`` (connection choices / core are resolved live inside the
builders themselves).
"""

from typing import Any

from cmk.gui.i18n import _l
from cmk.gui.watolib.config_domain_name import (
    ConfigVariable,
    ConfigVariableGroup,
    ConfigVariableGroupRegistry,
    ConfigVariableRegistry,
)
from cmk.maps.gui._config_domain import (
    CONFIG_VAR_CONNECTIONS,
    CONFIG_VAR_LOG_LEVEL,
    CONFIG_VAR_MAP_DEFAULTS,
    CONFIG_VAR_OBJECT_DEFAULTS,
    CONFIG_VAR_STATE_REFRESH_INTERVAL,
    ConfigDomainMaps,
    CONNECTIONS_TITLE,
    DEFAULT_LOG_LEVEL,
    DEFAULT_STATE_REFRESH_INTERVAL,
    MAP_DEFAULTS_TITLE,
    OBJECT_DEFAULTS_TITLE,
)
from cmk.maps.gui._settings import connection_choices, monitoring_core
from cmk.maps.gui.form_specs.connections import connections_list_spec
from cmk.maps.gui.form_specs.global_settings import map_defaults_spec, object_defaults_spec
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    Dictionary,
    Integer,
    List,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.form_specs.validators import NumberInRange

# Two groups along the config-domain seam (prefixed titles so they cluster in the
# central list, like "Event Console: generic"). The curated module-near modes
# scope to exactly one of these each.
ConfigVariableGroupMapsAuthoring = ConfigVariableGroup(
    title=_l("Maps: map & object defaults"),
    sort_index=60,
)
ConfigVariableGroupMapsDaemon = ConfigVariableGroup(
    title=_l("Maps: connections & daemon"),
    sort_index=61,
)


def connections_form_spec() -> List[Any]:
    # The metric-history default tracks the local site's core; resolved at render
    # time (like the connection-choices for map defaults).
    return connections_list_spec(monitoring_core(), title=CONNECTIONS_TITLE)


def map_defaults_form_spec() -> Dictionary:
    # Connection choices are dynamic (live Maps connections) and must be resolved
    # at render time, not at registration.
    return map_defaults_spec(connection_choices(), title=MAP_DEFAULTS_TITLE)


def object_defaults_form_spec() -> Dictionary:
    return object_defaults_spec(title=OBJECT_DEFAULTS_TITLE)


def log_level_form_spec() -> SingleChoice:
    return SingleChoice(
        title=Title("Log level"),
        help_text=Help("Log verbosity of the Maps backend daemon."),
        elements=[
            SingleChoiceElement(name="DEBUG", title=Title("Debug")),
            SingleChoiceElement(name="INFO", title=Title("Info")),
            SingleChoiceElement(name="WARNING", title=Title("Warning")),
            SingleChoiceElement(name="ERROR", title=Title("Error")),
            SingleChoiceElement(name="CRITICAL", title=Title("Critical")),
        ],
        prefill=DefaultValue(DEFAULT_LOG_LEVEL),
    )


def state_refresh_interval_form_spec() -> Integer:
    return Integer(
        title=Title("State refresh interval"),
        help_text=Help(
            "How often the Maps backend re-polls connection state and pushes "
            "updates to open maps. Lower is more live but adds load on the "
            "monitoring backend."
        ),
        unit_symbol="seconds",
        custom_validate=[NumberInRange(min_value=1, max_value=300)],
        prefill=DefaultValue(DEFAULT_STATE_REFRESH_INTERVAL),
    )


ConfigVariableMapsConnections = ConfigVariable(
    group=ConfigVariableGroupMapsDaemon,
    primary_domain=ConfigDomainMaps,
    ident=CONFIG_VAR_CONNECTIONS,
    form_spec=lambda context: connections_form_spec(),  # noqa: ARG005
)

# Authoring defaults are GUI-only (the daemon never reads them), but — like every
# standalone Checkmk daemon package (dcd, liveproxyd, …) — Maps keeps ALL its
# settings in its own config domain rather than the shared GUI domain, so the
# feature stays self-contained. The daemon simply ignores these keys in maps.d.
ConfigVariableMapsMapDefaults = ConfigVariable(
    group=ConfigVariableGroupMapsAuthoring,
    primary_domain=ConfigDomainMaps,
    ident=CONFIG_VAR_MAP_DEFAULTS,
    form_spec=lambda context: map_defaults_form_spec(),  # noqa: ARG005
)

ConfigVariableMapsObjectDefaults = ConfigVariable(
    group=ConfigVariableGroupMapsAuthoring,
    primary_domain=ConfigDomainMaps,
    ident=CONFIG_VAR_OBJECT_DEFAULTS,
    form_spec=lambda context: object_defaults_form_spec(),  # noqa: ARG005
)

ConfigVariableMapsLogLevel = ConfigVariable(
    group=ConfigVariableGroupMapsDaemon,
    primary_domain=ConfigDomainMaps,
    ident=CONFIG_VAR_LOG_LEVEL,
    form_spec=lambda context: log_level_form_spec(),  # noqa: ARG005
)

ConfigVariableMapsStateRefreshInterval = ConfigVariable(
    group=ConfigVariableGroupMapsDaemon,
    primary_domain=ConfigDomainMaps,
    ident=CONFIG_VAR_STATE_REFRESH_INTERVAL,
    form_spec=lambda context: state_refresh_interval_form_spec(),  # noqa: ARG005
)


def register(
    config_variable_group_registry: ConfigVariableGroupRegistry,
    config_variable_registry: ConfigVariableRegistry,
) -> None:
    config_variable_group_registry.register(ConfigVariableGroupMapsAuthoring)
    config_variable_group_registry.register(ConfigVariableGroupMapsDaemon)
    config_variable_registry.register(ConfigVariableMapsConnections)
    config_variable_registry.register(ConfigVariableMapsMapDefaults)
    config_variable_registry.register(ConfigVariableMapsObjectDefaults)
    config_variable_registry.register(ConfigVariableMapsLogLevel)
    config_variable_registry.register(ConfigVariableMapsStateRefreshInterval)
