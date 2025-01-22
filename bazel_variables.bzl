UPSTREAM_MIRROR_URL = "https://artifacts.lan.tribe29.com/repository/upstream-archives/"

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
    "cce": [
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
    ],
    "cee": [
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
    ],
    "cme": [
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
    ],
    "cse": [
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
    ],
}
