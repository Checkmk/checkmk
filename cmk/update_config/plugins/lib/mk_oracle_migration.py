#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Final, Literal, NamedTuple

from cmk.gui.watolib.rulesets import Rule, RuleOptions, Ruleset
from cmk.plugins.oracle.bakery.mk_oracle_unified import (
    GuiAsmAuthConf,
    GuiAuthConf,
    GuiAuthUserPasswordData,
    GuiConfig,
    GuiConnectionConf,
    GuiDiscoveryConf,
    GuiInstanceConf,
    GuiMainConf,
    GuiOracleIdentificationConf,
    OracleAuthType,
)

MIGRATION_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "checkmk.com/oracle-migration")

RawSecret = tuple[
    Literal["cmk_postprocessed"],
    Literal["explicit_password", "stored_password"],
    tuple[str, str],
]


class MigratedRule(NamedTuple):
    rule: GuiConfig[RawSecret]
    warnings: list[str]


class MigrationResult(NamedTuple):
    legacy_rule: Rule
    new_rule: Rule
    warnings: list[str]


field_warning_messages: Final[dict[str, str]] = {
    "sqlnet_ora_group": "'sqlnet.ora permission group' has been skipped because it is not needed anymore by the unified plugin.",
    "validate_permissions": "'Oracle binaries permissions check' has been skipped because it is not needed by the unified plugin.",
    "xinetd_or_systemd": "'Host uses xinetd or systemd' has been skipped because it is not needed by the unified plugin.",
    "sqlnet_send_timeout": "'Sqlnet Send timeout' has been skipped because it is not supported by the unified plugin. Use Connection Timeout instead if this is applicable.",
    "excluded_sections": "'Exclude some sections on certain instances' cannot be mapped. The new rule format only supports disabling sections globally.",
    "remote_oracle_home": "'ORACLE_HOME to use for remote access' has been skipped because it is not needed by the unified plugin.",
    "tnsalias_pre_postfix": "'Add pre or postfix to TNSALIASes' has been skipped because it is not supported by the unified plugin.",
}

valid_sections: Final[frozenset[str]] = frozenset(
    {
        "instance",
        "asm_instance",
        "asm_diskgroup",
        "dataguard_stats",
        "locks",
        "logswitches",
        "longactivesessions",
        "performance",
        "processes",
        "recovery_area",
        "recovery_status",
        "sessions",
        "systemparameter",
        "undostat",
        "iostats",
        "jobs",
        "resumable",
        "rman",
        "tablespaces",
    }
)


def convert(legacy: Mapping[str, Any]) -> MigratedRule:
    warnings: list[str] = []
    instances: list[GuiInstanceConf[RawSecret]] = []

    deploy: tuple[Literal["deploy", "do_not_deploy"], None] = (
        ("deploy", None) if legacy.get("activated") else ("do_not_deploy", None)
    )

    cache_age = legacy.get("async_interval") or None

    sections = _convert_sections(legacy["sections"], warnings) if legacy.get("sections") else None

    discovery = _convert_discovery(legacy.get("sids"))

    auth, connection, login_instances = _convert_login(legacy, warnings)
    instances.extend(login_instances)

    login_exceptions = dict(legacy.get("login_exceptions", []))
    instances.extend(
        _convert_remote_instances(legacy.get("remote_instances", []), login_exceptions, warnings)
    )

    if asm_auth := _convert_login_asm(legacy.get("login_asm"), login_exceptions, warnings):
        if auth is None:
            auth = GuiAuthConf[RawSecret]()
        auth.asm_auth = asm_auth

    instances.extend(_convert_login_exceptions(login_exceptions, warnings))

    if auth is None and instances and instances[0].auth is not None:
        auth = instances[0].auth.model_copy()

    if auth is None or auth.auth_type is None:
        auth = (auth or GuiAuthConf[RawSecret]()).model_copy(
            update={"auth_type": (OracleAuthType.WALLET.value, None)}
        )
        warnings.append("No auth defined in legacy rule. Defaulting to Oracle wallet.")

    main = GuiMainConf[RawSecret](
        auth=auth,
        connection=connection or GuiConnectionConf(),
        cache_age=cache_age,
        discovery=discovery,
        sections=sections,
    )

    warnings.extend(msg for key, msg in field_warning_messages.items() if key in legacy)

    return MigratedRule(
        rule=GuiConfig[RawSecret](deploy=deploy, instances=instances, main=main),
        warnings=warnings,
    )


def _convert_sections(
    sections: Mapping[str, Any], warnings: list[str]
) -> dict[str, Literal["synchronous", "asynchronous", "disabled"]]:
    """Rename ASM section keys, map sync/async settings, and warn on unsupported sections."""
    literal_mapping: dict[str, Literal["synchronous", "asynchronous"]] = {
        "sync": "synchronous",
        "async": "asynchronous",
    }
    sections_to_rename = {
        "asm:instance": "asm_instance",
        "asm:asm_diskgroup": "asm_diskgroup",
        "asm:processes": "processes",
    }

    new_sections: dict[str, Literal["synchronous", "asynchronous", "disabled"]] = {}
    for section, setting in sections.items():
        section = sections_to_rename.get(section, section)

        if section not in valid_sections:
            if section == "ts_quotas":
                message = (
                    "'TS quotas (not used)' has no corresponding check in either the legacy or "
                    "unified plugin, so no monitoring data would result from enabling "
                    "it — omitted."
                )
            else:
                message = f"Could not map section '{section}'."
            warnings.append(message)
            continue
        # None for the old plugin means disabled
        # but any other wrong values can also mean that too
        new_sections[section] = literal_mapping.get(setting, "disabled")

    return new_sections


def _convert_discovery(sids: tuple[str, Sequence[str]] | None) -> GuiDiscoveryConf | None:
    """Map the legacy (mode, names) sids tuple to the unified discovery include/exclude dict."""
    if not sids:
        return None

    how, names = sids
    if how == "only":
        return GuiDiscoveryConf(enabled=True, include=list(names))
    if how in ("skip", "exclude"):
        return GuiDiscoveryConf(enabled=True, exclude=list(names))
    return None


def _convert_login(
    legacy: Mapping[str, Any], warnings: list[str]
) -> tuple[
    GuiAuthConf[RawSecret] | None, GuiConnectionConf | None, list[GuiInstanceConf[RawSecret]]
]:
    """Convert the legacy 'login' block into the unified main auth/connection,
    plus an extra instance if a tnsalias is configured."""
    login = legacy.get("login")
    if not isinstance(login, Mapping):
        return None, None, []

    auth = _convert_auth(login, auth_required=True, warnings=warnings)
    assert auth is not None  # auth_required=True always yields a real GuiAuthConf
    connection = _convert_connection(login) or GuiConnectionConf()
    if admin := legacy.get("tns_admin"):
        connection.tns_admin = admin

    instances = []
    if tns_alias := login.get("tnsalias"):
        instances.append(
            GuiInstanceConf[RawSecret](
                auth=auth.model_copy(),
                connection=connection.model_copy(),
                oracle_id=("alias", GuiOracleIdentificationConf(alias=tns_alias)),
            )
        )

    return auth, connection, instances


def _convert_remote_instances(
    remote_instances: Sequence[Mapping[str, Any]],
    login_exceptions: dict[str, Any],
    warnings: list[str],
) -> list[GuiInstanceConf[RawSecret]]:
    """Build instances for remote_instances entries, consuming matching
    login_exceptions entries (looked up by sid/piggyhost/explicit id) for their auth."""
    instances = []
    for remote in remote_instances:
        if "sid" not in remote:
            continue

        if tns_alias := remote.get("tnsalias"):
            oracle_id: tuple[Literal["alias", "descriptor", "sid"], GuiOracleIdentificationConf] = (
                "alias",
                GuiOracleIdentificationConf(alias=tns_alias),
            )
        else:
            oracle_id = ("sid", GuiOracleIdentificationConf(sid=remote["sid"]))

        # The remote instance is valid at this point,
        # because the login is optional
        new_instance = GuiInstanceConf[RawSecret](
            connection=_convert_connection(remote),
            oracle_id=oracle_id,
            piggyback_host=remote.get("piggyhost") or None,
        )
        instances.append(new_instance)

        look_up_type = remote.get("id")
        if (
            isinstance(look_up_type, str)
            and look_up_type in remote
            and isinstance(remote[look_up_type], str)
        ):
            look_up_key = remote[look_up_type]
        elif isinstance(look_up_type, tuple):
            look_up_key = look_up_type[-1]
        else:
            continue

        login_exception = login_exceptions.get(look_up_key)
        if isinstance(login_exception, Mapping):
            if auth := _convert_auth(login_exception, auth_required=False, warnings=warnings):
                new_instance.auth = auth
            del login_exceptions[look_up_key]
        else:
            warnings.append(f"Could not find login for {remote['sid']} remote instance.")

    return instances


def _convert_login_exceptions(
    login_exceptions: Mapping[str, Any], warnings: list[str]
) -> list[GuiInstanceConf[RawSecret]]:
    """Build instances for login_exceptions entries not consumed by remote_instances
    (i.e. plain SID-keyed logins, and any ASM login routed here via '+ASM')."""
    instances = []
    for sid, login in login_exceptions.items():
        if not isinstance(login, Mapping):
            continue

        if tns_alias := login.get("tnsalias"):
            oracle_id: tuple[Literal["alias", "descriptor", "sid"], GuiOracleIdentificationConf] = (
                "alias",
                GuiOracleIdentificationConf(alias=tns_alias),
            )
        else:
            oracle_id = ("sid", GuiOracleIdentificationConf(sid=sid))

        instances.append(
            GuiInstanceConf[RawSecret](
                auth=_convert_auth(login, auth_required=False, warnings=warnings),
                connection=_convert_connection(login),
                oracle_id=oracle_id,
            )
        )

    return instances


def _convert_login_asm(
    login_asm: Mapping[str, Any] | None,
    login_exceptions: dict[str, Any],
    warnings: list[str],
) -> GuiAsmAuthConf[RawSecret] | None:
    """Route an ASM login either into login_exceptions as a '+ASM' fallback instance
    (dedicated host, or wallet auth), or return an asm_auth object for the main section
    (explicit auth without a dedicated host)."""
    if not isinstance(login_asm, Mapping):
        return None

    asm_auth = login_asm.get("auth")
    if "host" in login_asm or "port" in login_asm or asm_auth == "wallet":
        login_exceptions["+ASM"] = login_asm
        warnings.append(
            "ASM login with dedicated host has been mapped to an instance in the new rule. "
            "This requires a SID, thus +ASM has been specified. Please update the new rule "
            "to the correct SID as needed."
        )
        return None

    if isinstance(asm_auth, tuple) and asm_auth[0] == "explicit":
        username, password = _convert_username_password(asm_auth)
        return GuiAsmAuthConf[RawSecret](
            username=username, password=password, role=login_asm.get("as") or None
        )

    return None


def _convert_username_password(auth: tuple[Any, ...]) -> tuple[str, RawSecret]:
    username, password = auth[1]
    password_type, password_value = password
    final_type: Literal["explicit_password", "stored_password"] = (
        "explicit_password" if password_type == "password" else "stored_password"
    )
    final_value: tuple[str, str] = (
        ("", password_value) if final_type == "explicit_password" else (password_value, "")
    )
    return username, ("cmk_postprocessed", final_type, final_value)


def _convert_auth(
    login: Mapping[str, Any], auth_required: bool, warnings: list[str]
) -> GuiAuthConf[RawSecret] | None:
    auth = login.get("auth")
    auth_type: tuple[OracleAuthType, GuiAuthUserPasswordData[RawSecret] | None] | None = None
    if isinstance(auth, tuple) and auth[0] == "explicit":
        username, password = _convert_username_password(auth)
        auth_type = (
            OracleAuthType.STANDARD,
            GuiAuthUserPasswordData[RawSecret](username=username, password=password),
        )
    elif auth == "wallet":
        auth_type = (OracleAuthType.WALLET, None)
    elif auth_required:
        warnings.append(
            "Unknown auth type, defaulting to wallet because auth-type is mandatory in the unified plugin."
        )
        auth_type = (OracleAuthType.WALLET, None)

    role = login.get("as") or None
    if auth_type is None and role is None:
        return None
    return GuiAuthConf[RawSecret](auth_type=auth_type, role=role)


def _convert_connection(login: Mapping[str, Any]) -> GuiConnectionConf | None:
    kwargs: dict[str, Any] = {}
    if host := login.get("host"):
        kwargs["host"] = host
    if port := login.get("port"):
        kwargs["port"] = port
    return GuiConnectionConf(**kwargs) if kwargs else None


def dump(config: GuiConfig[RawSecret]) -> dict[str, Any]:
    return config.model_dump(exclude_unset=True, exclude_none=True, mode="python")


def migrate_ruleset(
    legacy_ruleset: Ruleset, unified_ruleset: Ruleset, *, disabled: bool
) -> tuple[list[MigrationResult], int]:
    existing_ids = {rule.id for _, _, rule in unified_ruleset.get_rules()}

    results: list[MigrationResult] = []
    skipped = 0
    for folder, _index, rule in legacy_ruleset.get_rules():
        new_id = str(uuid.uuid5(MIGRATION_NAMESPACE, rule.id))
        if new_id in existing_ids:
            skipped += 1
            continue

        migrated = convert(rule.value)

        new_rule = Rule(
            id_=new_id,
            folder=folder,
            ruleset=unified_ruleset,
            conditions=rule.conditions.clone(),
            options=RuleOptions(
                disabled=disabled,
                description=f"(Migrated) {rule.description()}"
                if rule.description()
                else "(Migrated)",
                comment=rule.rule_options.comment,
                docu_url="",
                predefined_condition_id=rule.rule_options.predefined_condition_id,
            ),
            value=dump(migrated.rule),
        )
        results.append(
            MigrationResult(
                legacy_rule=rule,
                new_rule=new_rule,
                warnings=migrated.warnings,
            )
        )

    return results, skipped
