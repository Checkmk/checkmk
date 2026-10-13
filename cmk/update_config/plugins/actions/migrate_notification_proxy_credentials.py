#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Move the proxy credentials of notification plug-ins into the password store.

Until 3.0 the notification plug-ins configured an explicit proxy as URL, so credentials
like http://user:secret@proxy:3128 ended up in the configuration in plain text. The
plug-ins now use the structured proxy form. This action converts the proxy URLs into it
and moves their credentials into password store entries.

There is one entry per proxy credential, so a proxy used in many places can be changed in
one place. Entries are owned by the administrators. Credentials from personal notification
rules get entries of their own, which are not shared with anyone, so the update does not
widen who can use them.

The form spec of the plug-ins converts proxy URLs as well, but keeps the credentials as
explicit password. That is why this action runs before the rulesets action (30), which
applies the form spec migration to the notification parameter rulesets.

Proxy URLs that cannot be fully represented in the structured form (unsupported scheme,
invalid port, no host or a password without user) are converted as far as possible, with
port 0 so that the form rejects them until they are fixed. Their credentials are moved to
the password store as well, and the update reports them.
"""

import re
from collections.abc import Container, Iterable, Mapping, MutableMapping
from dataclasses import dataclass, field
from datetime import datetime
from logging import Logger
from typing import Final, override

from cmk.ccc.user import UserId
from cmk.gui import userdb
from cmk.gui.config import active_config, Config
from cmk.gui.default_name import unique_default_name_suggestion
from cmk.gui.userdb.store import load_users_uncached
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.gui.watolib.notification_parameter import notification_parameter_registry
from cmk.gui.watolib.notifications import NotificationParameterConfigFile
from cmk.gui.watolib.password_store import PasswordStore
from cmk.gui.watolib.rulesets import AllRulesets, RulesetCollection
from cmk.ruleset_matcher.definition import RuleGroup
from cmk.rulesets.internal.form_specs import (
    InternalProxy,
    parse_proxy_url_leniently,
)
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.http_proxy_config import ProxyAuthSpec
from cmk.utils.password_store import PasswordConfig

_PROXY_KEY: Final = "proxy_url"


def proxy_methods(logger: Logger) -> frozenset[str]:
    """The notification methods whose proxy setting uses the structured proxy form

    Plug-ins of extension packages may still use the plain proxy URL and are left alone.
    """
    methods = set()
    for method in notification_parameter_registry:
        try:
            elements = notification_parameter_registry.parameter_form_spec(method).elements
        except Exception:
            logger.warning(
                "Cannot check the proxy setting of the notification method %(method)s. "
                "Its proxy credentials are not moved to the password store.",
                {"method": method},
            )
            continue
        if _PROXY_KEY in elements and isinstance(
            elements[_PROXY_KEY].parameter_form, InternalProxy
        ):
            methods.add(method)
    return frozenset(methods)


def legacy_proxy_url(value: object) -> str | None:
    """Return the URL of an explicit proxy that is not yet structured"""
    match value:
        case ("url", str(url)) | ("cmk_postprocessed", "explicit_proxy", str(url)):
            return url
        case _:
            return None


def _password_id(base: str, taken: Iterable[str]) -> str:
    # The password store pages only accept ASCII idents
    candidate = re.sub(r"[^-\w]", "_", f"notification_proxy_{base}", flags=re.ASCII)
    return unique_default_name_suggestion(candidate, taken)


@dataclass(frozen=True)
class _CredentialKey:
    personal_rules_of: UserId | None
    proxy_server_name: str
    port: int
    user: str
    secret: str


@dataclass
class _Entry:
    password_id: str
    title: str
    secret: str
    locations: list[str] = field(default_factory=list)


class ProxyCredentialsMigration:
    """Converts proxy URLs and collects the password store entries for their credentials"""

    def __init__(self, existing_password_ids: Iterable[str], logger: Logger) -> None:
        self._taken_password_ids = set(existing_password_ids)
        self._logger = logger
        self._entries: dict[_CredentialKey, _Entry] = {}

    @property
    def new_passwords(self) -> dict[str, PasswordConfig]:
        return {
            entry.password_id: PasswordConfig(
                title=entry.title,
                comment="Created during the update from the proxy URLs of: %s."
                % ", ".join(entry.locations),
                docu_url="",
                password=entry.secret,
                owned_by=None,
                shared_with=[],
            )
            for entry in self._entries.values()
        }

    def _entry(self, key: _CredentialKey, location: str) -> _Entry:
        if (entry := self._entries.get(key)) is None:
            base = f"{key.user}_at_{key.proxy_server_name}_{key.port}"
            title = f"Proxy credentials of {key.user}@{key.proxy_server_name}:{key.port}"
            if key.personal_rules_of is not None:
                base = f"{key.personal_rules_of}_{base}"
                title += f" for the personal notification rules of {key.personal_rules_of}"
            entry = _Entry(
                password_id=_password_id(base, self._taken_password_ids),
                title=title,
                secret=key.secret,
            )
            self._taken_password_ids.add(entry.password_id)
            self._entries[key] = entry
        entry.locations.append(location)
        return entry

    def migrate_parameters(
        self,
        parameters: MutableMapping[str, object],
        *,
        location: str,
        personal_rules_of: UserId | None = None,
    ) -> bool:
        """Migrate the proxy of the given plug-in parameters in place

        Returns whether the parameters were changed. The location describes where the
        parameters are configured and is logged; values are never logged.
        """
        if (url := legacy_proxy_url(parameters.get(_PROXY_KEY))) is None:
            return False

        # The same conversion as the form spec, so both agree on the result. A URL that
        # cannot be represented gets port 0, which the form rejects, so it gets noticed.
        (proxy_config, credentials), is_complete = parse_proxy_url_leniently(url)
        if not is_complete:
            self._logger.warning(
                "The proxy URL of %(location)s cannot be fully converted into the structured "
                "proxy form. Please fix the proxy setting in the Setup.",
                {"location": location},
            )

        if credentials is not None:
            user, secret = credentials
            entry = self._entry(
                _CredentialKey(
                    personal_rules_of=personal_rules_of,
                    proxy_server_name=proxy_config["proxy_server_name"],
                    port=proxy_config["port"],
                    user=user,
                    secret=secret,
                ),
                location,
            )
            proxy_config["auth"] = ProxyAuthSpec(
                user=user,
                password=("cmk_postprocessed", "stored_password", (entry.password_id, "")),
            )
            self._logger.info(
                "Moved the proxy credentials of %(location)s to the password store entry "
                "'%(password_id)s'.",
                {"location": location, "password_id": entry.password_id},
            )

        parameters[_PROXY_KEY] = ("cmk_postprocessed", "explicit_proxy", proxy_config)
        return True


def migrate_notification_parameters[ParameterID: str](
    parameters: Mapping[str, Mapping[ParameterID, Mapping[str, object]]],
    methods: Container[str],
    migration: ProxyCredentialsMigration,
) -> bool:
    changed = False
    for method, parameters_of_method in parameters.items():
        if method not in methods:
            continue
        for parameter_id, item in parameters_of_method.items():
            properties = item.get("parameter_properties")
            if not isinstance(properties, MutableMapping):
                continue
            changed |= migration.migrate_parameters(
                properties, location=f"notification parameter '{parameter_id}'"
            )
    return changed


def migrate_notification_parameter_rules(
    all_rulesets: RulesetCollection,
    methods: Iterable[str],
    migration: ProxyCredentialsMigration,
) -> bool:
    changed = False
    for method in sorted(methods):
        if not all_rulesets.exists(ruleset_name := RuleGroup.NotificationParameters(method)):
            continue
        for _folder, _index, rule in all_rulesets.get(ruleset_name).get_rules():
            if not isinstance(rule.value, MutableMapping):
                continue
            changed |= migration.migrate_parameters(
                rule.value, location=f"rule '{rule.id}' of ruleset '{ruleset_name}'"
            )
    return changed


def migrate_user_notification_rules(
    users: Mapping[UserId, Mapping[str, object]],
    methods: Container[str],
    migration: ProxyCredentialsMigration,
) -> list[UserId]:
    """Personal notification rules keep the plug-in parameters inline"""
    changed_users = []
    for user_id, user_spec in users.items():
        rules = user_spec.get("notification_rules")
        if not isinstance(rules, list):
            continue
        changed = False
        for rule in rules:
            match rule:
                case {"notify_plugin": (str(method), MutableMapping() as parameters)} if (
                    method in methods
                ):
                    changed |= migration.migrate_parameters(
                        parameters,
                        location=f"notification rule '{rule.get('rule_id', '')}' of user "
                        f"'{user_id}'",
                        personal_rules_of=user_id,
                    )
        if changed:
            changed_users.append(user_id)
    return changed_users


def save_new_passwords(new_passwords: Mapping[str, PasswordConfig], pprint_value: bool) -> None:
    """Add the entries to the password store

    The automation that updates the merged password file cannot run during the update.
    The core config update at the end of the update ("cmk -U") writes that file.
    """
    store = PasswordStore()
    store.save(
        {**store.load_for_modification(), **new_passwords},
        pprint_value,
        update_merged_file=False,
    )


def migrate_proxy_credentials(
    logger: Logger,
    ui_config: Config,
    users: Mapping[UserId, Mapping[str, object]],
) -> list[UserId]:
    """Migrate all proxy URLs and save the changed configuration

    The users are migrated in place, and the IDs of the changed users are returned, since
    saving users is up to the caller.
    """
    methods = proxy_methods(logger)
    migration = ProxyCredentialsMigration(PasswordStore().load_for_reading().keys(), logger)

    parameter_file = NotificationParameterConfigFile()
    parameters = parameter_file.load_for_modification()
    parameters_changed = migrate_notification_parameters(parameters, methods, migration)

    all_rulesets = AllRulesets.load_all_rulesets(make_folder_tree(ui_config))
    rules_changed = migrate_notification_parameter_rules(all_rulesets, methods, migration)

    changed_users = migrate_user_notification_rules(users, methods, migration)

    # Save the passwords first: a configuration referring to a missing entry would break
    # the notifications, an unused entry does no harm.
    if new_passwords := migration.new_passwords:
        save_new_passwords(new_passwords, ui_config.wato_pprint_config)
    if parameters_changed:
        parameter_file.save(parameters, pprint_value=ui_config.wato_pprint_config)
    if rules_changed:
        all_rulesets.save(pprint_value=ui_config.wato_pprint_config, debug=ui_config.debug)
    return changed_users


class MigrateNotificationProxyCredentials(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        # Uncached: the users are modified in place and must not leak into other actions
        users = load_users_uncached(lock=True)
        try:
            changed_users = migrate_proxy_credentials(logger, active_config, users)
        except Exception:
            userdb.release_users_lock()
            raise

        if not changed_users:
            userdb.release_users_lock()
            return
        userdb.save_users(
            users,
            userdb.get_user_attributes(active_config.wato_user_attrs),
            active_config.user_connections,
            now=datetime.now(),
            pprint_value=active_config.wato_pprint_config,
            call_users_saved_hook=False,
            changed_users=changed_users,
        )


update_action_registry.register(
    MigrateNotificationProxyCredentials(
        name="migrate_notification_proxy_credentials",
        title="Moving proxy credentials of notification plug-ins to the password store",
        sort_index=22,  # before the rulesets action (30) migrates the proxy URLs
        expiry_version=ExpiryVersion.CMK_310,
    )
)
