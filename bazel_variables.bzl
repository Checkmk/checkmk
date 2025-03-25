UPSTREAM_MIRROR_URL = "https://artifacts.lan.tribe29.com/repository/upstream-archives/"
RUFF_VERSION = "0.9.6"

edition_deps = {
    "cre": [],
    "cce": [
        "//non-free/packages/cmk-mknotifyd:cmk_mknotifyd_pkg",
        "//non-free/packages/cmc-protocols:pkg_tar",
        "//non-free/packages/cmk-otel-collector:pkg_tar",
    ],
    "cee": [
        "//non-free/packages/cmk-mknotifyd:cmk_mknotifyd_pkg",
        "//non-free/packages/cmc-protocols:pkg_tar",
    ],
    "cme": [
        "//non-free/packages/cmk-mknotifyd:cmk_mknotifyd_pkg",
        "//non-free/packages/cmc-protocols:pkg_tar",
        "//non-free/packages/cmk-otel-collector:pkg_tar",
    ],
    "cse": [
        "//non-free/packages/cmk-mknotifyd:cmk_mknotifyd_pkg",
        "//non-free/packages/cmc-protocols:pkg_tar",
        "//non-free/packages/cmk-otel-collector:pkg_tar",
    ],
}

edition_skel_permissions = {
    "cre": [
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
    ],
    "cce": [
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
    ],
    "cee": [
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
    ],
    "cme": [
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
    ],
    "cse": [
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
    ],
}
