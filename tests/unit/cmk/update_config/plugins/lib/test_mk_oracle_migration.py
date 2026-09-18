#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.update_config.plugins.lib.mk_oracle_migration import convert, dump


def test_empty_body_says_nothing_about_deployment() -> None:
    # The legacy bakery refused a merged configuration that named no "Activation",
    # so a rule that names none must not answer for the rules below it.
    assert "deploy_rev2" not in dump(convert({}).rule)


def test_empty_body_says_nothing_about_authentication() -> None:
    assert "auth" not in dump(convert({}).rule)


def test_a_login_without_a_usable_auth_type_becomes_a_wallet() -> None:
    converted = convert({"login": {"host": "db1"}})
    auth_type = dump(converted.rule)["auth"]["auth_type"]
    assert auth_type == ("wallet", None)
    # StrEnum == str, so this catches what == "wallet" above can't: an unconverted enum
    # member, which pprints as invalid Python syntax.
    assert type(auth_type[0]) is str
    assert (
        "Unknown auth type, defaulting to wallet because auth-type is mandatory in the "
        "unified plugin." in converted.warnings
    )


def test_empty_body_has_no_instances() -> None:
    assert "instances_rev2" not in dump(convert({}).rule)


def test_deploy_when_activated_true() -> None:
    assert dump(convert({"activated": True}).rule)["deploy_rev2"] == "deploy"


def test_do_not_deploy_when_activated_false() -> None:
    assert dump(convert({"activated": False}).rule)["deploy_rev2"] == "do_not_deploy"


def test_async_interval_cache_age() -> None:
    assert dump(convert({"async_interval": 600}).rule)["cache_age"] == 600


def test_sections_supported_keys_are_mapped() -> None:
    new_rule = convert({"sections": {"instance": "sync"}})

    assert new_rule.warnings == []
    assert dump(new_rule.rule)["sections"] == {"instance": False}


def test_sections_absent_is_left_to_the_plug_in_with_a_warning() -> None:
    """The legacy bakery applied its own section list when the merged rules named none.

    Writing that list into every converted rule would make the rule answer for
    the rules below it, so the selection is left to the unified plug-in, whose
    own list holds the same sections.
    """
    new_rule = convert({"login": {"auth": "wallet"}})

    assert "sections" not in dump(new_rule.rule)
    assert len(new_rule.warnings) == 1
    assert "'Sections' was not configured" in new_rule.warnings[0]


def test_sections_unsupported_keys_are_skipped_with_warning() -> None:
    new_rule = convert({"sections": {"special_section": "sync"}})

    assert new_rule.warnings == ["Could not map section 'special_section'."]
    assert dump(new_rule.rule)["sections"] == {}


def test_sections_sync_becomes_synchronous() -> None:
    assert dump(convert({"sections": {"instance": "sync"}}).rule)["sections"] == {"instance": False}


def test_sections_async_becomes_asynchronous() -> None:
    assert dump(convert({"sections": {"tablespaces": "async"}}).rule)["sections"] == {
        "tablespaces": True
    }


def test_sections_none_becomes_disabled() -> None:
    assert dump(convert({"sections": {"iostats": None}}).rule)["sections"] == {}


def test_sections_unsupported_value_becomes_disabled() -> None:
    assert dump(convert({"sections": {"iostats": "bad"}}).rule)["sections"] == {}


def test_sections_asm_sections_are_renamed() -> None:
    new_rule = convert(
        {
            "sections": {
                "asm:instance": "sync",
                "asm:asm_diskgroup": "async",
                "asm:processes": "sync",
            }
        }
    )
    assert dump(new_rule.rule)["sections"] == {
        "asm_instance": False,
        "asm_diskgroup": True,
        "processes": False,
    }


def test_missing_excluded_sections_are_not_mapped() -> None:
    new_rule = convert({})
    assert "excluded_sections" not in dump(new_rule.rule)


def test_excluded_sections_are_mapped_correctly() -> None:
    new_rule = convert(
        {"excluded_sections": [("test_sid", ["performance", "tablespaces", "locks"])]}
    )
    assert dump(new_rule.rule)["excluded_sections"] == [
        {
            "target_id": ("sid", "test_sid"),
            "sections": ["performance", "tablespaces", "locks"],
        }
    ]


def test_unmappable_fields_ignored() -> None:
    new_rule = convert(
        {
            "sqlnet_ora_group": "some_group",
            "xinetd_or_systemd": ("xinetd", None),
            "sqlnet_send_timeout": 30,
            "tnsalias_pre_postfix": ("all_sids", ("a", "b")),
            "remote_oracle_home": "/x",
        }
    )
    assert (
        "'sqlnet.ora permission group' has been skipped because it is not needed anymore by the unified plugin."
        in new_rule.warnings
    )
    assert (
        "'Host uses xinetd or systemd' has been skipped because it is not needed by the unified plugin."
        in new_rule.warnings
    )
    assert (
        "'Sqlnet Send timeout' has been skipped because it is not supported by the unified plugin. Use Connection Timeout instead if this is applicable."
        in new_rule.warnings
    )
    # A rule that names none of the settings the unified plug-in needs converts
    # to a rule that names none of them either.
    assert dump(new_rule.rule) == {}


def test_permissions_not_mapped_when_validate_permissions_absent() -> None:
    assert "validate_permissions" not in dump(convert({"activated": True}).rule)


def test_permissions_disabled_when_validate_permissions_disabled() -> None:
    assert dump(convert({"validate_permissions": "disable"}).rule)["validate_permissions"] == (
        "disabled",
        None,
    )


def test_permissions_enabled_with_safe_entries_when_white_list_set() -> None:
    new_rule = convert(
        {"validate_permissions": ("enable", {"groups_and_users_white_list": ["aaaaaa", "bbbbb"]})}
    )
    assert dump(new_rule.rule)["validate_permissions"] == (
        "enabled",
        {"safe_entries": ["aaaaaa", "bbbbb"]},
    )


def test_permissions_enabled_without_safe_entries_when_white_list_empty() -> None:
    new_rule = convert({"validate_permissions": ("enable", {"groups_and_users_white_list": []})})
    assert dump(new_rule.rule)["validate_permissions"] == ("enabled", {})


def test_permissions_enabled_without_safe_entries_when_white_list_absent() -> None:
    assert dump(convert({"validate_permissions": ("enable", {})}).rule)["validate_permissions"] == (
        "enabled",
        {},
    )


def test_permissions_not_mapped_when_validate_permissions_unknown() -> None:
    assert "validate_permissions" not in dump(convert({"validate_permissions": "nonsense"}).rule)


def test_discovery_not_mapped_when_nothing_defined() -> None:
    assert "discovery" not in dump(convert({"sids": None}).rule)


def test_discovery_include_mapped_when_sids_defined() -> None:
    assert dump(convert({"sids": ("only", ["a", "b"])}).rule)["discovery"] == {
        "enabled": "enabled",
        "include": ["a", "b"],
    }


def test_discovery_exclude_mapped_when_skip_defined() -> None:
    assert dump(convert({"sids": ("skip", ["a"])}).rule)["discovery"] == {
        "enabled": "enabled",
        "exclude": ["a"],
    }


def test_discovery_include_mapped_when_exclude_defined() -> None:
    assert dump(convert({"sids": ("exclude", ["a"])}).rule)["discovery"] == {
        "enabled": "enabled",
        "exclude": ["a"],
    }


def test_auth_type_wallet_when_auth_is_wallet() -> None:
    assert dump(convert({"login": {"auth": "wallet"}}).rule)["auth"] == {
        "auth_type": ("wallet", None)
    }


def test_standard_auth_type_with_password_when_auth_is_explicit_with_password() -> None:
    new_rule = convert({"login": {"auth": ("explicit", ("my_user", ("password", "my_password")))}})
    assert dump(new_rule.rule)["auth"] == {
        "auth_type": (
            "standard",
            {
                "username": "my_user",
                "password": ("cmk_postprocessed", "explicit_password", ("", "my_password")),
            },
        )
    }


def test_standard_auth_type_with_store_when_auth_is_explicit_with_store() -> None:
    new_rule = convert({"login": {"auth": ("explicit", ("store_user", ("store", "password_1")))}})
    assert dump(new_rule.rule)["auth"] == {
        "auth_type": (
            "standard",
            {
                "username": "store_user",
                "password": ("cmk_postprocessed", "stored_password", ("password_1", "")),
            },
        )
    }


def test_role_mapped_when_as_set() -> None:
    new_rule = convert({"login": {"auth": "wallet", "as": "sysdba"}})
    assert dump(new_rule.rule)["auth"] == {"auth_type": ("wallet", None), "role": "sysdba"}


def test_role_omitted_when_as_none() -> None:
    new_rule = convert({"login": {"auth": "wallet", "as": None}})
    assert dump(new_rule.rule)["auth"] == {"auth_type": ("wallet", None)}


def test_connection_empty_when_not_specified() -> None:
    new_rule = convert({"login": {"auth": "wallet"}})
    assert dump(new_rule.rule)["connection"] == {}


def test_connection_converts_without_tns_admin() -> None:
    new_rule = convert({"login": {"auth": "wallet", "host": "my_host", "port": 1521}})
    assert dump(new_rule.rule)["connection"] == {"host": "my_host", "port": 1521}


def test_connection_host_kept_when_explicitly_set_to_localhost() -> None:
    new_rule = convert({"login": {"auth": "wallet", "host": "localhost"}})
    assert dump(new_rule.rule)["connection"] == {"host": "localhost"}


def test_connection_converts_with_tns_admin() -> None:
    new_rule = convert(
        {"login": {"auth": "wallet", "host": "my_host", "port": 1521}, "tns_admin": "tadmin"}
    )
    dumped = dump(new_rule.rule)
    assert dumped["connection"] == {"host": "my_host", "port": 1521}
    assert dumped["tns_admin"] == "tadmin"


def test_tns_admin_survives_a_rule_without_a_login() -> None:
    # The legacy ruleset holds tns_admin beside 'login', not inside it, so a rule
    # can name one without the other.
    assert dump(convert({"tns_admin": "tadmin"}).rule)["tns_admin"] == "tadmin"


def test_login_without_tnsalias_has_no_instance() -> None:
    new_rule = convert({"login": {"auth": "wallet"}})
    dumped = dump(new_rule.rule)

    assert dumped["auth"] == {"auth_type": ("wallet", None)}
    assert dumped["connection"] == {}

    assert "instances_rev2" not in dumped


def test_login_with_tnsalias_creates_no_instance() -> None:
    new_rule = convert({"login": {"auth": "wallet", "tnsalias": "myalias"}})
    dumped = dump(new_rule.rule)

    assert dumped["auth"] == {"auth_type": ("wallet", None)}
    assert dumped["connection"] == {}

    assert "instances_rev2" not in dumped


def test_login_with_tnsalias_warns_that_it_could_not_be_migrated() -> None:
    new_rule = convert({"login": {"auth": "wallet", "tnsalias": "myalias"}})

    assert (
        "The TNS alias 'myalias' of the default login could not be migrated, because the "
        "unified plugin accepts a TNS alias for a single database only, not as a default for "
        "all of them. Monitored instances are now reached via the configured host and port. "
        "If the alias points somewhere else, add it as an entry under 'Databases to monitor'."
        in new_rule.warnings
    )


def test_login_tnsalias_does_not_affect_main_auth_and_connection() -> None:
    new_rule = convert(
        {"login": {"auth": "wallet", "host": "mydata.db", "port": 3635, "tnsalias": "myalias"}}
    )
    dumped = dump(new_rule.rule)

    assert dumped["auth"] == {"auth_type": ("wallet", None)}
    assert dumped["connection"] == {"host": "mydata.db", "port": 3635}

    assert "instances_rev2" not in dumped


def test_no_instance_created_when_no_login_exceptions() -> None:
    new_rule = convert({"login_exceptions": []})
    assert "instances_rev2" not in dump(new_rule.rule)


def test_instance_created_when_login_exceptions_present() -> None:
    new_rule = convert(
        {
            "login_exceptions": [
                ("SID1", {"auth": "wallet", "host": "mydata.db", "port": 3635, "as": None})
            ]
        }
    )
    assert dump(new_rule.rule)["instances_rev2"] == [
        {
            "auth": {"auth_type": ("wallet", None)},
            "oracle_id": ("sid", "SID1"),
            "connection": {"host": "mydata.db", "port": 3635},
        }
    ]


def test_sid_specific_credentials_are_not_promoted_to_the_default_login() -> None:
    new_rule = convert(
        {
            "login_exceptions": [
                ("proddb", {"auth": ("explicit", ("sys", ("password", "oracle"))), "as": "sysdba"}),
                ("testdb", {"auth": ("explicit", ("checkmk", ("password", "checkmk")))}),
            ]
        }
    )
    dumped = dump(new_rule.rule)

    assert "auth" not in dumped, "credentials for one database are not the default ones"
    assert [instance["oracle_id"] for instance in dumped["instances_rev2"]] == [
        ("sid", "proddb"),
        ("sid", "testdb"),
    ]


def test_remote_instance_maps_connection_and_piggyback() -> None:
    new_rule = convert(
        {
            "remote_instances": [
                {
                    "id": "sid",
                    "sid": "ORCL",
                    "host": "remote-host",
                    "port": 1521,
                    "piggyhost": "remote-monitoring-host",
                }
            ]
        }
    )
    assert dump(new_rule.rule)["instances_rev2"] == [
        {
            "oracle_id": ("sid", "ORCL"),
            "connection": {"host": "remote-host", "port": 1521},
            "piggyback_host": "remote-monitoring-host",
        }
    ]


def test_remote_instance_auth_from_login_exception_via_sid() -> None:
    new_rule = convert(
        {
            "remote_instances": [
                {
                    "id": "sid",
                    "sid": "ORCL",
                    "host": "remote-host",
                    "port": 1521,
                }
            ],
            "login_exceptions": [
                (
                    "ORCL",
                    {
                        "auth": ("explicit", ("orcl_user", ("password", "orcl_pass"))),
                        "as": "sysdba",
                    },
                )
            ],
        }
    )
    assert dump(new_rule.rule)["instances_rev2"][0]["auth"] == {
        "auth_type": (
            "standard",
            {
                "username": "orcl_user",
                "password": ("cmk_postprocessed", "explicit_password", ("", "orcl_pass")),
            },
        ),
        "role": "sysdba",
    }


def test_remote_instance_auth_from_login_exception_via_piggyhost() -> None:
    new_rule = convert(
        {
            "remote_instances": [
                {
                    "id": "piggyhost",
                    "sid": "ORCL2",
                    "host": "remote-host-2",
                    "port": 1522,
                    "piggyhost": "monitor-host-2",
                }
            ],
            "login_exceptions": [
                (
                    "monitor-host-2",
                    {
                        "auth": ("explicit", ("piggy_user", ("store", "stored_pw_id"))),
                        "as": "sysoper",
                    },
                )
            ],
        }
    )
    assert dump(new_rule.rule)["instances_rev2"][0]["auth"] == {
        "auth_type": (
            "standard",
            {
                "username": "piggy_user",
                "password": ("cmk_postprocessed", "stored_password", ("stored_pw_id", "")),
            },
        ),
        "role": "sysoper",
    }


def test_remote_instance_auth_from_login_exception_via_id() -> None:
    new_rules = convert(
        {
            "remote_instances": [
                {
                    "id": ("explicit", "custom123"),
                    "sid": "ORCL3",
                    "host": "remote-host-3",
                    "port": 1523,
                }
            ],
            "login_exceptions": [
                (
                    "custom123",
                    {"auth": "wallet", "as": "sysbackup"},
                )
            ],
        }
    )
    assert dump(new_rules.rule)["instances_rev2"][0]["auth"] == {
        "auth_type": ("wallet", None),
        "role": "sysbackup",
    }


def test_converts_only_one_instance_when_remote_instance_references_login_exception() -> None:
    # the login_exceptions entry is consumed by the remote instance's auth look-up,
    # it must not also be emitted as a separate local-SID instance
    new_rule = convert(
        {
            "remote_instances": [
                {
                    "id": "sid",
                    "sid": "ORCL",
                    "host": "remote-host",
                    "port": 1521,
                }
            ],
            "login_exceptions": [("ORCL", {"auth": "wallet", "as": "sysdba"})],
        }
    )
    assert len(dump(new_rule.rule)["instances_rev2"]) == 1


def test_converts_two_instances_when_remote_instance_cannot_reference_login_exception() -> None:
    new_rule = convert(
        {
            "remote_instances": [
                {
                    "id": "sid",
                    "sid": "ORCL",
                    "host": "remote-host",
                    "port": 1521,
                }
            ],
            "login_exceptions": [("EPIC", {"auth": "wallet", "as": "sysdba"})],
        }
    )
    assert len(dump(new_rule.rule)["instances_rev2"]) == 2
    assert "Could not find login for ORCL remote instance." in new_rule.warnings


def test_main_asm_auth_mapped_when_login_asm_present_without_host_and_port() -> None:
    new_rule = convert(
        {
            "login_asm": {
                "auth": ("explicit", ("asm_user", ("password", "asm_pass"))),
                "as": "sysasm",
            }
        }
    )
    dumped = dump(new_rule.rule)
    assert dumped["auth"]["asm_auth"] == {
        "username": "asm_user",
        "password": ("cmk_postprocessed", "explicit_password", ("", "asm_pass")),
        "role": "sysasm",
    }
    assert "instances_rev2" not in dumped


def test_fallback_instance_created_when_login_asm_has_host_and_port() -> None:
    new_rule = convert(
        {"login_asm": {"auth": "wallet", "as": "sysasm", "host": "asmhost", "port": 1521}}
    )
    dumped = dump(new_rule.rule)
    assert dumped["instances_rev2"] == [
        {
            "oracle_id": ("sid", "+ASM"),
            "auth": {"auth_type": ("wallet", None), "role": "sysasm"},
            "connection": {"host": "asmhost", "port": 1521},
        }
    ]
    assert "asm_auth" not in dumped.get("auth", {})


def test_fallback_instance_created_when_login_asm_has_explicit_auth_and_host() -> None:
    new_rule = convert(
        {
            "login_asm": {
                "auth": ("explicit", ("asm_user", ("password", "asm_pass"))),
                "as": "sysasm",
                "host": "asmhost",
                "port": 1521,
            }
        }
    )
    dumped = dump(new_rule.rule)
    assert dumped["instances_rev2"] == [
        {
            "oracle_id": ("sid", "+ASM"),
            "auth": {
                "auth_type": (
                    "standard",
                    {
                        "username": "asm_user",
                        "password": ("cmk_postprocessed", "explicit_password", ("", "asm_pass")),
                    },
                ),
                "role": "sysasm",
            },
            "connection": {"host": "asmhost", "port": 1521},
        }
    ]
    assert "asm_auth" not in dumped.get("auth", {})
