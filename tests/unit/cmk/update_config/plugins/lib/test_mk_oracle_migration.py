#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.update_config.plugins.lib.mk_oracle_migration import convert, dump


def test_empty_body_is_not_deployed() -> None:
    assert dump(convert({}).rule)["deploy"] == ("do_not_deploy", None)


def test_empty_body_auth_is_wallet() -> None:
    assert dump(convert({}).rule)["main"]["auth"] == {"auth_type": ("wallet", None)}


def test_empty_body_auth_type_is_a_plain_str_not_an_enum_member() -> None:
    # StrEnum == str, so this catches what == "wallet" above can't: an unconverted enum
    # member, which pprints as invalid Python syntax.
    auth_type = dump(convert({}).rule)["main"]["auth"]["auth_type"][0]
    assert type(auth_type) is str


def test_empty_body_has_no_instances() -> None:
    assert dump(convert({}).rule)["instances"] == []


def test_empty_body_has_warning() -> None:
    assert convert({}).warnings == ["No auth defined in legacy rule. Defaulting to Oracle wallet."]


def test_deploy_when_activated_true() -> None:
    assert dump(convert({"activated": True}).rule)["deploy"] == ("deploy", None)


def test_do_not_deploy_when_activated_false() -> None:
    assert dump(convert({"activated": False}).rule)["deploy"] == ("do_not_deploy", None)


def test_async_interval_cache_age() -> None:
    assert dump(convert({"async_interval": 600}).rule)["main"]["cache_age"] == 600


def test_sections_supported_keys_are_mapped() -> None:
    new_rule = convert({"sections": {"instance": "sync"}})

    assert new_rule.warnings == ["No auth defined in legacy rule. Defaulting to Oracle wallet."]
    assert dump(new_rule.rule)["main"]["sections"] == {"instance": "synchronous"}


def test_sections_unsupported_keys_are_skipped_with_warning() -> None:
    new_rule = convert({"sections": {"special_section": "sync"}})

    assert new_rule.warnings == [
        "Could not map section 'special_section'.",
        "No auth defined in legacy rule. Defaulting to Oracle wallet.",
    ]
    assert dump(new_rule.rule)["main"]["sections"] == {}


def test_sections_sync_becomes_synchronous() -> None:
    assert dump(convert({"sections": {"instance": "sync"}}).rule)["main"]["sections"] == {
        "instance": "synchronous"
    }


def test_sections_async_becomes_asynchronous() -> None:
    assert dump(convert({"sections": {"tablespaces": "async"}}).rule)["main"]["sections"] == {
        "tablespaces": "asynchronous"
    }


def test_sections_none_becomes_disabled() -> None:
    assert dump(convert({"sections": {"iostats": None}}).rule)["main"]["sections"] == {
        "iostats": "disabled"
    }


def test_sections_unsupported_value_becomes_disabled() -> None:
    assert dump(convert({"sections": {"iostats": "bad"}}).rule)["main"]["sections"] == {
        "iostats": "disabled"
    }


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
    assert dump(new_rule.rule)["main"]["sections"] == {
        "asm_instance": "synchronous",
        "asm_diskgroup": "asynchronous",
        "processes": "synchronous",
    }


def test_unmappable_fields_ignored() -> None:
    new_rule = convert(
        {
            "sqlnet_ora_group": "some_group",
            "validate_permissions": ("enable", {}),
            "xinetd_or_systemd": ("xinetd", None),
            "sqlnet_send_timeout": 30,
            "excluded_sections": [("s", ["x"])],
            "tnsalias_pre_postfix": ("all_sids", ("a", "b")),
            "remote_oracle_home": "/x",
        }
    )
    assert (
        "'sqlnet.ora permission group' has been skipped because it is not needed anymore by the unified plugin."
        in new_rule.warnings
    )
    assert (
        "'Oracle binaries permissions check' has been skipped because it is not needed by the unified plugin."
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
    assert (
        "'Exclude some sections on certain instances' cannot be mapped. The new rule format only supports disabling sections globally."
        in new_rule.warnings
    )
    assert dump(new_rule.rule) == {
        "deploy": ("do_not_deploy", None),
        "main": {"auth": {"auth_type": ("wallet", None)}, "connection": {}},
        "instances": [],
    }


def test_discovery_not_mapped_when_nothing_defined() -> None:
    assert "discovery" not in dump(convert({"sids": None}).rule)["main"]


def test_discovery_include_mapped_when_sids_defined() -> None:
    assert dump(convert({"sids": ("only", ["a", "b"])}).rule)["main"]["discovery"] == {
        "enabled": True,
        "include": ["a", "b"],
    }


def test_discovery_exclude_mapped_when_skip_defined() -> None:
    assert dump(convert({"sids": ("skip", ["a"])}).rule)["main"]["discovery"] == {
        "enabled": True,
        "exclude": ["a"],
    }


def test_discovery_include_mapped_when_exclude_defined() -> None:
    assert dump(convert({"sids": ("exclude", ["a"])}).rule)["main"]["discovery"] == {
        "enabled": True,
        "exclude": ["a"],
    }


def test_auth_type_wallet_when_auth_is_wallet() -> None:
    assert dump(convert({"login": {"auth": "wallet"}}).rule)["main"]["auth"] == {
        "auth_type": ("wallet", None)
    }


def test_standard_auth_type_with_password_when_auth_is_explicit_with_password() -> None:
    new_rule = convert({"login": {"auth": ("explicit", ("my_user", ("password", "my_password")))}})
    assert dump(new_rule.rule)["main"]["auth"] == {
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
    assert dump(new_rule.rule)["main"]["auth"] == {
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
    assert dump(new_rule.rule)["main"]["auth"] == {"auth_type": ("wallet", None), "role": "sysdba"}


def test_role_omitted_when_as_none() -> None:
    new_rule = convert({"login": {"auth": "wallet", "as": None}})
    assert dump(new_rule.rule)["main"]["auth"] == {"auth_type": ("wallet", None)}


def test_connection_empty_when_not_specified() -> None:
    new_rule = convert({"login": {"auth": "wallet"}})
    assert dump(new_rule.rule)["main"]["connection"] == {}


def test_connection_converts_without_tns_admin() -> None:
    new_rule = convert({"login": {"auth": "wallet", "host": "my_host", "port": 1521}})
    assert dump(new_rule.rule)["main"]["connection"] == {"host": "my_host", "port": 1521}


def test_connection_host_kept_when_explicitly_set_to_localhost() -> None:
    new_rule = convert({"login": {"auth": "wallet", "host": "localhost"}})
    assert dump(new_rule.rule)["main"]["connection"] == {"host": "localhost"}


def test_connection_converts_with_tns_admin() -> None:
    new_rule = convert(
        {"login": {"auth": "wallet", "host": "my_host", "port": 1521}, "tns_admin": "tadmin"}
    )
    assert dump(new_rule.rule)["main"]["connection"] == {
        "host": "my_host",
        "port": 1521,
        "tns_admin": "tadmin",
    }


def test_login_without_tnsalias_has_no_instance() -> None:
    new_rule = convert({"login": {"auth": "wallet"}})
    dumped = dump(new_rule.rule)

    assert dumped["main"] == {"auth": {"auth_type": ("wallet", None)}, "connection": {}}

    assert dumped["instances"] == []


def test_login_with_tnsalias_adds_an_instance() -> None:
    new_rule = convert({"login": {"auth": "wallet", "tnsalias": "myalias"}})
    dumped = dump(new_rule.rule)

    assert dumped["main"] == {"auth": {"auth_type": ("wallet", None)}, "connection": {}}

    assert dumped["instances"] == [
        {
            "auth": {"auth_type": ("wallet", None)},
            "connection": {},
            "oracle_id": ("alias", {"alias": "myalias"}),
        }
    ]


def test_login_tnsalias_extra_instance_has_correct_connection() -> None:
    new_rule = convert(
        {"login": {"auth": "wallet", "host": "mydata.db", "port": 3635, "tnsalias": "myalias"}}
    )
    dumped = dump(new_rule.rule)

    assert dumped["main"] == {
        "auth": {"auth_type": ("wallet", None)},
        "connection": {"host": "mydata.db", "port": 3635},
    }

    assert dumped["instances"] == [
        {
            "auth": {"auth_type": ("wallet", None)},
            "connection": {"host": "mydata.db", "port": 3635},
            "oracle_id": ("alias", {"alias": "myalias"}),
        }
    ]


def test_no_instance_created_when_no_login_exceptions() -> None:
    new_rule = convert({"login_exceptions": []})
    assert dump(new_rule.rule)["instances"] == []


def test_instance_created_when_login_exceptions_present() -> None:
    new_rule = convert(
        {
            "login_exceptions": [
                ("SID1", {"auth": "wallet", "host": "mydata.db", "port": 3635, "as": None})
            ]
        }
    )
    assert dump(new_rule.rule)["instances"] == [
        {
            "auth": {"auth_type": ("wallet", None)},
            "oracle_id": ("sid", {"sid": "SID1"}),
            "connection": {"host": "mydata.db", "port": 3635},
        }
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
    assert dump(new_rule.rule)["instances"] == [
        {
            "oracle_id": ("sid", {"sid": "ORCL"}),
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
    assert dump(new_rule.rule)["instances"][0]["auth"] == {
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
    assert dump(new_rule.rule)["instances"][0]["auth"] == {
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
    assert dump(new_rules.rule)["instances"][0]["auth"] == {
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
    assert len(dump(new_rule.rule)["instances"]) == 1


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
    assert len(dump(new_rule.rule)["instances"]) == 2
    assert new_rule.warnings[0] == "Could not find login for ORCL remote instance."


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
    assert dumped["main"]["auth"]["asm_auth"] == {
        "username": "asm_user",
        "password": ("cmk_postprocessed", "explicit_password", ("", "asm_pass")),
        "role": "sysasm",
    }
    assert dumped["instances"] == []


def test_fallback_instance_created_when_login_asm_has_host_and_port() -> None:
    new_rule = convert(
        {"login_asm": {"auth": "wallet", "as": "sysasm", "host": "asmhost", "port": 1521}}
    )
    dumped = dump(new_rule.rule)
    assert dumped["instances"] == [
        {
            "oracle_id": ("sid", {"sid": "+ASM"}),
            "auth": {"auth_type": ("wallet", None), "role": "sysasm"},
            "connection": {"host": "asmhost", "port": 1521},
        }
    ]
    assert "asm_auth" not in dumped["main"].get("auth", {})


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
    assert dumped["instances"] == [
        {
            "oracle_id": ("sid", {"sid": "+ASM"}),
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
    assert "asm_auth" not in dumped["main"].get("auth", {})
